#!/usr/bin/env python3
"""Inventory and triage agent skills without executing imported code."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from validate_skills import RISK_PATTERNS, parse_frontmatter

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SUFFIXES = {".py", ".sh", ".js", ".ts", ".ps1", ".exe"}

def assess(root: Path = ROOT) -> dict:
    root = root.resolve()
    entries, issues = [], []
    statuses, categories = Counter(), Counter()
    imported_count = script_count = 0
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        directory = path.parent
        name = directory.name
        if path.is_symlink() or directory.is_symlink():
            issues.append({"skill": name, "level": "error", "code": "symlink-skill"})
            continue
        try:
            content = path.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(content)
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append({"skill": name, "level": "error",
                           "code": "invalid-frontmatter", "detail": str(exc)[:240]})
            continue
        if meta.get("name") != name:
            issues.append({"skill": name, "level": "error", "code": "name-mismatch"})
        status = meta.get("status", "draft")
        statuses[status] += 1
        categories[meta.get("category", "uncategorised")] += 1
        imported = (directory / "UPSTREAM.md").exists()
        imported_count += int(imported)
        scripts = []
        for child in directory.rglob("*"):
            if child.is_symlink():
                issues.append({"skill": name, "level": "review", "code": "symlink-file",
                               "path": str(child.relative_to(directory))})
            elif child.is_file() and child.suffix.lower() in SCRIPT_SUFFIXES:
                scripts.append(str(child.relative_to(directory)))
        script_count += len(scripts)
        flags = [code for code, pattern in RISK_PATTERNS if pattern.search(content)]
        if imported and status != "verified":
            issues.append({"skill": name, "level": "review", "code": "imported-unverified"})
        if scripts:
            issues.append({"skill": name, "level": "review",
                           "code": "executable-scripts-present", "count": len(scripts)})
        for flag in flags:
            issues.append({"skill": name, "level": "review", "code": "heuristic-" + flag})
        entries.append({"name": name, "status": status, "category": meta.get("category", "uncategorised"),
                        "imported": imported, "script_paths": scripts, "review_flags": flags,
                        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
    errors = sum(item["level"] == "error" for item in issues)
    return {"workflow": "skill-portfolio-audit",
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "scope": "read-only-inventory-and-heuristic-review; no imported code executed",
            "status": "FAIL" if errors else "OBSERVED",
            "summary": {"skills": len(entries), "imported": imported_count,
                        "first_party_or_untracked": len(entries) - imported_count,
                        "script_files": script_count, "errors": errors,
                        "review_findings": sum(item["level"] == "review" for item in issues),
                        "statuses": dict(sorted(statuses.items())),
                        "categories": dict(sorted(categories.items()))},
            "issues": issues, "skills": entries}

def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = ["# Shards skill portfolio review", "",
             "Generated: " + report["observed_at"], "",
             "Read-only inventory, not an execution or security certification.", "",
             "| Measure | Observed |", "|---|---:|"]
    for key in ("skills", "imported", "first_party_or_untracked", "script_files",
                "errors", "review_findings"):
        lines.append("| " + key.replace("_", " ").title() + " | " + str(summary[key]) + " |")
    lines.extend(["", "## Review queue (first 35 findings)", ""])
    for item in report["issues"][:35]:
        lines.append("- **" + item["level"].upper() + "** " + item["skill"] + ": " + item["code"])
    if len(report["issues"]) > 35:
        lines.extend(["", "Additional items: " + str(len(report["issues"]) - 35) + ". See JSON report."])
    lines.extend(["", "Imported skills and executable scripts require provenance, "
                  "permission and sandbox review before use.", ""])
    return "\n".join(lines)

def write_new(path: Path, content: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = assess(args.root)
        if args.json_output:
            write_new(args.json_output, json.dumps(result, sort_keys=True, indent=2) + "\n")
        if args.markdown_output:
            write_new(args.markdown_output, markdown(result))
        print(json.dumps({"status": result["status"], "summary": result["summary"],
                          "sample_findings": result["issues"][:12]}, indent=2, sort_keys=True))
        return int(result["status"] == "FAIL")
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
