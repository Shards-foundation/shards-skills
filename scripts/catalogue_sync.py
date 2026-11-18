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

def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    fields = {}
    for name, value in pairs:
        if name in fields:
            raise ValueError("Duplicate catalogue JSON field")
        fields[name] = value
    return fields


def _reject_constant(value: str) -> object:
    raise ValueError("Invalid catalogue JSON numeric constant")


def _load_catalogue(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # The standard decoder is recursive. Skip quoted strings when counting
    # containers so braces inside skill descriptions do not count as nesting.
    depth = 0
    i = 0
    while i < len(text):
        char = text[i]
        i += 1
        if char == '"':
            _, i = json.decoder.scanstring(text, i)
        elif char in "[{":
            depth += 1
            if depth > 32:
                raise ValueError("Catalogue nesting exceeds limit")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("Invalid JSON nesting")

    catalogue = json.loads(text, object_pairs_hook=_unique_fields, parse_constant=_reject_constant)
    if not isinstance(catalogue, dict):
        raise ValueError("Catalogue root must be an object")
    version = catalogue.get("schema_version")
    if type(version) is not int or version != 1:
        raise ValueError("Invalid catalogue schema_version")
    if any(not isinstance(catalogue.get(key), str) for key in ("name", "version", "status")):
        raise ValueError("Invalid catalogue name, version or status")
    count = catalogue.get("skill_count")
    if type(count) is not int or count < 0:
        raise ValueError("Invalid catalogue skill_count")

    for field in ("categories", "skill_paths"):
        values = catalogue.get(field)
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"Catalogue {field} must contain strings")
        if len(set(values)) != len(values):
            raise ValueError(f"Duplicate entry in catalogue {field}")

    entries = catalogue.get("skills")
    if not isinstance(entries, list):
        raise ValueError("Catalogue skills must be a list")
    paths = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Catalogue skill must be an object")
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            raise ValueError("Catalogue skill requires a string path")
        if path_value in paths:
            raise ValueError("Duplicate catalogue skill path")
        paths.add(path_value)
        # Missing descriptive metadata is repairable drift for a known path.
        for field in ("name", "description", "category", "status", "version"):
            if field in entry and not isinstance(entry[field], str):
                raise ValueError(f"Invalid catalogue skill {field}")
    return catalogue


def inspect_catalogue(root: Path = ROOT) -> tuple[dict, dict]:
    root = root.resolve()
    catalogue_path = root / "catalogue/catalogue.json"
    existing = _load_catalogue(catalogue_path)
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
    actual_by_path = {item["path"]: item for item in existing["skills"]}
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
