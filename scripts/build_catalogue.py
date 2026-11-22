#!/usr/bin/env python3
"""Rebuild the machine-readable catalogue from SKILL.md files."""
import json
from pathlib import Path

if __package__:
    from .validate_skills import catalogue_entry, catalogue_file, enrich_catalogue
else:
    from validate_skills import catalogue_entry, catalogue_file, enrich_catalogue

ROOT = Path(__file__).resolve().parents[1]

def build_catalogue(root=ROOT):
    root = Path(root)
    entries = enrich_catalogue([catalogue_entry(path, root)
                                for path in sorted((root / "skills").glob("*/SKILL.md"))], root)
    cat = {"schema_version": 1, "name": "Shards Skills", "version": "0.1.0", "status": "active",
        "skill_count": len(entries), "categories": sorted({e["category"] for e in entries}),
        "skill_paths": [e["path"] for e in entries], "skills": entries}
    catalogue_file(root).write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    return cat

def main():
    cat = build_catalogue()
    print(f"Catalogue rebuilt: {cat['skill_count']} skills across {len(cat['categories'])} categories")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
