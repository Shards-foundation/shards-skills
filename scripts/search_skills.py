#!/usr/bin/env python3
"""Deterministic, read-only skill discovery; catalogue results are never executable."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dispatch_skills import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
TOKENS = re.compile(r"[a-z0-9]+")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_STATUSES = {"draft", "review", "verified", "deprecated"}


def words(value: str) -> set[str]:
    return set(TOKENS.findall(value.lower()))


# Common task prose is not useful evidence of skill relevance.
# Use conservative, deterministic inflection reduction; never execute skill code.
STOPWORDS = set(
    "a an the in on at to for of is are was were with into when by from and or "
    "but without not no do does dont should have has had this that those these "
    "who which your my me us our it its all any as before after just only please "
    "there what how would could can".split()
)


def normalized_words(value: str) -> set[str]:
    result = set()
    for token in words(value):
        if token in STOPWORDS or len(token) <= 2:
            continue
        if token.endswith("ies") and len(token) > 4:
            result.add(token[:-3] + "y")
        elif token.endswith("ing") and len(token) > 6:
            stem = token[:-3]
            result.update((stem, stem + "e"))
        elif token.endswith("ed") and len(token) > 5:
            stem = token[:-2]
            result.update((stem, stem + "e"))
        elif token.endswith("es") and len(token) > 4:
            result.update((token[:-1], token[:-2]))
        elif token.endswith("s") and len(token) > 3:
            result.add(token[:-1])
        else:
            result.add(token)
    return result


def catalogue_entries(root: Path = ROOT) -> list[dict]:
    """Read metadata only. Never import, execute, or parse imported skill code."""
    source = Path(root) / "catalogue" / "catalogue.json"
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 5_000_000:
        raise ValueError("Catalogue missing, symlinked or too large")
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported catalogue schema")
    records = data.get("skills")
    if (not isinstance(records, list) or
            type(data.get("skill_count")) is not int or
            data["skill_count"] != len(records)):
        raise ValueError("Catalogue count and records disagree")
    results: list[dict] = []
    seen: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Invalid skill entry")
        name, path = item.get("name"), item.get("path")
        description = item.get("description")
        category, status = item.get("category"), item.get("status")
        if (not isinstance(name, str) or not NAME.fullmatch(name) or name in seen or
                path != "skills/" + name or
                not isinstance(description, str) or not description.strip() or
                not isinstance(category, str) or not category.strip() or
                not isinstance(status, str) or status not in VALID_STATUSES):
            raise ValueError("Malformed, duplicate or unsafe catalogue entry")
        seen.add(name)
        results.append({"name": name, "path": path, "description": description,
                        "category": category, "status": status,
                        "source": "catalogue", "execution": "not-dispatchable"})
    return results


def curated_entries(root: Path = ROOT) -> list[dict]:
    """Expose only explicitly registered first-party skill metadata."""
    results: list[dict] = []
    for name in sorted(REGISTRY):
        descriptor = Path(root) / "plugins" / "shards-core" / "skills" / name / "SKILL.md"
        if descriptor.is_symlink() or not descriptor.is_file():
            raise ValueError("Curated descriptor missing or symlinked: " + name)
        # Only the bounded YAML frontmatter is authoritative. Body text must
        # never masquerade as metadata or override the trust-labelled listing.
        content = descriptor.read_text(encoding="utf-8")
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("Curated descriptor missing frontmatter: " + name)
        try:
            closing = lines.index("---", 1)
        except ValueError as exc:
            raise ValueError("Curated descriptor unclosed frontmatter: " + name) from exc
        if closing > 100 or sum(len(line) + 1 for line in lines[:closing + 1]) > 8192:
            raise ValueError("Curated descriptor frontmatter too large: " + name)
        metadata = lines[1:closing]
        names = [line.split(":", 1)[1].strip().strip("\\\"'")
                 for line in metadata if line.startswith("name:")]
        descriptions = [line.split(":", 1)[1].strip().strip("\\\"'")
                        for line in metadata if line.startswith("description:")]
        if names != [name]:
            raise ValueError("Curated descriptor metadata mismatch: " + name)
        if len(descriptions) != 1 or not descriptions[0]:
            raise ValueError("Curated descriptor lacks a unique description: " + name)
        results.append({"name": name,
                        "path": "plugins/shards-core/skills/" + name,
                        "description": descriptions[0], "category": "curated",
                        "status": "curated", "source": "curated",
                        "execution": "dispatcher-plan-required"})
    return results


def rank(entries: list[dict], query: str, *, category: str | None = None,
         status: str | None = None) -> list[dict]:
    if not words(query):
        raise ValueError("Query must contain at least one letter or number")
    query_tokens = normalized_words(query)
    raw_fallback = not query_tokens
    if raw_fallback:
        query_tokens = words(query)
    term_words = words if raw_fallback else normalized_words
    ranked = []
    for item in entries:
        if category and item["category"] != category:
            continue
        if status and item["status"] != status:
            continue
        name = item["name"].replace("-", " ").lower()
        desc = item["description"].lower()
        hits_name = len(query_tokens & term_words(name))
        hits_desc = len(query_tokens & term_words(desc))
        hits_cat = len(query_tokens & term_words(item["category"]))
        # Short skill names are high-signal; generic prose overlap is not.
        score = 10 * hits_name + 4 * hits_desc + 2 * hits_cat
        if score == 0:
            continue
        ranked.append({**item, "score": score})
    ranked.sort(key=lambda item: (-item["score"],
                                  item["execution"] != "dispatcher-plan-required",
                                  item["name"]))
    return ranked


def discover(query: str, *, root: Path = ROOT, category: str | None = None,
             status: str | None = None, limit: int = 10) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    entries = catalogue_entries(root) + curated_entries(root)
    matches = rank(entries, query, category=category, status=status)
    return {"query": query, "candidate_count": len(entries),
            "match_count": len(matches), "results": matches[:limit],
            "trust_boundary": ("Discovery is metadata-only. Catalogue results are not "
                               "dispatchable. Curated results require a reviewed dispatcher "
                               "plan, explicit execution flag and host authorization.")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Task terms to match against metadata")
    parser.add_argument("--category", help="Exact category filter")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES | {"curated"}))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(discover(args.query, category=args.category,
                                  status=args.status, limit=args.limit),
                         indent=2, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
