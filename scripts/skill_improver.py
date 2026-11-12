#!/usr/bin/env python3
"""Offline, evidence-gated SKILL.md revision tool. No dynamic skill execution."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX = re.compile(r"^[a-f0-9]{64}$")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

def load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object")
    return obj

def target_path(raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) != 3 or rel.parts[0] != "skills" or rel.parts[2] != "SKILL.md" or not NAME.fullmatch(rel.parts[1]):
        raise ValueError("Target must be skills/<first-party-name>/SKILL.md")
    base = ROOT / "skills"
    if ROOT.is_symlink() or base.is_symlink() or base.resolve().parent != ROOT.resolve():
        raise ValueError("Symlinked or escaped skill root")
    folder = base / rel.parts[1]
    path = folder / "SKILL.md"
    if folder.is_symlink() or path.is_symlink() or (folder / "UPSTREAM.md").exists() or not path.is_file():
        raise ValueError("Target is missing, symlinked or imported")
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("Target escapes skills directory")
    return path

def descriptor(blob: bytes, name: str) -> str:
    text = blob.decode("utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("Invalid SKILL.md frontmatter")
    header = text.split("\n---\n", 1)[0].splitlines()[1:]
    matches = [line.split(":", 1)[1].strip().strip('"\'') for line in header if line.startswith("name:")]
    if matches != [name]:
        raise ValueError("Candidate name must match target")
    if len(text) > 200_000 or len(text) < 120:
        raise ValueError("Descriptor size outside limits")
    metadata = {}
    for line in header:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            raise ValueError("Unsupported frontmatter")
        key, value = line.split(":", 1)
        if key in metadata or not key.strip() or value.lstrip().startswith(("[", "{", "|", ">")):
            raise ValueError("Invalid frontmatter key or value")
        metadata[key] = value.strip().strip(chr(34) + chr(39))
    description = metadata.get("description", "")
    if not 20 <= len(description) <= 1024:
        raise ValueError("Invalid description")
    if metadata.get("status", "draft") not in {"draft", "review", "verified", "deprecated"}:
        raise ValueError("Invalid status")
    body = text.split("\n---\n", 1)[1]
    if len(body.strip()) < 100:
        raise ValueError("Descriptor body too short")
    skill_dir = ROOT / "skills" / name
    for link in re.findall(r"\\[[^\\]]*\\]\\(([^)]+)\\)", body):
        if link.startswith(("https://", "http://", "mailto:", "#")):
            continue
        path = (skill_dir / link.split("#", 1)[0]).resolve()
        if not path.is_relative_to(skill_dir.resolve()) or not path.exists():
            raise ValueError("Broken or unsafe relative link")
    return text

def safe_file(raw: str) -> Path:
    path = Path(raw)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Input must be a regular non-symlink file")
    return path

def create_only(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ValueError("Output must not be symlinked")
    with path.open("xb") as stream:
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            path.unlink(missing_ok=True)
            raise

def plan(args) -> dict:
    target = target_path(args.target)
    old, new = target.read_bytes(), safe_file(args.candidate).read_bytes()
    descriptor(old, target.parent.name)
    descriptor(new, target.parent.name)
    if old == new:
        raise ValueError("Candidate has no changes")
    diff = "".join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True),
        fromfile=args.target + " (baseline)", tofile=args.target + " (candidate)"))
    payload = {"schema": 1, "target": args.target, "baseline_sha256": digest(old),
               "candidate_sha256": digest(new), "diff": diff}
    payload["plan_sha256"] = digest(canonical(payload))
    create_only(Path(args.output), json.dumps(payload, indent=2).encode() + b"\n")
    return payload

def check_plan(raw: str) -> tuple[dict, Path]:
    record = load(safe_file(raw))
    allowed = {"schema", "target", "baseline_sha256", "candidate_sha256", "diff", "plan_sha256"}
    if set(record) != allowed or record["schema"] != 1:
        raise ValueError("Invalid plan shape")
    sig = record.pop("plan_sha256")
    if not isinstance(sig, str) or not HEX.fullmatch(sig) or digest(canonical(record)) != sig:
        raise ValueError("Plan checksum mismatch")
    record["plan_sha256"] = sig
    return record, target_path(record["target"])

def check_eval(raw: str, record: dict) -> None:
    ev = load(safe_file(raw))
    fields = {"baseline_sha256", "candidate_sha256", "case_set_sha256",
              "baseline_passed", "candidate_passed", "regressions", "failed_cases"}
    if set(ev) != fields or ev["baseline_sha256"] != record["baseline_sha256"] or ev["candidate_sha256"] != record["candidate_sha256"]:
        raise ValueError("Eval does not match plan")
    if not isinstance(ev["case_set_sha256"], str) or not HEX.fullmatch(ev["case_set_sha256"]):
        raise ValueError("Invalid fixed evaluation set")
    values = [ev[k] for k in ("baseline_passed", "candidate_passed", "regressions", "failed_cases")]
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError("Invalid evaluation counts")
    if ev["candidate_passed"] < 1 or ev["candidate_passed"] < ev["baseline_passed"] or ev["regressions"] or ev["failed_cases"]:
        raise ValueError("Candidate fails regression gate")

def apply(args) -> dict:
    if not args.approve:
        raise ValueError("Apply requires --approve")
    record, target = check_plan(args.plan)
    if args.expect_plan_sha256 != record["plan_sha256"]:
        raise ValueError("Reviewed plan checksum not approved")
    old, new = target.read_bytes(), safe_file(args.candidate).read_bytes()
    if digest(old) != record["baseline_sha256"] or digest(new) != record["candidate_sha256"]:
        raise ValueError("Stale target or candidate")
    descriptor(new, target.parent.name)
    check_eval(args.eval, record)
    expected = "".join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True),
        fromfile=record["target"] + " (baseline)", tofile=record["target"] + " (candidate)"))
    if expected != record["diff"]:
        raise ValueError("Diff mismatch")
    backup = target.with_name("SKILL.md.backup-" + digest(old)[:16] + "-" + uuid.uuid4().hex)
    create_only(backup, old)
    temp = None
    replaced = False
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".skill-improver-", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(new)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(target.read_bytes()) != digest(old):
            raise ValueError("Target changed during apply")
        os.replace(temp, target)
        replaced = True
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        if not replaced:
            backup.unlink(missing_ok=True)
    return {"status": "applied", "target": record["target"], "before_sha256": digest(old),
            "after_sha256": digest(new), "backup": str(backup.relative_to(ROOT)),
            "plan_sha256": record["plan_sha256"]}

def rollback(args) -> dict:
    if not args.approve or not HEX.fullmatch(args.expect_current_sha256 or ""):
        raise ValueError("Rollback requires approval and exact current digest")
    target = target_path(args.target)
    backup = safe_file(args.backup)
    if backup.parent.resolve() != target.parent.resolve():
        raise ValueError("Backup must belong to target")
    match = re.fullmatch(r"SKILL\.md\.backup-([0-9a-f]{16})-([0-9a-f]{32})", backup.name)
    if match is None:
        raise ValueError("Invalid backup filename")
    old, current = backup.read_bytes(), target.read_bytes()
    if not digest(old).startswith(match.group(1)):
        raise ValueError("Backup digest mismatch")
    descriptor(old, target.parent.name)
    if digest(current) != args.expect_current_sha256:
        raise ValueError("Target changed; rollback blocked")
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=".skill-rollback-", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(old)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(target.read_bytes()) != digest(current):
            raise ValueError("Target changed during rollback")
        os.replace(temp, target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return {"status": "rolled_back", "target": args.target, "sha256": digest(old)}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--target", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("apply")
    p.add_argument("--plan", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--eval", required=True)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--expect-plan-sha256", required=True)
    p = sub.add_parser("rollback")
    p.add_argument("--target", required=True)
    p.add_argument("--backup", required=True)
    p.add_argument("--expect-current-sha256", required=True)
    p.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = {"plan": plan, "apply": apply, "rollback": rollback}[args.operation](args)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
