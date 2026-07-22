#!/usr/bin/env python3
"""Process-execution containment rollup deployed during the Warden incident.

This build is producing an unreliable containment queue. It is the artifact the
response team asked to have investigated and restored.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA_VERSION = "exec-containment-v2"
CLASS_ORDER = ["system", "service", "batch", "adhoc"]


def load_events(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def export_report(events: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    run_counts = {name: 0 for name in CLASS_ORDER}
    hosts: set[str] = set()
    for event in events:
        run_class = str(event.get("run_class", ""))
        if run_class in run_counts:
            run_counts[run_class] += 1
        hosts.add(str(event.get("host", "")))

    contained = []
    for event in events:
        if event.get("run_class") == "system":
            contained.append(
                {
                    "exec_id": event["exec_id"],
                    "entered_ms": event["granted_at"] if "granted_at" in event else 0,
                    "run_class": event["run_class"],
                    "host": event["host"],
                    "binary": event["binary"],
                }
            )

    contained.sort(key=lambda row: row["entered_ms"])

    summary = {
        "schema_version": SCHEMA_VERSION,
        "raw_exec_count": len(events),
        "unique_exec_ids": len({str(event["exec_id"]) for event in events}),
        "total_execs": len(events),
        "run_counts": run_counts,
        "hosts": sorted(hosts),
        "contained_count": len(contained),
        "killed_excluded_count": 0,
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output_dir / "host_matrix.json").write_text(json.dumps({}, indent=2) + "\n")
    with (output_dir / "contained.jsonl").open("w", encoding="utf-8") as handle:
        for row in contained:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/app/data/exec_events.json")
    parser.add_argument("--output-dir", default="/app/output")
    args = parser.parse_args()

    events = load_events(Path(args.input))
    export_report(events, Path(args.output_dir))
    print(f"Wrote containment rollup to {args.output_dir}")


if __name__ == "__main__":
    main()
