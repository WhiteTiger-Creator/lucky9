#!/usr/bin/env python3
"""Warden exec-access containment audit CLI: diagnose and repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORKFLOW_PATH = Path("/app/workflow/export_report.py")
FROZEN_PATH = Path("/app/workflow/.export_report.original")
DOSSIER_PATH = Path("/app/incident/exec_review_dossier.md")
SPEC_PATH = Path("/app/docs/report_spec.json")
EVENTS_PATH = Path("/app/data/exec_events.json")

REPAIRED_SOURCE = '#!/usr/bin/env python3\n"""Badge-access containment rollup, restored per the Warden review decisions."""\n\nfrom __future__ import annotations\n\nimport argparse\nimport hashlib\nimport json\nfrom pathlib import Path\n\nSCHEMA_VERSION = "exec-containment-v2"\nCLASS_ORDER = ["system", "service", "batch", "adhoc"]\nCLASS_RANK = {name: len(CLASS_ORDER) - idx for idx, name in enumerate(CLASS_ORDER)}\nPRIORITY_ORDER = ["critical", "urgent", "normal"]\nPRIORITY_RANK = {name: len(PRIORITY_ORDER) - idx for idx, name in enumerate(PRIORITY_ORDER)}\nCONTROLS_PATH = Path("/app/data/exec_policies.json")\nSTITCH_GAP_MS = 140\nCARRY_CAP_MS = 780\nZONE_QUEUE_CAP = 2\nADMISSION_FLOOR = {"system": 150, "service": 190, "batch": 240, "adhoc": 300}\n\n\ndef _norm_text(value: object) -> str:\n    return " ".join(str(value).split())\n\n\ndef _norm_class(value: object) -> str:\n    text = str(value).strip().lower()\n    return text if text in CLASS_RANK else "adhoc"\n\n\ndef _norm_host(value: object) -> str:\n    text = str(value).strip().lower()\n    return text or "unknown"\n\n\ndef _norm_ms(value: object) -> int:\n    try:\n        return int(str(value).strip())\n    except (TypeError, ValueError):\n        return 0\n\n\ndef _norm_killed(value: object) -> bool:\n    if isinstance(value, bool):\n        return value\n    if isinstance(value, str):\n        return value.strip().lower() in {"true", "1", "yes"}\n    return bool(value)\n\n\ndef load_events(path: Path) -> list[dict]:\n    return json.loads(path.read_text(encoding="utf-8"))\n\n\ndef load_controls(path: Path = CONTROLS_PATH) -> list[dict]:\n    if not path.exists():\n        return []\n    return json.loads(path.read_text(encoding="utf-8"))\n\n\ndef canonical_events(rows: list[dict]) -> list[dict]:\n    deduped: dict[str, dict] = {}\n    for row in rows:\n        exec_id = str(row.get("exec_id", "")).strip()\n        if not exec_id:\n            continue\n        candidate = {\n            "exec_id": exec_id,\n            "image_ref": str(row.get("image_ref", "")).strip(),\n            "run_class": _norm_class(row.get("run_class", "")),\n            "host": _norm_host(row.get("host", "")),\n            "binary": _norm_text(row.get("binary", "")),\n            "started_ms": _norm_ms(row.get("started_ms", 0)),\n            "ended_ms": _norm_ms(row.get("ended_ms", 0)),\n            "killed": _norm_killed(row.get("killed", False)),\n        }\n        existing = deduped.get(exec_id)\n        if existing is None:\n            deduped[exec_id] = candidate\n            continue\n        if candidate["started_ms"] > existing["started_ms"]:\n            deduped[exec_id] = candidate\n            continue\n        if candidate["started_ms"] < existing["started_ms"]:\n            continue\n        # PX-3318 reverses this: on a duplicate tie the LOWER exec class wins.\n        if CLASS_RANK[candidate["run_class"]] < CLASS_RANK[existing["run_class"]]:\n            deduped[exec_id] = candidate\n            continue\n        if CLASS_RANK[candidate["run_class"]] > CLASS_RANK[existing["run_class"]]:\n            continue\n        if len(candidate["binary"]) > len(existing["binary"]):\n            deduped[exec_id] = candidate\n            continue\n        if len(candidate["binary"]) < len(existing["binary"]):\n            continue\n        if candidate["host"] > existing["host"]:\n            deduped[exec_id] = candidate\n    canonical = list(deduped.values())\n    canonical.sort(key=lambda row: (row["host"], row["started_ms"], row["exec_id"]))\n    return canonical\n\n\ndef _compact(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:\n    merged: list[list[int]] = []\n    for start, end in sorted(spans):\n        if not merged or start > merged[-1][1]:\n            merged.append([start, end])\n        else:\n            merged[-1][1] = max(merged[-1][1], end)\n    return [(s, e) for s, e in merged]\n\n\ndef _overlap(a_start: int, a_end: int, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:\n    out = []\n    for start, end in spans:\n        lo, hi = max(a_start, start), min(a_end, end)\n        if hi > lo:\n            out.append((lo, hi))\n    return out\n\n\ndef controls_for(rows: list[dict], host: str, layer: str, run_class: str) -> list[tuple[int, int]]:\n    """PX-3326 scope: a class uses its OWN windows for this layer; only a class with\n    no window of its own falls back to the `all` scope. Own entries do not also\n    inherit `all`."""\n    own = [\n        (_norm_ms(r["start_ms"]), _norm_ms(r["end_ms"])) for r in rows\n        if r.get("layer") == layer and _norm_host(r.get("host")) == host\n        and str(r.get("scope")) == run_class and _norm_ms(r["end_ms"]) > _norm_ms(r["start_ms"])\n    ]\n    if own:\n        return _compact(own)\n    return _compact([\n        (_norm_ms(r["start_ms"]), _norm_ms(r["end_ms"])) for r in rows\n        if r.get("layer") == layer and _norm_host(r.get("host")) == host\n        and str(r.get("scope")) == "all" and _norm_ms(r["end_ms"]) > _norm_ms(r["start_ms"])\n    ])\n\n\ndef build_sessions(canonical: list[dict], controls: list[dict]) -> dict[str, list[dict]]:\n    by_host: dict[str, list[dict]] = {}\n    for row in canonical:\n        # PX-3322: killed execs are excluded from session construction only.\n        if row["killed"]:\n            continue\n        by_host.setdefault(row["host"], []).append(row)\n\n    result: dict[str, list[dict]] = {}\n    for host, rows in by_host.items():\n        rows.sort(key=lambda r: (r["started_ms"], r["exec_id"]))\n        sessions: list[dict] = []\n        current: dict | None = None\n        for row in rows:\n            end_ms = max(row["ended_ms"], row["started_ms"])\n            if current is None:\n                current = {\n                    "start_ms": row["started_ms"], "end_ms": end_ms,\n                    "exec_ids": [row["exec_id"]], "lead_class": row["run_class"],\n                }\n                continue\n            # PX-3320 retuned the stitch gap; sessions merge across it.\n            if row["started_ms"] <= current["end_ms"] + STITCH_GAP_MS:\n                current["end_ms"] = max(current["end_ms"], end_ms)\n                current["exec_ids"].append(row["exec_id"])\n                if CLASS_RANK[row["run_class"]] > CLASS_RANK[current["lead_class"]]:\n                    current["lead_class"] = row["run_class"]\n                continue\n            sessions.append(current)\n            current = {\n                "start_ms": row["started_ms"], "end_ms": end_ms,\n                "exec_ids": [row["exec_id"]], "lead_class": row["run_class"],\n            }\n        if current is not None:\n            sessions.append(current)\n\n        prev_carry_out = 0\n        prev_end: int | None = None\n        built: list[dict] = []\n        for session in sessions:\n            runtime = max(session["end_ms"] - session["start_ms"], 0)\n            lock_spans = _compact(_overlap(\n                session["start_ms"], session["end_ms"],\n                controls_for(controls, host, "sandbox", session["lead_class"])))\n            maint_spans = _compact(_overlap(\n                session["start_ms"], session["end_ms"],\n                controls_for(controls, host, "audit", session["lead_class"])))\n            sandbox_overlap = sum(e - s for s, e in lock_spans)\n            audit_overlap = sum(e - s for s, e in maint_spans)\n            # PX-3328: sandbox wins any instant both layers cover.\n            shared = 0\n            for ls, le in lock_spans:\n                for ms, me in maint_spans:\n                    shared += max(0, min(le, me) - max(ls, ms))\n            audit_used = max(audit_overlap - shared, 0)\n            adjusted_runtime = max(\n                runtime - (-(-sandbox_overlap // 2)) - (-(-audit_used // 3)), 0\n            )\n            idle_gap = 0 if prev_end is None else max(session["start_ms"] - prev_end, 0)\n            carry_in = max(prev_carry_out - (-(-idle_gap // 4)), 0)\n            ledger_runtime = adjusted_runtime + (-(-carry_in // 5))\n            carry_out = min(\n                carry_in + adjusted_runtime + len(session["exec_ids"]) * 6, CARRY_CAP_MS\n            )\n            built.append({\n                "start_ms": session["start_ms"], "end_ms": session["end_ms"],\n                "runtime_ms": runtime,\n                "sandbox_overlap_ms": sandbox_overlap,\n                "audit_overlap_ms": audit_overlap,\n                "adjusted_runtime_ms": adjusted_runtime,\n                "idle_gap_ms": idle_gap, "carry_in_ms": carry_in,\n                "carry_out_ms": carry_out, "ledger_runtime_ms": ledger_runtime,\n                "exec_count": len(session["exec_ids"]),\n                "exec_ids": sorted(session["exec_ids"]),\n                "lead_class": session["lead_class"],\n            })\n            prev_carry_out = carry_out\n            prev_end = session["end_ms"]\n        result[host] = built\n    return {host: result[host] for host in sorted(result)}\n\n\ndef build_queue(sessions: dict[str, list[dict]]) -> list[dict]:\n    queue: list[dict] = []\n    for host, rows in sessions.items():\n        for row in rows:\n            if row["ledger_runtime_ms"] < ADMISSION_FLOOR[row["lead_class"]]:\n                continue\n            if row["ledger_runtime_ms"] >= 420 or (\n                row["lead_class"] == "system" and row["sandbox_overlap_ms"] > 0\n            ):\n                priority = "critical"\n            elif row["ledger_runtime_ms"] >= 300 or row["exec_count"] >= 3:\n                priority = "urgent"\n            else:\n                priority = "normal"\n            payload = (\n                f"{host}|{row[\'start_ms\']}|{row[\'end_ms\']}|{\',\'.join(row[\'exec_ids\'])}"\n                f"|{row[\'lead_class\']}|{row[\'ledger_runtime_ms\']}"\n            )\n            queue.append({\n                "incident_id": f"{host}:{row[\'start_ms\']}-{row[\'end_ms\']}",\n                "host": host, "start_ms": row["start_ms"], "end_ms": row["end_ms"],\n                "lead_class": row["lead_class"], "priority": priority,\n                "runtime_ms": row["runtime_ms"], "adjusted_runtime_ms": row["adjusted_runtime_ms"],\n                "ledger_runtime_ms": row["ledger_runtime_ms"],\n                "sandbox_overlap_ms": row["sandbox_overlap_ms"],\n                "audit_overlap_ms": row["audit_overlap_ms"],\n                "carry_in_ms": row["carry_in_ms"], "carry_out_ms": row["carry_out_ms"],\n                "exec_count": row["exec_count"], "exec_ids": row["exec_ids"],\n                "burst_digest": hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12],\n            })\n    queue.sort(key=lambda r: (\n        -PRIORITY_RANK[r["priority"]], -r["ledger_runtime_ms"], -r["runtime_ms"],\n        -r["exec_count"], r["host"], r["start_ms"],\n    ))\n    # PX-3330: responder capacity cap, applied AFTER the ordering chain above.\n    kept: dict[str, int] = {}\n    capped: list[dict] = []\n    for row in queue:\n        taken = kept.get(row["host"], 0)\n        if taken >= ZONE_QUEUE_CAP:\n            continue\n        kept[row["host"]] = taken + 1\n        capped.append(row)\n    return capped\n\n\ndef export_report(events: list[dict], output_dir: Path, controls: list[dict]) -> dict:\n    output_dir.mkdir(parents=True, exist_ok=True)\n    canonical = canonical_events(events)\n    sessions = build_sessions(canonical, controls)\n    queue = build_queue(sessions)\n\n    run_counts = {name: 0 for name in CLASS_ORDER}\n    for row in canonical:\n        run_counts[row["run_class"]] += 1\n\n    all_rows = [r for rows in sessions.values() for r in rows]\n    matrix = {\n        host: {\n            "session_count": len(rows),\n            "total_runtime_ms": sum(r["runtime_ms"] for r in rows),\n            "total_ledger_runtime_ms": sum(r["ledger_runtime_ms"] for r in rows),\n            "max_carry_out_ms": max((r["carry_out_ms"] for r in rows), default=0),\n            "queued_count": sum(1 for r in queue if r["host"] == host),\n        }\n        for host, rows in sessions.items()\n    }\n\n    canonical_payload = "\\n".join(\n        f"{r[\'exec_id\']}|{r[\'image_ref\']}|{r[\'run_class\']}|{r[\'host\']}|{r[\'started_ms\']}"\n        f"|{r[\'ended_ms\']}|{1 if r[\'killed\'] else 0}" for r in canonical\n    )\n    control_payload = "\\n".join(\n        f"{r[\'layer\']}|{r[\'scope\']}|{_norm_host(r[\'host\'])}|{_norm_ms(r[\'start_ms\'])}|{_norm_ms(r[\'end_ms\'])}"\n        for r in sorted(controls, key=lambda r: (\n            str(r["layer"]), str(r["scope"]), _norm_host(r["host"]), _norm_ms(r["start_ms"])))\n    )\n    queue_payload = "\\n".join(\n        f"{r[\'incident_id\']}|{r[\'priority\']}|{r[\'ledger_runtime_ms\']}|{r[\'burst_digest\']}" for r in queue\n    )\n\n    summary = {\n        "schema_version": SCHEMA_VERSION,\n        "raw_exec_count": len(events),\n        "unique_exec_ids": len({str(e.get("exec_id", "")).strip() for e in events if str(e.get("exec_id", "")).strip()}),\n        "canonical_exec_count": len(canonical),\n        "run_counts": run_counts,\n        "hosts": sorted(sessions),\n        "host_count": len(sessions),\n        "killed_excluded_count": sum(1 for r in canonical if r["killed"]),\n        "session_count": len(all_rows),\n        "total_runtime_ms": sum(r["runtime_ms"] for r in all_rows),\n        "total_adjusted_runtime_ms": sum(r["adjusted_runtime_ms"] for r in all_rows),\n        "total_ledger_runtime_ms": sum(r["ledger_runtime_ms"] for r in all_rows),\n        "total_sandbox_overlap_ms": sum(r["sandbox_overlap_ms"] for r in all_rows),\n        "total_audit_overlap_ms": sum(r["audit_overlap_ms"] for r in all_rows),\n        "max_ledger_runtime_ms": max((r["ledger_runtime_ms"] for r in all_rows), default=0),\n        "max_carry_out_ms": max((r["carry_out_ms"] for r in all_rows), default=0),\n        "longest_session_ms": max((r["runtime_ms"] for r in all_rows), default=0),\n        "contained_count": len(queue),\n        "priority_counts": {\n            name: sum(1 for r in queue if r["priority"] == name) for name in PRIORITY_ORDER\n        },\n        "canonical_exec_checksum": hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),\n        "exec_policy_checksum": hashlib.sha256(control_payload.encode("utf-8")).hexdigest(),\n        "containment_checksum": hashlib.sha256(queue_payload.encode("utf-8")).hexdigest(),\n    }\n\n    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\\n", encoding="utf-8")\n    (output_dir / "host_matrix.json").write_text(json.dumps(matrix, indent=2) + "\\n", encoding="utf-8")\n    with (output_dir / "contained.jsonl").open("w", encoding="utf-8") as handle:\n        for row in queue:\n            handle.write(json.dumps(row, separators=(",", ":")) + "\\n")\n    return summary\n\n\ndef main() -> None:\n    parser = argparse.ArgumentParser()\n    parser.add_argument("--input", default="/app/data/exec_events.json")\n    parser.add_argument("--output-dir", default="/app/output")\n    args = parser.parse_args()\n\n    events = load_events(Path(args.input))\n    export_report(events, Path(args.output_dir), load_controls())\n    print(f"Wrote containment rollup to {args.output_dir}")\n\n\nif __name__ == "__main__":\n    main()\n'


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def load_events(path: Path = EVENTS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def input_stats(events: list[dict]) -> dict:
    ids = [str(e.get("exec_id", "")).strip() for e in events]
    present = [i for i in ids if i]
    return {
        "raw_exec_count": len(events),
        "unique_exec_ids": len(set(present)),
        "duplicate_exec_ids": len(present) - len(set(present)),
        "killed_row_count": sum(
            1 for e in events
            if (e.get("killed") is True)
            or (isinstance(e.get("killed"), str) and e["killed"].strip().lower() in {"true", "1", "yes"})
        ),
    }


def frozen_audit() -> dict:
    raw = FROZEN_PATH.read_bytes()
    return {
        "frozen_sha256": hashlib.sha256(raw).hexdigest(),
        "frozen_byte_count": len(raw),
    }


def _line_has_all(line: str, terms: list[str]) -> bool:
    low = line.lower()
    return all(t.lower() in low for t in terms)


def find_dossier_quote(text: str, terms: list[str]) -> str:
    """First line of the dossier containing every term, returned VERBATIM."""
    for line in text.splitlines():
        if line.strip() and _line_has_all(line, terms):
            return line.strip()
    raise SystemExit(f"no dossier line matches {terms}")


def find_pipeline_evidence(source: str, terms: list[str]) -> str:
    """First line of the FROZEN workflow containing every term, VERBATIM."""
    for line in source.splitlines():
        if line.strip() and _line_has_all(line, terms):
            return line.strip()
    raise SystemExit(f"no pipeline line matches {terms}")


def build_issues(dossier: str, frozen: str, spec: dict) -> list[dict]:
    issues = []
    for entry in spec["known_defects"]:
        issues.append({
            "defect_id": entry["defect_id"],
            "stage": entry["stage"],
            "dossier_quote": find_dossier_quote(dossier, entry["dossier_terms"]),
            "pipeline_evidence": find_pipeline_evidence(frozen, entry["pipeline_terms"]),
            "repair_action": entry["repair_action"],
        })
    issues.sort(key=lambda row: row["defect_id"])
    return issues


def build_diagnosis(dossier: str, frozen: str, spec: dict, events: list[dict]) -> dict:
    issues = build_issues(dossier, frozen, spec)
    payload = "\n".join(
        f"{i['defect_id']}|{i['stage']}|{i['repair_action']}" for i in issues
    )
    return {
        "schema_version": spec["diagnosis_report"]["schema_version"],
        "input_stats": input_stats(events),
        "defect_count": len(issues),
        "defects": issues,
        "diagnosis_checksum": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def patch_workflow() -> None:
    """Write the repaired pipeline to disk BEFORE it is loaded or run."""
    WORKFLOW_PATH.write_text(REPAIRED_SOURCE, encoding="utf-8")


def cmd_diagnose(dossier_path: Path, report_path: Path) -> None:
    spec = load_spec()
    report = build_diagnosis(
        dossier_path.read_text(encoding="utf-8"),
        FROZEN_PATH.read_text(encoding="utf-8"),
        spec,
        load_events(),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote diagnosis to {report_path}")


def cmd_repair(output_dir: Path) -> None:
    spec = load_spec()
    before = frozen_audit()
    dossier = DOSSIER_PATH.read_text(encoding="utf-8")
    frozen = FROZEN_PATH.read_text(encoding="utf-8")
    events = load_events()

    patch_workflow()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(WORKFLOW_PATH), "--output-dir", str(output_dir)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"repaired workflow failed: {result.stderr}")

    diagnosis = build_diagnosis(dossier, frozen, spec, events)
    (output_dir / "diagnosis.json").write_text(
        json.dumps(diagnosis, indent=2) + "\n", encoding="utf-8")

    repaired_bytes = WORKFLOW_PATH.read_bytes()
    removed = [t for t in spec["workflow_repair"]["forbidden_tokens"]
               if t not in repaired_bytes.decode("utf-8")]
    audit = {
        "schema_version": spec["repair_audit"]["schema_version"],
        "pre_repair_sha256": before["frozen_sha256"],
        "pre_repair_byte_count": before["frozen_byte_count"],
        "post_repair_sha256": hashlib.sha256(repaired_bytes).hexdigest(),
        "post_repair_byte_count": len(repaired_bytes),
        "defects_repaired": [i["defect_id"] for i in diagnosis["defects"]],
        "forbidden_tokens_removed": sorted(removed),
        "artifacts": sorted(p.name for p in output_dir.iterdir() if p.is_file()),
    }
    audit["artifacts"] = sorted(set(audit["artifacts"]) | {"repair_audit.json"})
    (output_dir / "repair_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"Repaired workflow and wrote artifacts to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Warden exec-access containment audit")
    sub = parser.add_subparsers(dest="command", required=True)

    diag = sub.add_parser("diagnose")
    diag.add_argument("--dossier", default=str(DOSSIER_PATH))
    diag.add_argument("--report", default="/app/output/diagnosis.json")

    rep = sub.add_parser("repair")
    rep.add_argument("--output-dir", default="/app/output")

    args = parser.parse_args()
    if args.command == "diagnose":
        cmd_diagnose(Path(args.dossier), Path(args.report))
    else:
        cmd_repair(Path(args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
