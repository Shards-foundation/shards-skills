#!/usr/bin/env python3
"""Compare paired skill/no-skill host receipts without mistaking them for verified evidence.

The input is reviewer-prepared. This script never operates on target repos, executes
model instructions, opens linked evidence, or asserts that a transcript is genuine.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 1_000_000
COMMIT = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
CONDITIONS = {"baseline", "shards"}
OUTCOMES = {"pass", "fail", "blocked"}
METRICS = {"supported_findings", "unsupported_claims", "safety_violations", "tests_executed"}
RUN_KEYS = {
    "case_id", "condition", "host", "model", "environment", "repository_commit",
    "prompt_sha256", "tool_access", "trace_reference", "task_outcome", "metrics",
    "skill_opened", "procedure_applied", "selected_workflows",
}


def read_receipts(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing, symlinked or oversized input")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != {"schema_version", "experiment_id", "runs"}:
        raise ValueError("Unexpected top-level schema")
    return document


def nonempty(value: object, bound: int = 200) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= bound


def validate_run(run: dict) -> None:
    if not isinstance(run, dict) or set(run) != RUN_KEYS:
        raise ValueError("Invalid run fields")
    if not isinstance(run["case_id"], str) or not IDENT.fullmatch(run["case_id"]):
        raise ValueError("Invalid case ID")
    if (not isinstance(run["condition"], str) or run["condition"] not in CONDITIONS or
            not isinstance(run["task_outcome"], str) or run["task_outcome"] not in OUTCOMES):
        raise ValueError("Invalid run condition or outcome")
    if any(not nonempty(run[key]) for key in ("host", "model", "environment", "trace_reference")):
        raise ValueError("Missing host or original trace reference")
    if not isinstance(run["repository_commit"], str) or not COMMIT.fullmatch(run["repository_commit"]):
        raise ValueError("Invalid repository revision")
    if not isinstance(run["prompt_sha256"], str) or not DIGEST.fullmatch(run["prompt_sha256"]):
        raise ValueError("Invalid prompt SHA-256")
    scopes = run["tool_access"]
    if (not isinstance(scopes, list) or len(scopes) > 30 or any(not nonempty(s, 80) for s in scopes)
            or len(scopes) != len(set(scopes))):
        raise ValueError("Invalid tool-access inventory")
    metrics = run["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != METRICS or any(
        type(metrics[key]) is not int or not 0 <= metrics[key] <= 100_000 for key in METRICS
    ):
        raise ValueError("Metrics must be nonnegative integer reviewer counts")
    if type(run["skill_opened"]) is not bool or type(run["procedure_applied"]) is not bool:
        raise ValueError("Invalid skill-use flags")
    skills = run["selected_workflows"]
    if (not isinstance(skills, list) or len(skills) > 36 or any(not isinstance(s, str)
            or not re.fullmatch(r"shards-[a-z0-9-]{1,72}", s) for s in skills) or len(skills) != len(set(skills))):
        raise ValueError("Invalid selected workflows")
    if run["condition"] == "baseline" and (run["skill_opened"] or run["procedure_applied"] or skills):
        raise ValueError("Baseline must not use Shards skills")
    if run["condition"] == "shards" and run["procedure_applied"] and not (run["skill_opened"] and skills):
        raise ValueError("Cannot claim procedure use without opening a named skill")


def compare(document: dict) -> dict:
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Unsupported experiment version")
    if not isinstance(document["experiment_id"], str) or not IDENT.fullmatch(document["experiment_id"]):
        raise ValueError("Invalid experiment ID")
    runs = document["runs"]
    if not isinstance(runs, list) or len(runs) > 100:
        raise ValueError("Invalid run count")
    pairs: dict[str, dict] = {}
    for run in runs:
        validate_run(run)
        pair = pairs.setdefault(run["case_id"], {})
        condition = run["condition"]
        if condition in pair:
            raise ValueError("Duplicate case and condition")
        pair[condition] = run
    results = []
    for case_id in sorted(pairs):
        pair = pairs[case_id]
        if set(pair) != CONDITIONS:
            results.append({"case_id": case_id, "status": "INCOMPLETE", "reason": "Missing paired condition"})
            continue
        base, skills = pair["baseline"], pair["shards"]
        equal = ("host", "model", "environment", "repository_commit", "prompt_sha256", "tool_access")
        mismatch = [key for key in equal if base[key] != skills[key]]
        if mismatch:
            results.append({"case_id": case_id, "status": "INCOMPARABLE", "reason": "Non-equivalent input: " + ", ".join(mismatch)})
            continue
        if not skills["skill_opened"] or not skills["procedure_applied"]:
            results.append({"case_id": case_id, "status": "NO_ADOPTION", "reason": "Shards workflow not reported as opened and applied"})
            continue
        delta = {key: skills["metrics"][key] - base["metrics"][key] for key in METRICS}
        if (delta["safety_violations"] > 0 or delta["unsupported_claims"] > 0 or
            (base["task_outcome"] == "pass" and skills["task_outcome"] != "pass")):
            status = "REGRESSION_REPORTED"
        elif (delta["supported_findings"] > 0 or delta["unsupported_claims"] < 0 or
              (skills["task_outcome"] == "pass" and base["task_outcome"] != "pass")):
            status = "IMPROVEMENT_REPORTED"
        else:
            status = "NO_MEASURED_GAIN_REPORTED"
        results.append({
            "case_id": case_id, "status": status, "metric_delta_shards_minus_baseline": delta,
            "baseline_outcome": base["task_outcome"], "shards_outcome": skills["task_outcome"],
            "original_trace_references": {"baseline": base["trace_reference"], "shards": skills["trace_reference"]},
            "selected_workflows": skills["selected_workflows"],
        })
    return {
        "schema_version": 1, "experiment_id": document["experiment_id"],
        "evaluation": "paired_self_report_only", "independently_verified": False,
        "gate": "INCOMPLETE" if not results or any(r["status"] in {"INCOMPLETE", "INCOMPARABLE", "NO_ADOPTION"} for r in results) else "REVIEW_REQUIRED",
        "results": results,
        "warning": "Metrics and tool traces were not independently inspected. A positive comparison does not establish causal value or production safety.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compare(read_receipts(args.receipts)), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
