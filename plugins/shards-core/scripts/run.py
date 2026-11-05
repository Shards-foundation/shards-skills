#!/usr/bin/env python3
"""Shards Agent Core: dependency-free, bounded local workflows."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)
SENSITIVE_KEY = re.compile(r"password|api[_-]?key|access[_-]?token|private[_-]?key|secret", re.I)

def read(path: Path) -> str:
    if not path.is_file() or path.stat().st_size > 2000000:
        raise ValueError("Missing or oversized file: " + str(path))
    return path.read_text(encoding="utf-8")

def metadata(content: str) -> dict:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, re.S)
    if not match:
        raise ValueError("Missing skill frontmatter")
    meta = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            raise ValueError("Unsupported YAML metadata line")
        k, v = line.split(":", 1)
        k = k.strip()
        if not k or k in meta:
            raise ValueError("Duplicate or missing metadata key")
        meta[k] = v.strip().strip("\"'")
    return meta

def catalogue() -> dict:
    entries = []
    for p in sorted(SKILLS.glob("*/SKILL.md")):
        m = metadata(read(p))
        entries.append({"name": m.get("name"), "description": m.get("description"), "path": str(p.relative_to(ROOT))})
    return {"workflow": "catalogue", "count": len(entries), "scope": "curated-only", "skills": entries}

def audit_skill(path: Path) -> dict:
    d = path.expanduser().resolve()
    issues, scripts, meta = [], [], {}
    if not d.is_dir():
        return {"workflow": "audit-skill", "status": "BLOCK", "issues": ["Directory missing"], "executable": False}
    try:
        body = read(d / "SKILL.md")
        meta = metadata(body)
    except (ValueError, OSError, UnicodeError) as error:
        issues.append("Invalid SKILL.md: " + str(error))
        body = ""
    if not NAME.fullmatch(meta.get("name", "")) or meta.get("name") != d.name:
        issues.append("Invalid skill name")
    if not 20 <= len(meta.get("description", "")) <= 1024:
        issues.append("Invalid description length")
    for item in re.finditer(r"\[[^\]]*]\(([^)]+)\)", body):
        rel = item.group(1).split("#", 1)[0]
        if not rel or rel.startswith(("https://", "http://", "mailto:")):
            continue
        f = (d / rel).resolve()
        if not f.is_relative_to(d) or not f.is_file():
            issues.append("Unsafe link: " + rel)
    for p in d.rglob("*"):
        if p.is_symlink():
            issues.append("Symlink needs review: " + str(p.relative_to(d)))
        elif p.is_file() and p.suffix in (".py", ".sh", ".js", ".ts", ".ps1", ".exe"):
            scripts.append(str(p.relative_to(d)))
    if (d / "UPSTREAM.md").exists() or meta.get("status") == "review":
        issues.append("Imported/review-stage skill needs independent review")
    if scripts:
        issues.append("Executable scripts need independent review")
    blocked = any(x.startswith(("Invalid", "Unsafe")) for x in issues)
    return {"workflow": "audit-skill", "path": str(d),
            "status": "BLOCK" if blocked else ("REVIEW" if issues else "METADATA_PASS"),
            "issues": issues, "scripts": scripts, "metadata": meta,
            "executable": False, "scope": "static-structural-only"}

def git(repo: Path, *args: str) -> dict:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=12)
        return {"ok": r.returncode == 0, "output": r.stdout[:12000].strip(), "error": r.stderr[:1000].strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ok": False, "output": "", "error": str(error)}

def repository_health(path: Path) -> dict:
    repo = path.expanduser().resolve()
    if not repo.is_dir():
        raise ValueError("Repository path missing")
    top, head, changes = git(repo, "rev-parse", "--show-toplevel"), git(repo, "rev-parse", "HEAD"), git(repo, "status", "--porcelain")
    good = all(x["ok"] for x in (top, head, changes)) and Path(top["output"]).resolve() == repo
    return {"workflow": "repository-health", "repo": str(repo), "status": "OBSERVED" if good else "INCOMPLETE",
            "scope": "metadata-only", "commit": head["output"] if head["ok"] else None,
            "dirty": bool(changes["output"]) if changes["ok"] else None,
            "changed_paths": changes["output"].splitlines()[:100] if changes["ok"] else [],
            "metadata": {name: (repo / name).exists() for name in ("README.md", "LICENSE", "pyproject.toml", "tests", ".github/workflows")},
            "errors": [x["error"] for x in (top, head, changes) if not x["ok"]]}

def release_check(repo: Path, run_tests: bool, trusted_local_code: bool) -> dict:
    if run_tests and not trusted_local_code:
        raise ValueError("--run-tests also requires --trusted-local-code and user authorization")
    state = repository_health(repo)
    reasons = []
    if state["status"] != "OBSERVED":
        reasons.append("Repository identity unverified")
    if state["dirty"]:
        reasons.append("Working tree dirty")
    for key in ("README.md", "LICENSE", "pyproject.toml", "tests"):
        if not state["metadata"][key]:
            reasons.append("Missing " + key)
    tests = {"executed": False, "exit_code": None}
    if run_tests:
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        try:
            p = subprocess.run(cmd, cwd=state["repo"], capture_output=True, text=True, timeout=120)
            tests = {"executed": True, "command": cmd, "exit_code": p.returncode, "output_tail": (p.stdout + p.stderr)[-5000:]}
            if p.returncode:
                reasons.append("Unit tests failed")
        except (OSError, subprocess.TimeoutExpired) as error:
            tests = {"executed": True, "exit_code": None, "error": str(error)}
            reasons.append("Unit tests incomplete")
    else:
        reasons.append("Unit tests not executed")
    return {"workflow": "release-check", "decision": "HOLD" if reasons else "READY",
            "scope": "local-unit-tests-only", "release_authorized": False, "production_verified": False,
            "reasons": reasons, "tests": tests, "repository": state}

def contains_secret(value, key: str = "") -> bool:
    if SENSITIVE_KEY.search(key):
        return True
    if isinstance(value, str):
        return bool(SECRET.search(value))
    if isinstance(value, list):
        return any(contains_secret(x) for x in value)
    if isinstance(value, dict):
        return any(contains_secret(x, str(k)) for k, x in value.items())
    return False

def validate_handoff(path: Path) -> dict:
    data = json.loads(read(path))
    if not isinstance(data, dict):
        raise ValueError("Checkpoint must be a JSON object")
    strings = ("goal", "repo", "branch", "commit")
    arrays = ("completed", "decisions", "evidence", "blockers", "pending")
    for key in strings:
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError("Missing string: " + key)
    for key in arrays:
        if not isinstance(data.get(key), list) or any(not isinstance(x, str) for x in data[key]):
            raise ValueError("Missing string array: " + key)
    if contains_secret(data):
        raise ValueError("Potential sensitive information in checkpoint")
    return {k: data[k] for k in (*strings, *arrays)}

def write_exclusive(path: Path, data: str):
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(data)

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="command", required=True)
    subs.add_parser("catalogue")
    for name in ("repository-health", "release-check"):
        item = subs.add_parser(name)
        item.add_argument("--repo", type=Path, required=True)
        item.add_argument("--output", type=Path)
        if name == "release-check":
            item.add_argument("--run-tests", action="store_true")
            item.add_argument("--trusted-local-code", action="store_true")
    audit = subs.add_parser("audit-skill")
    audit.add_argument("--path", type=Path, required=True)
    audit.add_argument("--output", type=Path)
    checkpoint = subs.add_parser("handoff")
    checkpoint.add_argument("--input", type=Path, required=True)
    checkpoint.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "catalogue":
            report = catalogue()
        elif args.command == "repository-health":
            report = repository_health(args.repo)
        elif args.command == "audit-skill":
            report = audit_skill(args.path)
        elif args.command == "release-check":
            report = release_check(args.repo, args.run_tests, args.trusted_local_code)
        else:
            report = {"workflow": "handoff", "checkpoint": validate_handoff(args.input), "status": "VALIDATED"}
        result = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if getattr(args, "output", None):
            write_exclusive(args.output, result)
        print(result, end="")
        return int((args.command == "release-check" and report["decision"] == "HOLD") or
                   (args.command == "audit-skill" and report["status"] == "BLOCK") or
                   (args.command == "repository-health" and report["status"] == "INCOMPLETE"))
    except (ValueError, OSError, UnicodeError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
