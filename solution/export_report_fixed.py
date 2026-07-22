#!/usr/bin/env python3
"""Badge-access containment rollup, restored per the Warden review decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = "exec-containment-v2"
CLASS_ORDER = ["system", "service", "batch", "adhoc"]
CLASS_RANK = {name: len(CLASS_ORDER) - idx for idx, name in enumerate(CLASS_ORDER)}
PRIORITY_ORDER = ["critical", "urgent", "normal"]
PRIORITY_RANK = {name: len(PRIORITY_ORDER) - idx for idx, name in enumerate(PRIORITY_ORDER)}
CONTROLS_PATH = Path("/app/data/exec_policies.json")
STITCH_GAP_MS = 140
CARRY_CAP_MS = 780
ZONE_QUEUE_CAP = 2
ADMISSION_FLOOR = {"system": 150, "service": 190, "batch": 240, "adhoc": 300}


def _norm_text(value: object) -> str:
    return " ".join(str(value).split())


def _norm_class(value: object) -> str:
    text = str(value).strip().lower()
    return text if text in CLASS_RANK else "adhoc"


def _norm_host(value: object) -> str:
    text = str(value).strip().lower()
    return text or "unknown"


def _norm_ms(value: object) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _norm_killed(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def load_events(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_controls(path: Path = CONTROLS_PATH) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_events(rows: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for row in rows:
        exec_id = str(row.get("exec_id", "")).strip()
        if not exec_id:
            continue
        candidate = {
            "exec_id": exec_id,
            "image_ref": str(row.get("image_ref", "")).strip(),
            "run_class": _norm_class(row.get("run_class", "")),
            "host": _norm_host(row.get("host", "")),
            "binary": _norm_text(row.get("binary", "")),
            "started_ms": _norm_ms(row.get("started_ms", 0)),
            "ended_ms": _norm_ms(row.get("ended_ms", 0)),
            "killed": _norm_killed(row.get("killed", False)),
        }
        existing = deduped.get(exec_id)
        if existing is None:
            deduped[exec_id] = candidate
            continue
        if candidate["started_ms"] > existing["started_ms"]:
            deduped[exec_id] = candidate
            continue
        if candidate["started_ms"] < existing["started_ms"]:
            continue
        # PX-3318 reverses this: on a duplicate tie the LOWER exec class wins.
        if CLASS_RANK[candidate["run_class"]] < CLASS_RANK[existing["run_class"]]:
            deduped[exec_id] = candidate
            continue
        if CLASS_RANK[candidate["run_class"]] > CLASS_RANK[existing["run_class"]]:
            continue
        if len(candidate["binary"]) > len(existing["binary"]):
            deduped[exec_id] = candidate
            continue
        if len(candidate["binary"]) < len(existing["binary"]):
            continue
        if candidate["host"] > existing["host"]:
            deduped[exec_id] = candidate
    canonical = list(deduped.values())
    canonical.sort(key=lambda row: (row["host"], row["started_ms"], row["exec_id"]))
    return canonical


def _compact(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(s, e) for s, e in merged]


def _overlap(a_start: int, a_end: int, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = []
    for start, end in spans:
        lo, hi = max(a_start, start), min(a_end, end)
        if hi > lo:
            out.append((lo, hi))
    return out


def controls_for(rows: list[dict], host: str, layer: str, run_class: str) -> list[tuple[int, int]]:
    """PX-3326 scope: a class uses its OWN windows for this layer; only a class with
    no window of its own falls back to the `all` scope. Own entries do not also
    inherit `all`."""
    own = [
        (_norm_ms(r["start_ms"]), _norm_ms(r["end_ms"])) for r in rows
        if r.get("layer") == layer and _norm_host(r.get("host")) == host
        and str(r.get("scope")) == run_class and _norm_ms(r["end_ms"]) > _norm_ms(r["start_ms"])
    ]
    if own:
        return _compact(own)
    return _compact([
        (_norm_ms(r["start_ms"]), _norm_ms(r["end_ms"])) for r in rows
        if r.get("layer") == layer and _norm_host(r.get("host")) == host
        and str(r.get("scope")) == "all" and _norm_ms(r["end_ms"]) > _norm_ms(r["start_ms"])
    ])


def build_sessions(canonical: list[dict], controls: list[dict]) -> dict[str, list[dict]]:
    by_host: dict[str, list[dict]] = {}
    for row in canonical:
        # PX-3322: killed execs are excluded from session construction only.
        if row["killed"]:
            continue
        by_host.setdefault(row["host"], []).append(row)

    result: dict[str, list[dict]] = {}
    for host, rows in by_host.items():
        rows.sort(key=lambda r: (r["started_ms"], r["exec_id"]))
        sessions: list[dict] = []
        current: dict | None = None
        for row in rows:
            end_ms = max(row["ended_ms"], row["started_ms"])
            if current is None:
                current = {
                    "start_ms": row["started_ms"], "end_ms": end_ms,
                    "exec_ids": [row["exec_id"]], "lead_class": row["run_class"],
                }
                continue
            # PX-3320 retuned the stitch gap; sessions merge across it.
            if row["started_ms"] <= current["end_ms"] + STITCH_GAP_MS:
                current["end_ms"] = max(current["end_ms"], end_ms)
                current["exec_ids"].append(row["exec_id"])
                if CLASS_RANK[row["run_class"]] > CLASS_RANK[current["lead_class"]]:
                    current["lead_class"] = row["run_class"]
                continue
            sessions.append(current)
            current = {
                "start_ms": row["started_ms"], "end_ms": end_ms,
                "exec_ids": [row["exec_id"]], "lead_class": row["run_class"],
            }
        if current is not None:
            sessions.append(current)

        prev_carry_out = 0
        prev_end: int | None = None
        built: list[dict] = []
        for session in sessions:
            runtime = max(session["end_ms"] - session["start_ms"], 0)
            lock_spans = _compact(_overlap(
                session["start_ms"], session["end_ms"],
                controls_for(controls, host, "sandbox", session["lead_class"])))
            maint_spans = _compact(_overlap(
                session["start_ms"], session["end_ms"],
                controls_for(controls, host, "audit", session["lead_class"])))
            sandbox_overlap = sum(e - s for s, e in lock_spans)
            audit_overlap = sum(e - s for s, e in maint_spans)
            # PX-3328: sandbox wins any instant both layers cover.
            shared = 0
            for ls, le in lock_spans:
                for ms, me in maint_spans:
                    shared += max(0, min(le, me) - max(ls, ms))
            audit_used = max(audit_overlap - shared, 0)
            adjusted_runtime = max(
                runtime - (-(-sandbox_overlap // 2)) - (-(-audit_used // 3)), 0
            )
            idle_gap = 0 if prev_end is None else max(session["start_ms"] - prev_end, 0)
            carry_in = max(prev_carry_out - (-(-idle_gap // 4)), 0)
            ledger_runtime = adjusted_runtime + (carry_in // 5)
            carry_out = min(
                carry_in + adjusted_runtime + len(session["exec_ids"]) * 6, CARRY_CAP_MS
            )
            built.append({
                "start_ms": session["start_ms"], "end_ms": session["end_ms"],
                "runtime_ms": runtime,
                "sandbox_overlap_ms": sandbox_overlap,
                "audit_overlap_ms": audit_overlap,
                "adjusted_runtime_ms": adjusted_runtime,
                "idle_gap_ms": idle_gap, "carry_in_ms": carry_in,
                "carry_out_ms": carry_out, "ledger_runtime_ms": ledger_runtime,
                "exec_count": len(session["exec_ids"]),
                "exec_ids": sorted(session["exec_ids"]),
                "lead_class": session["lead_class"],
            })
            prev_carry_out = carry_out
            prev_end = session["end_ms"]
        result[host] = built
    return {host: result[host] for host in sorted(result)}


def build_queue(sessions: dict[str, list[dict]]) -> list[dict]:
    queue: list[dict] = []
    for host, rows in sessions.items():
        for row in rows:
            if row["ledger_runtime_ms"] < ADMISSION_FLOOR[row["lead_class"]]:
                continue
            if row["ledger_runtime_ms"] >= 420 or (
                row["lead_class"] == "system" and row["sandbox_overlap_ms"] > 0
            ):
                priority = "critical"
            elif row["ledger_runtime_ms"] >= 300 or row["exec_count"] >= 3:
                priority = "urgent"
            else:
                priority = "normal"
            payload = (
                f"{host}|{row['start_ms']}|{row['end_ms']}|{','.join(row['exec_ids'])}"
                f"|{row['lead_class']}|{row['ledger_runtime_ms']}"
            )
            queue.append({
                "incident_id": f"{host}:{row['start_ms']}-{row['end_ms']}",
                "host": host, "start_ms": row["start_ms"], "end_ms": row["end_ms"],
                "lead_class": row["lead_class"], "priority": priority,
                "runtime_ms": row["runtime_ms"], "adjusted_runtime_ms": row["adjusted_runtime_ms"],
                "ledger_runtime_ms": row["ledger_runtime_ms"],
                "sandbox_overlap_ms": row["sandbox_overlap_ms"],
                "audit_overlap_ms": row["audit_overlap_ms"],
                "carry_in_ms": row["carry_in_ms"], "carry_out_ms": row["carry_out_ms"],
                "exec_count": row["exec_count"], "exec_ids": row["exec_ids"],
                "burst_digest": hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12],
            })
    queue.sort(key=lambda r: (
        -PRIORITY_RANK[r["priority"]], -r["ledger_runtime_ms"], -r["runtime_ms"],
        -r["exec_count"], r["host"], r["start_ms"],
    ))
    # PX-3330: responder capacity cap, applied AFTER the ordering chain above.
    kept: dict[str, int] = {}
    capped: list[dict] = []
    for row in queue:
        taken = kept.get(row["host"], 0)
        if taken >= ZONE_QUEUE_CAP:
            continue
        kept[row["host"]] = taken + 1
        capped.append(row)
    return capped


def export_report(events: list[dict], output_dir: Path, controls: list[dict]) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical = canonical_events(events)
    sessions = build_sessions(canonical, controls)
    queue = build_queue(sessions)

    run_counts = {name: 0 for name in CLASS_ORDER}
    for row in canonical:
        run_counts[row["run_class"]] += 1

    all_rows = [r for rows in sessions.values() for r in rows]
    matrix = {
        host: {
            "session_count": len(rows),
            "total_runtime_ms": sum(r["runtime_ms"] for r in rows),
            "total_ledger_runtime_ms": sum(r["ledger_runtime_ms"] for r in rows),
            "max_carry_out_ms": max((r["carry_out_ms"] for r in rows), default=0),
            "queued_count": sum(1 for r in queue if r["host"] == host),
        }
        for host, rows in sessions.items()
    }

    canonical_payload = "\n".join(
        f"{r['exec_id']}|{r['image_ref']}|{r['run_class']}|{r['host']}|{r['started_ms']}"
        f"|{r['ended_ms']}|{1 if r['killed'] else 0}" for r in canonical
    )
    control_payload = "\n".join(
        f"{r['layer']}|{r['scope']}|{_norm_host(r['host'])}|{_norm_ms(r['start_ms'])}|{_norm_ms(r['end_ms'])}"
        for r in sorted(controls, key=lambda r: (
            str(r["layer"]), str(r["scope"]), _norm_host(r["host"]), _norm_ms(r["start_ms"])))
    )
    queue_payload = "\n".join(
        f"{r['incident_id']}|{r['priority']}|{r['ledger_runtime_ms']}|{r['burst_digest']}" for r in queue
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "raw_exec_count": len(events),
        "unique_exec_ids": len({str(e.get("exec_id", "")).strip() for e in events if str(e.get("exec_id", "")).strip()}),
        "canonical_exec_count": len(canonical),
        "run_counts": run_counts,
        "hosts": sorted(sessions),
        "host_count": len(sessions),
        "killed_excluded_count": sum(1 for r in canonical if r["killed"]),
        "session_count": len(all_rows),
        "total_runtime_ms": sum(r["runtime_ms"] for r in all_rows),
        "total_adjusted_runtime_ms": sum(r["adjusted_runtime_ms"] for r in all_rows),
        "total_ledger_runtime_ms": sum(r["ledger_runtime_ms"] for r in all_rows),
        "total_sandbox_overlap_ms": sum(r["sandbox_overlap_ms"] for r in all_rows),
        "total_audit_overlap_ms": sum(r["audit_overlap_ms"] for r in all_rows),
        "max_ledger_runtime_ms": max((r["ledger_runtime_ms"] for r in all_rows), default=0),
        "max_carry_out_ms": max((r["carry_out_ms"] for r in all_rows), default=0),
        "longest_session_ms": max((r["runtime_ms"] for r in all_rows), default=0),
        "contained_count": len(queue),
        "priority_counts": {
            name: sum(1 for r in queue if r["priority"] == name) for name in PRIORITY_ORDER
        },
        "canonical_exec_checksum": hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        "exec_policy_checksum": hashlib.sha256(control_payload.encode("utf-8")).hexdigest(),
        "containment_checksum": hashlib.sha256(queue_payload.encode("utf-8")).hexdigest(),
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_dir / "host_matrix.json").write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "contained.jsonl").open("w", encoding="utf-8") as handle:
        for row in queue:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/app/data/exec_events.json")
    parser.add_argument("--output-dir", default="/app/output")
    args = parser.parse_args()

    events = load_events(Path(args.input))
    export_report(events, Path(args.output_dir), load_controls())
    print(f"Wrote containment rollup to {args.output_dir}")


if __name__ == "__main__":
    main()
