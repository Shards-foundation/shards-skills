#!/usr/bin/env python3
"""Governed dispatcher for reviewed Shards skills; never evaluates skill-supplied commands."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "shards-core"
LOCAL_STATE = ROOT / ".shards" / "state"
REPORTS = ROOT / "reports" / "dispatch"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)

# Only these exact skill identifiers are dispatchable. No user-provided executable paths.
REGISTRY = {
    "shards-repository-health": ("read-only", "plugins/shards-core/scripts/run.py", "repository-health"),
    "shards-skill-audit": ("read-only", "plugins/shards-core/scripts/run.py", "audit-skill"),
    "shards-release-gate": ("read-only", "plugins/shards-core/scripts/run.py", "release-check"),
    "shards-agent-handoff": ("local-write", "plugins/shards-core/scripts/run.py", "handoff"),
    "shards-automation-operator": ("local-tests", "scripts/automate.py", "run"),
    "shards-catalogue-sync": ("read-only", "scripts/catalogue_sync.py", "--check"),
    "shards-skill-dispatch": ("read-only", "scripts/verify_plugins.py", "--check"),
}

def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _contained(path: Path, directory: Path) -> bool:
    return path.resolve().is_relative_to(directory.resolve())

def _repository_path(relative: str) -> Path:
    path = ROOT / relative
    if not _contained(path, ROOT) or not path.is_file() or path.is_symlink():
        raise ValueError("Trusted executable missing or outside checkout: " + relative)
    return path

def _selected_skill(name: str) -> Path:
    if not NAME.fullmatch(name):
        raise ValueError("Invalid target skill name")
    for base in (CORE / "skills", ROOT / "skills"):
        path = base / name
        if not _contained(path, base) or path.is_symlink():
            continue
        if (path / "SKILL.md").is_file() and not (path / "SKILL.md").is_symlink():
            return path.resolve()
    raise ValueError("Target skill not found")

def _state_file(raw: str, *, must_exist: bool) -> Path:
    if not raw:
        raise ValueError("Explicit checkpoint input and output required")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not _contained(path, LOCAL_STATE) or path.suffix.lower() != ".json":
        raise ValueError("Checkpoints must be JSON files inside .shards/state")
    if must_exist and not path.is_file():
        raise ValueError("Checkpoint input missing")
    if not must_exist and path.exists():
        raise ValueError("Checkpoint output already exists")
    return path

def _check_descriptor(skill_id: str) -> None:
    skill = CORE / "skills" / skill_id
    descriptor = skill / "SKILL.md"
    if not descriptor.is_file() or descriptor.is_symlink() or (skill / "UPSTREAM.md").exists():
        raise ValueError("Curated skill is missing or untrusted: " + skill_id)
    first = descriptor.read_text(encoding="utf-8")[:1000]
    if not first.startswith("---\n") or ("\nname: " + skill_id + "\n") not in first:
        raise ValueError("Curated skill frontmatter does not match: " + skill_id)

def _source_revision() -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                           text=True, capture_output=True, timeout=5, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def _plan_fingerprint(plan: dict) -> str:
    """Stable digest of the command and effects the operator actually reviewed."""
    fields = ("skill", "effect", "command", "script_sha256", "commit", "timeout_seconds")
    payload = {key: plan[key] for key in fields}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _check_plan_integrity(plan: dict) -> None:
    """Fail closed if a reviewed plan, trusted script or checkout changed."""
    skill = plan.get("skill")
    if skill not in REGISTRY:
        raise ValueError("Unknown curated skill in execution plan")
    _check_descriptor(skill)
    _, script_path, operation = REGISTRY[skill]
    script = _repository_path(script_path)
    command = plan.get("command")
    if (not isinstance(command, list) or len(command) < 3 or
            command[:3] != [sys.executable, str(script), operation]):
        raise ValueError("Execution plan command differs from curated registry")
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    expected_script = plan.get("script_sha256")
    if not isinstance(expected_script, str) or not hmac.compare_digest(digest, expected_script):
        raise ValueError("Trusted executable changed since planning")
    if plan.get("commit") != _source_revision():
        raise ValueError("Repository revision changed since planning")
    claimed = plan.get("plan_sha256")
    actual = _plan_fingerprint(plan)
    if not isinstance(claimed, str) or not hmac.compare_digest(actual, claimed):
        raise ValueError("Execution plan changed since planning")

def describe(skill_id: str, *, target_skill: str | None = None,
             profile: str = "quick", input_file: str | None = None,
             output_file: str | None = None, allow_local_write: bool = False) -> dict:
    if skill_id not in REGISTRY:
        raise ValueError("Unknown or unapproved skill identifier")
    _check_descriptor(skill_id)
    effect, relative_script, operation = REGISTRY[skill_id]
    script = _repository_path(relative_script)
    cmd = [sys.executable, str(script), operation]
    timeout = 180
    if skill_id == "shards-repository-health" or skill_id == "shards-release-gate":
        cmd.extend(["--repo", str(ROOT)])
    elif skill_id == "shards-skill-audit":
        if target_skill is None:
            raise ValueError("Audit requires --target-skill")
        cmd.extend(["--path", str(_selected_skill(target_skill))])
    elif skill_id == "shards-agent-handoff":
        if not allow_local_write:
            raise ValueError("Handoff requires --allow-local-write")
        cmd.extend(["--input", str(_state_file(input_file, must_exist=True)),
                    "--output", str(_state_file(output_file, must_exist=False))])
    elif skill_id == "shards-automation-operator":
        if profile not in ("quick", "weekly", "verify"):
            raise ValueError("Only named maintenance profiles can run")
        cmd.extend(["--workflow", profile])
        timeout = 420
    elif skill_id == "shards-skill-dispatch":
        timeout = 30
    plan = {"skill": skill_id, "effect": effect, "command": cmd,
            "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "commit": _source_revision(), "timeout_seconds": timeout,
            "approved_by": "host-required", "executed": False}
    plan["plan_sha256"] = _plan_fingerprint(plan)
    return plan

def run(plan: dict, *, executor=None) -> dict:
    _check_plan_integrity(plan)
    if executor is None:
        executor = subprocess.run
    env = {key: value for key, value in os.environ.items() if key in
           ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    started = timestamp()
    try:
        proc = executor(plan["command"], cwd=str(ROOT), env=env, capture_output=True,
                        text=True, timeout=plan["timeout_seconds"], check=False)
        stdout = SECRET.sub("[REDACTED]", proc.stdout)[-4000:]
        stderr = SECRET.sub("[REDACTED]", proc.stderr)[-2000:]
        status = "pass" if proc.returncode == 0 else "fail"
        if plan["skill"] == "shards-release-gate" and proc.returncode == 1:
            try:
                if json.loads(proc.stdout).get("decision") == "HOLD":
                    status = "hold"
            except json.JSONDecodeError:
                pass
        observed = {"status": status, "exit_code": proc.returncode,
                    "stdout_tail": stdout, "stderr_tail": stderr}
    except subprocess.TimeoutExpired:
        observed = {"status": "timeout", "exit_code": None,
                    "error": "Process exceeded timeout"}
    except OSError as exc:
        observed = {"status": "error", "exit_code": None, "error": type(exc).__name__}
    return {"receipt_id": str(uuid.uuid4()), "skill": plan["skill"],
            "effect": plan["effect"], "commit": plan["commit"],
            "plan_sha256": plan["plan_sha256"],
            "script_sha256": plan["script_sha256"], "command": plan["command"],
            "started_at": started, "finished_at": timestamp(), "executed": True,
            "observation": observed, "production_verified": False}

def persist(receipt: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / (receipt["receipt_id"] + ".json")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    for action in ("plan", "run"):
        s = sub.add_parser(action)
        s.add_argument("--skill", required=True, choices=sorted(REGISTRY))
        s.add_argument("--target-skill")
        s.add_argument("--profile", choices=("quick", "weekly", "verify"), default="quick")
        s.add_argument("--input-file")
        s.add_argument("--output-file")
        s.add_argument("--allow-local-write", action="store_true")
        if action == "run":
            s.add_argument("--execute", action="store_true", help="Explicitly authorize execution")
            s.add_argument("--expect-plan-sha256", metavar="SHA256",
                           help="Fail unless the reviewed plan matches this digest")
            s.add_argument("--save-receipt", action="store_true", help="Write JSON receipt under reports/dispatch")
    args = p.parse_args(argv)
    if args.action == "list":
        print(json.dumps({"skills": [{"name": key, "effect": value[0]}
                                     for key, value in sorted(REGISTRY.items())]}, indent=2))
        return 0
    try:
        plan = describe(args.skill, target_skill=args.target_skill, profile=args.profile,
                        input_file=args.input_file, output_file=args.output_file,
                        allow_local_write=args.allow_local_write)
        if args.action == "plan":
            print(json.dumps(plan, indent=2))
            return 0
        if not args.execute:
            raise ValueError("Run requires --execute; use plan first")
        if args.expect_plan_sha256 is not None:
            expected = args.expect_plan_sha256.lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected) or not hmac.compare_digest(
                    expected, plan["plan_sha256"]):
                raise ValueError("Reviewed plan SHA-256 does not match current execution plan")
        receipt = run(plan)
        if args.save_receipt:
            receipt["report_path"] = str(persist(receipt))
        print(json.dumps(receipt, indent=2))
        return 0 if receipt["observation"]["status"] == "pass" else 1
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
