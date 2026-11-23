#!/usr/bin/env python3
"""Bounded Shards automation: explicit, trusted workflow allowlist."""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = {
    "catalogue-check": (["scripts/catalogue_sync.py", "--check"], 45),
    "skill-metadata": (["scripts/validate_skills.py"], 90),
    "security-lint": (["scripts/security_lint.py"], 90),
    "portfolio-audit": (["scripts/audit_portfolio.py"], 90),
    "plugin-integrity": (["scripts/verify_plugins.py", "--check"], 45),
    "plugin-audit": (["plugins/shards-core/scripts/run.py", "audit-skill", "--path",
                      "plugins/shards-core/skills/shards-skill-audit"], 30),
    "unit-tests": (["-m", "unittest", "discover", "-s", "tests", "-v"], 150),
}
WORKFLOWS = {
    "quick": ("catalogue-check", "skill-metadata", "plugin-integrity", "plugin-audit"),
    "weekly": ("catalogue-check", "skill-metadata", "security-lint", "portfolio-audit", "plugin-integrity"),
    "verify": ("catalogue-check", "skill-metadata", "security-lint", "plugin-integrity", "plugin-audit", "unit-tests"),
}
CREDENTIAL = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})", re.I)
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    re.DOTALL)
# Deliberately narrow: do not send runner credentials or Python import overrides
# into maintenance subprocesses. This is environment minimisation, not sandboxing.
SAFE_ENV_KEYS = frozenset({
    "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
    "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL", "TZ", "CI", "GITHUB_ACTIONS",
})


def execution_environment(source=None) -> dict[str, str]:
    if source is None:
        source = os.environ
    env = {key: value for key, value in source.items() if key in SAFE_ENV_KEYS}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONNOUSERSITE="1")
    return env


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def source_revision() -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-prefix", "--verify", "HEAD^{commit}"],
                              cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=5, check=False, env=execution_environment())
    except (OSError, subprocess.TimeoutExpired):
        return None
    # A source archive nested inside an unrelated checkout has no revision of its own.
    match = re.fullmatch(r"\n([0-9a-f]{40}|[0-9a-f]{64})\n", proc.stdout)
    return match[1] if proc.returncode == 0 and match else None


def command_for(step: str) -> tuple[list[str], int]:
    if step not in STEPS:
        raise ValueError("Untrusted step: " + step)
    args, timeout = STEPS[step]
    if args[0] == "-m":
        return [sys.executable, *args], timeout
    script = ROOT / args[0]
    if script.is_symlink() or not script.is_file() or not script.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Trusted maintenance script missing, symlinked or outside checkout: " + args[0])
    return [sys.executable, str(script), *args[1:]], timeout

def plan(workflow: str) -> dict:
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    steps = []
    for name in WORKFLOWS[workflow]:
        argv, limit = command_for(name)
        steps.append({"id": name, "argv": argv, "timeout_seconds": limit})
    return {"workflow": workflow, "mode": "plan", "steps": steps, "executed": False}

def safe_tail(data: str) -> str:
    return CREDENTIAL.sub("[REDACTED]", PRIVATE_KEY_BLOCK.sub("[REDACTED]", data))[-2400:]

def run_workflow(workflow: str, *, execute: bool, fail_fast: bool = False,
                 run_command=None) -> dict:
    if not execute:
        return plan(workflow)
    if workflow not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    steps = WORKFLOWS[workflow]
    for name in steps:
        if name not in STEPS:
            raise ValueError("Untrusted step: " + name)
    if run_command is None:
        run_command = subprocess.run
    entries = []
    env = execution_environment()
    for name in steps:
        entry = {"id": name, "command": None, "exit_code": None, "started_at": now()}
        try:
            argv, limit = command_for(name)
            entry["command"] = argv
            proc = run_command(argv, cwd=str(ROOT), capture_output=True,
                               encoding="utf-8", errors="replace",
                               timeout=limit, check=False, env=env)
            entry.update(status="passed" if proc.returncode == 0 else "failed",
                         exit_code=proc.returncode, stdout_tail=safe_tail(proc.stdout),
                         stderr_tail=safe_tail(proc.stderr))
        except subprocess.TimeoutExpired as error:
            entry.update(status="timeout", error=f"Timeout {error.timeout}s")
        except (ValueError, OSError) as error:
            entry.update(status="error", error=safe_tail(str(error)))
        entry["finished_at"] = now()
        entries.append(entry)
        if fail_fast and entry["status"] != "passed":
            break
    failures = [item["id"] for item in entries if item["status"] != "passed"]
    return {"workflow": workflow, "mode": "executed",
            "status": "pass" if not failures else "fail", "executed": True,
            "completed": len(entries), "total": len(steps),
            "pending_steps": list(steps[len(entries):]),
            "failed_steps": failures, "steps": entries,
            "note": "No imported skill code, remote writes, deployments or publishing actions executed."}

def write_report(folder: Path, report: dict) -> Path:
    folder = folder.expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / ("automation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    fd, temporary = tempfile.mkstemp(prefix=".automation-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, dest)
    finally:
        Path(temporary).unlink(missing_ok=True)
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
    try:
        if args.action == "list":
            report = {"workflows": {k: list(v) for k, v in WORKFLOWS.items()}}
        elif args.action == "plan":
            report = plan(args.workflow)
            report["commit"] = source_revision()
        else:
            revision = source_revision()
            report = run_workflow(args.workflow, execute=True, fail_fast=args.fail_fast)
            report["commit"] = revision
            if args.output_dir:
                try:
                    report["report_path"] = str(write_report(args.output_dir, report))
                except OSError as error:
                    report.update(workflow_status=report["status"], status="error",
                                  report_error=safe_tail(str(error)))
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.action == "run" and report["status"] == "error":
            return 2
        return int(args.action == "run" and report["status"] != "pass")
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, sort_keys=True),
              file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
