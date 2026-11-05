#!/usr/bin/env python3
"""Bounded Shards automation: explicit, trusted workflow allowlist."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = {
    "catalogue-check": (["scripts/catalogue_sync.py", "--check"], 45),
    "skill-metadata": (["scripts/validate_skills.py"], 90),
    "security-lint": (["scripts/security_lint.py"], 90),
    "portfolio-audit": (["scripts/audit_portfolio.py"], 90),
    "plugin-audit": (["plugins/shards-core/scripts/run.py", "audit-skill", "--path",
                      "plugins/shards-core/skills/shards-skill-audit"], 30),
    "unit-tests": (["-m", "unittest", "discover", "-s", "tests", "-v"], 150),
}
WORKFLOWS = {
    "quick": ("catalogue-check", "skill-metadata", "plugin-audit"),
    "weekly": ("catalogue-check", "skill-metadata", "security-lint", "portfolio-audit"),
    "verify": ("catalogue-check", "skill-metadata", "security-lint", "plugin-audit", "unit-tests"),
}
CREDENTIAL = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})")

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def command_for(step: str) -> tuple[list[str], int]:
    if step not in STEPS:
        raise ValueError("Untrusted step: " + step)
    args, timeout = STEPS[step]
    if args[0] == "-m":
        return [sys.executable, *args], timeout
    return [sys.executable, str(ROOT / args[0]), *args[1:]], timeout

def plan(workflow: str) -> dict:
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    return {"workflow": workflow, "mode": "plan", "steps": [
        {"id": name, "argv": command_for(name)[0], "timeout_seconds": command_for(name)[1]}
        for name in WORKFLOWS[workflow]], "executed": False}

def safe_tail(data: str) -> str:
    return CREDENTIAL.sub("[REDACTED]", data)[-2400:]

def run_workflow(workflow: str, *, execute: bool, fail_fast: bool = False,
                 run_command=None) -> dict:
    if not execute:
        return plan(workflow)
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    if run_command is None:
        run_command = subprocess.run
    entries = []
    for name in WORKFLOWS[workflow]:
        argv, limit = command_for(name)
        env = dict(os.environ)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        started = now()
        try:
            proc = run_command(argv, cwd=str(ROOT), capture_output=True, text=True,
                               timeout=limit, check=False, env=env)
            entry = {"id": name, "status": "passed" if proc.returncode == 0 else "failed",
                     "exit_code": proc.returncode, "command": argv, "started_at": started,
                     "finished_at": now(), "stdout_tail": safe_tail(proc.stdout),
                     "stderr_tail": safe_tail(proc.stderr)}
        except subprocess.TimeoutExpired:
            entry = {"id": name, "status": "timeout", "exit_code": None, "command": argv,
                     "started_at": started, "finished_at": now(), "error": f"Timeout {limit}s"}
        except OSError as error:
            entry = {"id": name, "status": "error", "exit_code": None, "command": argv,
                     "started_at": started, "finished_at": now(), "error": type(error).__name__}
        entries.append(entry)
        if fail_fast and entry["status"] != "passed":
            break
    failures = [item["id"] for item in entries if item["status"] != "passed"]
    return {"workflow": workflow, "mode": "executed",
            "status": "pass" if not failures else "fail", "executed": True,
            "completed": len(entries), "total": len(WORKFLOWS[workflow]),
            "failed_steps": failures, "steps": entries,
            "note": "No imported skill code, remote writes, deployments or publishing actions executed."}

def write_report(folder: Path, report: dict) -> Path:
    folder = folder.expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / ("automation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    with dest.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return dest

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("list")
    p = subs.add_parser("plan")
    p.add_argument("--workflow", required=True, choices=sorted(WORKFLOWS))
    r = subs.add_parser("run")
    r.add_argument("--workflow", required=True, choices=sorted(WORKFLOWS))
    r.add_argument("--output-dir", type=Path)
    r.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "list":
        report = {"workflows": {k: list(v) for k, v in WORKFLOWS.items()}}
    elif args.action == "plan":
        report = plan(args.workflow)
    else:
        report = run_workflow(args.workflow, execute=True, fail_fast=args.fail_fast)
        if args.output_dir:
            report["report_path"] = str(write_report(args.output_dir, report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(args.action == "run" and report["status"] != "pass")

if __name__ == "__main__":
    raise SystemExit(main())
