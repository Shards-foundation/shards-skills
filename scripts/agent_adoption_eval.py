#!/usr/bin/env python3
"""Measure skill retrieval; separately evaluate host-supplied agent-use traces.

Neither a ranked result nor a host-supplied trace proves real agent adoption.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from search_skills import ROOT, catalogue_entries, curated_entries, rank

SHA = re.compile(r"^[0-9a-f]{40}$")


def load_cases(path: Path) -> list[dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        raise ValueError("Missing, symlinked or oversized case file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported case schema")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Expected a nonempty cases list")
    for idx, case in enumerate(cases):
        if not isinstance(case, dict) or type(case.get("should_trigger")) is not bool:
            raise ValueError(f"Invalid trigger case {idx}")
        if not isinstance(case.get("skill"), str) or not isinstance(case.get("prompt"), str):
            raise ValueError(f"Invalid case fields {idx}")
        if not case["skill"].strip() or not case["prompt"].strip():
            raise ValueError(f"Blank case fields {idx}")
    return cases


def retrieval_report(cases: list[dict], entries: list[dict]) -> dict:
    results = []
    hits = {1: 0, 3: 0, 5: 0}
    positives = 0
    for idx, case in enumerate(cases):
        ordered = rank(entries, case["prompt"])
        names = [match["name"] for match in ordered]
        position = names.index(case["skill"]) + 1 if case["skill"] in names else None
        if case["should_trigger"]:
            positives += 1
            for k in hits:
                hits[k] += int(position is not None and position <= k)
        results.append({"case_id": str(idx + 1), "target_skill": case["skill"],
                        "expected_trigger": case["should_trigger"],
                        "rank": position, "top_3": names[:3],
                        "agent_activation_verified": False})
    return {"evaluation": "metadata_retrieval_only", "case_count": len(cases),
            "positive_count": positives,
            "recall_at_1": hits[1] / positives if positives else None,
            "recall_at_3": hits[3] / positives if positives else None,
            "recall_at_5": hits[5] / positives if positives else None,
            "negative_trigger_assessed": False,
            "caution": "Ranking is not an agent invocation. Negative triggers require host traces.",
            "results": results}


def host_report(cases: list[dict], receipts: dict) -> dict:
    """Check reported decisions without claiming independent verification of host activity."""
    if not isinstance(receipts, dict) or receipts.get("schema_version") != 1:
        raise ValueError("Unsupported host receipt schema")
    if not isinstance(receipts.get("host"), str) or not receipts["host"].strip():
        raise ValueError("Host identification is required")
    sha = receipts.get("repository_commit")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("A full lowercase repository commit SHA is required")
    runs = receipts.get("runs")
    if not isinstance(runs, list):
        raise ValueError("Runs must be a list")
    by_id = {}
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("case_id"), str):
            raise ValueError("Malformed host run")
        cid = run["case_id"]
        if cid not in {str(i + 1) for i in range(len(cases))} or cid in by_id:
            raise ValueError("Unknown or duplicate case id")
        for key in ("selected_skill", "skill_opened", "procedure_applied", "trace_reference", "task_outcome"):
            if key not in run:
                raise ValueError("Missing host-run field: " + key)
        if run["selected_skill"] is not None and not isinstance(run["selected_skill"], str):
            raise ValueError("Invalid selected_skill")
        if type(run["skill_opened"]) is not bool or type(run["procedure_applied"]) is not bool:
            raise ValueError("Invalid use flags")
        if not isinstance(run["trace_reference"], str):
            raise ValueError("Invalid trace reference")
        if run["task_outcome"] not in ("pass", "fail", "blocked", "not_run"):
            raise ValueError("Invalid task outcome")
        by_id[cid] = run
    results = []
    for i, case in enumerate(cases):
        cid = str(i + 1)
        run = by_id.get(cid)
        if run is None:
            result = "not_run"
        else:
            # Never guess which skill was opened from a boolean alone.
            touched_target = run["selected_skill"] == case["skill"]
            unidentified_open = run["skill_opened"] and run["selected_skill"] is None
            invoked_target = (run["selected_skill"] == case["skill"] and
                              run["skill_opened"] and run["procedure_applied"])
            if case["should_trigger"]:
                result = ("reported_use" if invoked_target and
                          bool(run["trace_reference"].strip()) and
                          run["task_outcome"] == "pass" else "not_demonstrated")
            else:
                result = ("reported_false_trigger" if touched_target else
                          "not_demonstrated" if unidentified_open else
                          "reported_appropriate_abstention" if
                          bool(run["trace_reference"].strip()) and
                          run["task_outcome"] == "pass" else "not_demonstrated")
        results.append({"case_id": cid, "target_skill": case["skill"],
                        "expected_trigger": case["should_trigger"], "result": result})
    return {"evaluation": "self_reported_host_trace", "host": receipts["host"],
            "repository_commit": sha, "independently_verified": False,
            "warning": "Receipts are untrusted self-reports; inspect original host logs and task outputs.",
            "results": results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "evals" / "trigger-cases.json")
    parser.add_argument("--receipts", type=Path, help="Host-produced JSON trace summary (not a proof)")
    args = parser.parse_args(argv)
    try:
        cases = load_cases(args.cases)
        if args.receipts:
            if args.receipts.is_symlink() or args.receipts.stat().st_size > 1_000_000:
                raise ValueError("Symlinked or oversized receipt file")
            receipts = json.loads(args.receipts.read_text(encoding="utf-8"))
            report = host_report(cases, receipts)
        else:
            report = retrieval_report(cases, catalogue_entries() + curated_entries())
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
