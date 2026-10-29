#!/usr/bin/env python3
"""Rebuild the machine-readable catalogue from SKILL.md files."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def build_catalogue(root=ROOT):
    root = Path(root)
    entries = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise ValueError(f"Invalid frontmatter: {path}")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Missing frontmatter close: {path}")
        meta = {}
        for line in parts[1].strip().splitlines():
            if ":" not in line or line[:1].isspace():
                raise ValueError(f"Unsupported metadata line in {path}: {line}")
            key, value = line.split(":", 1)
            key = key.strip()
            if key in meta:
                raise ValueError(f"Duplicate metadata key in {path}: {key}")
            meta[key] = value.strip().strip("\"'")
        if meta.get("name") != path.parent.name:
            raise ValueError(f"Name/directory mismatch: {path}")
        if not meta.get("name") or not meta.get("description"):
            raise ValueError(f"Missing required metadata: {path}")
        entries.append({"name": meta["name"], "path": str(path.parent.relative_to(root)),
            "description": meta.get("description", ""), "category": meta.get("category", "uncategorised"),
            "status": meta.get("status", "draft"), "version": meta.get("version", "0.0.0")})
    cat = {"schema_version": 1, "name": "Shards Skills", "version": "0.1.0", "status": "bootstrap",
        "skill_count": len(entries), "categories": sorted({e["category"] for e in entries}),
        "skill_paths": [e["path"] for e in entries], "skills": entries}
    (root / "catalogue" / "catalogue.json").write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    return cat

def main():
    cat = build_catalogue()
    print(f"Catalogue rebuilt: {cat['skill_count']} skills across {len(cat['categories'])} categories")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
