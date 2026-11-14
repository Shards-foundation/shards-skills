#!/usr/bin/env python3
"""Build an offline, source-checked Manus skill bundle. No network or model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "shards-sec-ai-agent-boundaries"
SOURCES = (
    "scripts/security_assurance.py",
    "scripts/security_skill_eval.py",
    "scripts/vibecode_guard.py",
    "catalogue/shards-security-controls.json",
    "docs/security-assurance.md",
    "docs/security-frameworks.md",
    "evals/shards-security-workflows.json",
)


def reject_symlink_path(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f"Refusing symlinked path component: {component}")


def checked_file(path: Path) -> bytes:
    reject_symlink_path(path)
    if not path.is_file():
        raise ValueError(f"Missing, unsafe or symlinked file: {path}")
    return path.read_bytes()


def verify(root: Path) -> dict[str, str]:
    skill = root / "skills" / NAME
    header = checked_file(skill / "SKILL.md")
    if not header.startswith(b"---\nname: shards-sec-ai-agent-boundaries\n"):
        raise ValueError("Unexpected SKILL.md header")
    if b"../../evals/" in header:
        raise ValueError("SKILL.md still references a resource outside its bundle")
    if b"python scripts/security_assurance.py" not in header:
        raise ValueError("SKILL.md omits the local plan entry point")
    output = {"SKILL.md": hashlib.sha256(header).hexdigest()}
    for relative in SOURCES:
        canonical = checked_file(root / relative)
        copy = checked_file(skill / relative)
        if canonical != copy:
            raise ValueError(f"Stale portable copy: {relative}; run --sync")
        output[relative] = hashlib.sha256(copy).hexdigest()
    return output


def sync(root: Path) -> None:
    target = root / "skills" / NAME
    checked_file(target / "SKILL.md")
    for relative in SOURCES:
        data = checked_file(root / relative)
        destination = target / relative
        reject_symlink_path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)


def build_zip(root: Path, target: Path) -> dict[str, str]:
    hashes = verify(root)
    reject_symlink_path(target)
    if not target.parent.is_dir():
        raise ValueError("ZIP output directory does not exist")
    files = ("SKILL.md",) + SOURCES
    manifest = json.dumps({"schema_version": 1, "name": NAME, "file_sha256": hashes,
                           "host_traces_verified": False}, indent=2, sort_keys=True).encode() + b"\n"
    with zipfile.ZipFile(target, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in (*files, "MANIFEST.json"):
            entry = zipfile.ZipInfo(NAME + "/" + relative, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100644 << 16)
            data = manifest if relative == "MANIFEST.json" else checked_file(root / "skills" / NAME / relative)
            archive.writestr(entry, data)
    return hashes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true", help="Fail on missing or stale bundled sources")
    modes.add_argument("--sync", action="store_true", help="Copy tracked canonical sources into the skill folder")
    modes.add_argument("--zip", type=Path, help="Produce a deterministic, source-checked ZIP")
    args = parser.parse_args(argv)
    try:
        if args.sync:
            sync(ROOT)
        hashes = verify(ROOT)
        if args.zip:
            build_zip(ROOT, args.zip)
        print(json.dumps({"status": "PASS", "skill": NAME, "files": len(hashes),
                          "output": str(args.zip) if args.zip else None}, sort_keys=True))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
