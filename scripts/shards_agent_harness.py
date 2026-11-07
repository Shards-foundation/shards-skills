#!/usr/bin/env python3
"""Bounded, local dual-channel sub-agent harness for reviewed read-only Shards checks.

This is NOT an Agent2Agent network endpoint or an A2A protocol implementation.
It performs local one-level delegation and concurrent execution of audited
first-party operations, with separate control and evidence channels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import dispatch_skills

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports" / "agent-harness"
ALLOWED = frozenset({
    "shards-repository-health",
    "shards-catalogue-sync",
    "shards-skill-dispatch",
})
PRESETS = {
    "a2a": ("shards-repository-health", "shards-skill-dispatch"),
    "dual-channel": ("shards-repository-health", "shards-catalogue-sync"),
    "subagents": ("shards-catalogue-sync", "shards-skill-dispatch"),
    "swarm": ("shards-repository-health", "shards-catalogue-sync",
              "shards-skill-dispatch"),
}
FIXED_ACTIONS = {
    "a2a-check": "a2a",
    "dual-channel-check": "dual-channel",
    "subagent-check": "subagents",
    "swarm-check": "swarm",
}
NAME = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
MAX_TASKS = 8
MAX_WORKERS = 4


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_plan(profile: str, *, skills: list[str] | None = None,
               workers: int | None = None) -> dict:
    """Resolve only pinned first-party dispatcher operations; never import skill code."""
    if profile not in (*PRESETS, "custom"):
        raise ValueError("Unknown harness profile")
    if skills and profile != "custom":
        raise ValueError("Preset profile does not accept unreviewed skill overrides")
    if profile == "custom":
        if not skills:
            raise ValueError("Custom profile requires at least one --skill")
        selected = list(skills)
    else:
        selected = list(PRESETS[profile])
    if not 1 <= len(selected) <= MAX_TASKS:
        raise ValueError("Task count exceeds the bounded agent limit")
    if any(not isinstance(skill, str) or not NAME.fullmatch(skill) or
           skill not in ALLOWED or dispatch_skills.REGISTRY.get(skill, (None,))[0] != "read-only"
           for skill in selected):
        raise ValueError("Delegation target is not on the reviewed read-only allowlist")
    parallel = profile == "swarm" or profile == "custom"
    capacity = min(MAX_WORKERS, len(selected)) if parallel else 1
    if workers is not None:
        if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
            raise ValueError("Workers must be between 1 and 4")
        if not parallel and workers != 1:
            raise ValueError("Non-swarm profiles execute sequentially")
        capacity = min(workers, len(selected))
    tasks = []
    for index, skill in enumerate(selected, start=1):
        tasks.append({
            "task_id": f"task-{index:03d}",
            "agent_id": f"subagent-{index:03d}",
            "skill": skill,
            "dispatch_plan": dispatch_skills.describe(skill),
        })
    plan = {
        "profile": profile,
        "protocol": "local-shards-harness-v1",
        "a2a_network_compatible": False,
        "channels": ["control", "data"],
        "execution": "one-level-read-only-delegation",
        "workers": capacity,
        "tasks": tasks,
        "executed": False,
        "host_approval_required": True,
    }
    plan["plan_sha256"] = fingerprint(plan)
    return plan


def _execute_one(task: dict, runner) -> dict:
    try:
        receipt = runner(task["dispatch_plan"])
        observation = receipt["observation"]
        outcome = observation["status"]
        if outcome not in ("pass", "fail", "hold", "timeout", "error"):
            raise ValueError("Unexpected sub-agent outcome")
        return {
            "status": outcome,
            "receipt_id": receipt["receipt_id"],
            "script_sha256": receipt["script_sha256"],
            "exit_code": observation.get("exit_code"),
            "stdout_tail": observation.get("stdout_tail", ""),
            "stderr_tail": observation.get("stderr_tail", ""),
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {
            "status": "error",
            "error_type": type(exc).__name__,
            "exit_code": None,
        }


def execute(plan: dict, *, runner=None) -> dict:
    """Fail on altered plans, then fan out within explicit concurrency limits."""
    if runner is None:
        runner = dispatch_skills.run
    if not isinstance(plan, dict) or plan.get("executed") is not False:
        raise ValueError("Execution requires an unexecuted validated plan")
    expected = build_plan(
        plan["profile"],
        skills=[task["skill"] for task in plan["tasks"]] if plan["profile"] == "custom" else None,
        workers=plan["workers"],
    )
    if plan.get("plan_sha256") != fingerprint({key: value for key, value in plan.items()
                                               if key != "plan_sha256"}):
        raise ValueError("Plan fingerprint mismatch")
    # Independent regeneration verifies exact registry mapping, source bytes and
    # plan data against the current checkout rather than trusting user JSON.
    if plan != expected:
        raise ValueError("Harness plan changed or local revision drifted")
    started = now()
    tasks = plan["tasks"]
    control = [{
        "channel": "control", "sequence": 0, "event": "swarm-started",
        "profile": plan["profile"], "task_count": len(tasks),
        "workers": plan["workers"], "occurred_at": started,
    }]
    for task in tasks:
        control.append({
            "channel": "control", "sequence": len(control), "event": "delegated",
            "task_id": task["task_id"], "agent_id": task["agent_id"], "skill": task["skill"],
        })
    if plan["workers"] == 1:
        results = [_execute_one(task, runner) for task in tasks]
    else:
        with ThreadPoolExecutor(max_workers=plan["workers"],
                                thread_name_prefix="shards-subagent") as executor:
            results = list(executor.map(lambda task: _execute_one(task, runner), tasks))
    data = []
    for task, observed in zip(tasks, results):
        control.append({
            "channel": "control", "sequence": len(control),
            "event": "completed" if observed["status"] == "pass" else "failed",
            "task_id": task["task_id"], "agent_id": task["agent_id"],
            "status": observed["status"],
        })
        data.append({
            "channel": "data", "task_id": task["task_id"],
            "agent_id": task["agent_id"], "skill": task["skill"],
            "artifact": observed,
        })
    passed = all(result["status"] == "pass" for result in results)
    control.append({
        "channel": "control", "sequence": len(control),
        "event": "swarm-finished", "status": "pass" if passed else "fail",
    })
    record = {
        "schema_version": 1,
        "run_id": str(uuid.uuid4()),
        "profile": plan["profile"],
        "protocol": "local-shards-harness-v1",
        "a2a_network_compatible": False,
        "plan_sha256": plan["plan_sha256"],
        "started_at": started, "finished_at": now(),
        "status": "pass" if passed else "fail",
        "executed": True, "workers": plan["workers"],
        "summary": {"total": len(tasks), "passed": sum(r["status"] == "pass" for r in results),
                    "failed": sum(r["status"] != "pass" for r in results)},
        "control_channel": control,
        "data_channel": data,
        "scope": "local-approved-read-only-skill-operations",
    }
    # Evidentiary integrity checksum: not a signature or tamper-proof log.
    record["receipt_sha256"] = fingerprint(record)
    return record


def persist(record: dict, directory: Path = REPORTS) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (record["run_id"] + ".json")
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return destination


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    for action in ("plan", "run"):
        item = sub.add_parser(action)
        item.add_argument("--profile", choices=sorted((*PRESETS, "custom")), required=True)
        item.add_argument("--skill", action="append", help="Repeat for custom read-only delegates")
        item.add_argument("--workers", type=int)
        if action == "run":
            item.add_argument("--execute", action="store_true")
            item.add_argument("--save-receipt", action="store_true")
    for action in FIXED_ACTIONS:
        item = sub.add_parser(action)
        item.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "list":
            output = {"profiles": {k: list(v) for k, v in PRESETS.items()},
                      "allowed_delegates": sorted(ALLOWED),
                      "max_tasks": MAX_TASKS, "max_workers": MAX_WORKERS,
                      "a2a_network_compatible": False}
            print(json.dumps(output, indent=2))
            return 0
        if args.action in FIXED_ACTIONS:
            if not args.execute:
                raise ValueError("Fixed action requires explicit --execute")
            profile = FIXED_ACTIONS[args.action]
            plan = build_plan(profile)
            record = execute(plan)
        elif args.action == "plan":
            print(json.dumps(build_plan(args.profile, skills=args.skill, workers=args.workers),
                             indent=2))
            return 0
        else:
            if not args.execute:
                raise ValueError("Run requires explicit --execute")
            plan = build_plan(args.profile, skills=args.skill, workers=args.workers)
            record = execute(plan)
            if args.save_receipt:
                record["report_path"] = str(persist(record))
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0 if record["status"] == "pass" else 1
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__,
                          "error": str(exc) if isinstance(exc, ValueError) else "Invalid harness request"}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
