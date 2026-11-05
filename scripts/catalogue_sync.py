#!/usr/bin/env python3
"""Check and optionally reconcile Shards catalogue metadata without running skills."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from validate_skills import parse_frontmatter

ROOT = Path(__file__).resolve().parents[1]

def inspect_catalogue(root: Path = ROOT) -> tuple[dict, dict]:
    root = root.resolve()
    catalogue_path = root / "catalogue/catalogue.json"
    existing = json.loads(catalogue_path.read_text(encoding="utf-8"))
    entries = []
    errors = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if path.is_symlink() or path.parent.is_symlink():
            errors.append("Symlinked skill requires manual review: " + str(path.relative_to(root)))
            continue
        try:
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if meta.get("name") != path.parent.name:
                raise ValueError("Name does not match directory")
            entries.append({
                "name": meta["name"],
                "path": str(path.parent.relative_to(root)),
                "description": meta.get("description", ""),
                "category": meta.get("category", "uncategorised"),
                "status": meta.get("status", "draft"),
                "version": meta.get("version", "0.0.0"),
            })
        except (ValueError, KeyError, UnicodeError, OSError) as exc:
            errors.append(str(path.relative_to(root)) + ": " + str(exc))
    expected = dict(existing)
    expected.update({
        "skill_count": len(entries),
        "skill_paths": [item["path"] for item in entries],
        "categories": sorted({item["category"] for item in entries}),
        "skills": entries,
    })
    actual_by_path = {item["path"]: item for item in existing.get("skills", []) if isinstance(item, dict) and "path" in item}
    expected_by_path = {item["path"]: item for item in entries}
    missing = sorted(set(expected_by_path) - set(actual_by_path))
    extra = sorted(set(actual_by_path) - set(expected_by_path))
    drift = sorted(path for path in expected_by_path.keys() & actual_by_path.keys()
                   if expected_by_path[path] != actual_by_path[path])
    if existing.get("skill_count") != len(entries):
        errors.append("Catalogue count disagrees with skill directories")
    if sorted(existing.get("skill_paths", [])) != sorted(expected["skill_paths"]):
        errors.append("Catalogue skill_paths differ from discovered SKILL.md files")
    if missing or extra:
        errors.append("Catalogue entries missing or stale")
    # Legacy imported metadata may be stale; report but do not misclassify an existing checked-out skill.
    report = {
        "workflow": "catalogue-sync", "observed_skills": len(entries),
        "declared_skills": existing.get("skill_count"),
        "status": "FAIL" if errors else ("DRIFT" if drift or existing != expected else "PASS"),
        "errors": errors, "missing": missing, "extra": extra,
        "metadata_drift": drift, "would_change": existing != expected,
        "note": "DRIFT is informational in check mode; explicit --write --approve-write repairs only the catalogue JSON.",
    }
    return expected, report

def repair(root: Path = ROOT) -> dict:
    expected, report = inspect_catalogue(root)
    if report["errors"]:
        raise ValueError("Repair refused: invalid or inconsistent skill paths; fix errors first")
    path = root.resolve() / "catalogue/catalogue.json"
    if report["would_change"]:
        data = json.dumps(expected, indent=2, ensure_ascii=False) + "\n"
        fd, temp = tempfile.mkstemp(prefix=".catalogue-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    report["repaired"] = report["would_change"]
    return report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    parser.add_argument("--approve-write", action="store_true",
                        help="Required in addition to --write before changing tracked files.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.write and not args.approve_write:
        parser.error("--write requires --approve-write")
    if args.approve_write and not args.write:
        parser.error("--approve-write requires --write")
    try:
        report = repair(args.root) if args.write else inspect_catalogue(args.root)[1]
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        print(json.dumps({"workflow": "catalogue-sync", "status": "ERROR", "error": str(error)}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(bool(report["errors"]))

if __name__ == "__main__":
    raise SystemExit(main())
