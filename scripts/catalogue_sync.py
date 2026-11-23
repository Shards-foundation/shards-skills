#!/usr/bin/env python3
"""Check and optionally reconcile Shards catalogue metadata without running skills."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from validate_skills import catalogue_entry, catalogue_file, enrich_catalogue

ROOT = Path(__file__).resolve().parents[1]

def inspect_catalogue(root: Path = ROOT) -> tuple[dict, dict]:
    root = root.resolve()
    existing = json.loads(catalogue_file(root).read_text(encoding="utf-8"))
    if (not isinstance(existing, dict) or type(existing.get("schema_version")) is not int
            or existing["schema_version"] != 1):
        raise ValueError("Unsupported catalogue schema, expected a JSON object with schema_version 1")
    records = existing.get("skills")
    paths = existing.get("skill_paths")
    if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
        raise ValueError("Catalogue skill_paths must be a list of strings")
    if type(existing.get("skill_count")) is not int:
        raise ValueError("Catalogue skill_count must be an integer")
    if not isinstance(records, list):
        raise ValueError("Catalogue skills must be a list")
    actual_by_path = {}
    for index, item in enumerate(records):
        path = item.get("path") if isinstance(item, dict) else None
        if not isinstance(path, str) or not path:
            raise ValueError(f"Catalogue skills entry {index} is missing a string path")
        if path in actual_by_path:
            raise ValueError(f"Duplicate catalogue skill path: {path}")
        actual_by_path[path] = item

    entries = []
    errors = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        try:
            entries.append(catalogue_entry(path, root))
        except (ValueError, KeyError, UnicodeError, OSError) as exc:
            errors.append(str(path.relative_to(root)) + ": " + str(exc))
    if not errors:
        entries = enrich_catalogue(entries, root)
    expected = dict(existing)
    expected.update({
        "skill_count": len(entries),
        "skill_paths": [item["path"] for item in entries],
        "categories": sorted({item["category"] for item in entries}),
        "skills": entries,
    })
    expected_by_path = {item["path"]: item for item in entries}
    missing = sorted(set(expected_by_path) - set(actual_by_path))
    extra = sorted(set(actual_by_path) - set(expected_by_path))
    drift = sorted(path for path in expected_by_path.keys() & actual_by_path.keys()
                   if expected_by_path[path] != actual_by_path[path])
    if existing.get("skill_count") != len(entries):
        errors.append("Catalogue count disagrees with skill directories")
    if sorted(paths) != sorted(expected["skill_paths"]):
        errors.append("Catalogue skill_paths differ from discovered SKILL.md files")
    if missing or extra:
        errors.append("Catalogue entries missing or stale")
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
    path = catalogue_file(root.resolve())
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
