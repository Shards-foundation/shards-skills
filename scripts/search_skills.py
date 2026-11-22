#!/usr/bin/env python3
"""Deterministic, read-only skill discovery; catalogue results are never executable."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path

from dispatch_skills import REGISTRY
from validate_skills import catalogue_entry, discovery_phrases

ROOT = Path(__file__).resolve().parents[1]
TOKENS = re.compile(r"[a-z0-9]+")
# Explicitly prohibited actions are constraints, not positive evidence of a
# skill the agent should select. Strip bounded negative clauses only from
# relevance scoring; retain the original task in the output. This is a
# conservative lexical heuristic, NOT a semantic intent classifier.
NEGATED_CLAUSE = re.compile(
    # Retain a positive instruction after "but", "and then", "instead",
    # punctuation, or a newline rather than swallowing the whole task.
    r"\b(?:do\s+not|don['’]t|dont|never|without|no(?=[ \t]))\b"
    r"[^,;.!?\n]*?(?=\b(?:but|and\s+then|instead|then)\b|[,;.!?\n]|$)",
    re.IGNORECASE,
)
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_STATUSES = {"draft", "review", "verified", "deprecated"}
MAX_DESCRIPTOR_BYTES = 256_000
DISCOVERY_BOUNDARY = ("Discovery is metadata-only. Catalogue and native candidates are not "
                      "dispatchable. Curated results require a reviewed dispatcher plan, "
                      "explicit execution flag and host authorization.")


def words(value: str) -> set[str]:
    return set(TOKENS.findall(value.lower()))


# Common task prose is not useful evidence of skill relevance.
# Use conservative, deterministic inflection reduction; never execute skill code.
STOPWORDS = set(
    "a an the in on at to for of is are was were with into when by from and or "
    "but without not no do does dont should have has had this that those these "
    "who which your my me us our it its all any as before after just only please "
    "there what how would could can use using task tasks work workflows workflow".split()
)


def normalized_words(value: str) -> set[str]:
    result = set()
    for token in words(value):
        # Short technical abbreviations (CI, AI, UI, Go) are meaningful even
        # when a query also contains longer words. Remove only stopwords.
        if token in STOPWORDS:
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
    if source.is_symlink() or source.parent.is_symlink() or not source.is_file() or source.stat().st_size > 5_000_000:
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
        marker = Path(root) / path / "UPSTREAM.md"
        if marker.exists() or marker.is_symlink():
            raise ValueError("Catalogue contains external provenance: " + name)
        row = {"name": name, "path": path, "description": description,
               "category": category, "status": status,
               "source": "catalogue", "execution": "not-dispatchable"}
        for field in ("signals", "exclude"):
            if field in item:
                row[field] = discovery_phrases(item[field], name)
        for field in ("compatibility", "license"):
            if field in item:
                value = item[field]
                if not isinstance(value, str) or not value.strip() or len(value) > 1024:
                    raise ValueError(f"Invalid {field} in {name}")
                row[field] = value
        results.append(row)
    return results


def descriptor_path(root: Path, folder: str) -> Path:
    relative = Path(folder) / "SKILL.md"
    path = root
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ValueError("Symlinked skill descriptor: " + folder)
    if not path.is_file():
        raise ValueError("Skill descriptor not found: " + folder)
    return path


def descriptor_description(path: Path, name: str) -> str:
    """Read only the bounded frontmatter of an installed descriptor."""
    metadata = []
    remaining = 8192
    with path.open(encoding="utf-8") as stream:
        first = stream.readline(remaining + 1)
        if first != "---\n":
            raise ValueError("Skill descriptor missing frontmatter: " + name)
        remaining -= len(first)
        for _ in range(100):
            line = stream.readline(remaining + 1)
            if len(line) > remaining:
                raise ValueError("Skill descriptor frontmatter too large: " + name)
            remaining -= len(line)
            if line.rstrip("\n") == "---":
                break
            if not line:
                raise ValueError("Skill descriptor unclosed frontmatter: " + name)
            metadata.append(line)
        else:
            raise ValueError("Skill descriptor frontmatter too large: " + name)
    names = [line.split(":", 1)[1].strip().strip("\"'")
             for line in metadata if line.startswith("name:")]
    descriptions = [line.split(":", 1)[1].strip().strip("\"'")
                    for line in metadata if line.startswith("description:")]
    if names != [name] or len(descriptions) != 1 or not descriptions[0]:
        raise ValueError("Invalid skill name or description in " + name)
    if ((path.parent / "UPSTREAM.md").exists() or (path.parent / "UPSTREAM.md").is_symlink()
            or any(line.startswith(("upstream:", "upstream-")) for line in metadata)):
        raise ValueError("External skill provenance in " + name)
    return descriptions[0]


def host_entry(root: Path, name: str, *, curated: bool) -> dict:
    base = "plugins/shards-core/skills" if curated else ".agents/skills"
    folder = f"{base}/{name}"
    path = descriptor_path(root, folder)
    source = "curated" if curated else "native"
    row = {"name": name, "path": folder, "description": descriptor_description(path, name),
           "category": "curated" if curated else "agents",
           "status": "curated" if curated else "candidate", "source": source,
           "execution": "dispatcher-plan-required" if curated else "not-dispatchable"}
    if not curated:
        row["variant_of"] = name.replace("shards-native-", "shards-", 1)
    return row


def curated_entries(root: Path = ROOT) -> list[dict]:
    return [host_entry(Path(root), name, curated=True) for name in sorted(REGISTRY)]


def native_entries(root: Path = ROOT) -> list[dict]:
    base = Path(root) / ".agents" / "skills"
    return [host_entry(Path(root), path.parent.name, curated=False)
            for path in sorted(base.glob("shards-native-*/SKILL.md"))
            if NAME.fullmatch(path.parent.name)]


def discovery_entries(root: Path = ROOT) -> list[dict]:
    entries = catalogue_entries(root) + curated_entries(root) + native_entries(root)
    if len({entry["name"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate identifiers across skill sources")
    return entries


def phrase(value: str) -> str:
    return " " + " ".join(word for word in TOKENS.findall(value.lower())
                            if word not in {"a", "an", "the", "this"}) + " "


def matching_terms(query_forms: dict[str, set[str]], terms: set[str]) -> set[str]:
    return {word for word, forms in query_forms.items() if forms & terms}


def rank(entries: list[dict], query: str, *, category: str | None = None,
         status: str | None = None) -> list[dict]:
    if not words(query):
        raise ValueError("Query must contain at least one letter or number")
    negated_clauses = NEGATED_CLAUSE.findall(query)
    positive_query = NEGATED_CLAUSE.sub(" ", query)
    if not words(positive_query):
        return []
    raw_words = words(positive_query)
    query_words = raw_words - STOPWORDS
    term_words = normalized_words if query_words else words
    query_forms = {word: term_words(word) for word in query_words or raw_words}
    excluded_names = set().union(*(term_words(clause) for clause in negated_clauses))
    excluded_names.difference_update(set().union(*query_forms.values()))
    query_phrase = phrase(positive_query)
    full_phrase = phrase(query)
    indexed = []
    frequencies = Counter()
    for entry in entries:
        terms = (term_words(entry["name"]), term_words(entry["description"]),
                 term_words(" ".join(entry.get("signals", []))))
        indexed.append((entry, terms))
        frequencies.update(matching_terms(query_forms, set().union(*terms)))

    def weight(term: str) -> int:
        return 4 if frequencies[term] <= max(2, len(entries) // 12) else 1

    ranked = []
    for entry, (name_terms, desc_terms, signal_terms) in indexed:
        if (category and category != entry["category"]) or (status and status != entry["status"]):
            continue
        name_phrase = phrase(entry["name"])
        explicit_name = name_phrase in query_phrase
        if entry.get("variant_of") and status != "candidate" and not explicit_name:
            continue
        if excluded_names & name_terms or any(phrase(value) in full_phrase for value in entry.get("exclude", [])):
            continue
        name_hits = matching_terms(query_forms, name_terms)
        desc_hits = matching_terms(query_forms, desc_terms) - name_hits
        signal_hits = matching_terms(query_forms, signal_terms) - name_hits - desc_hits
        category_match = bool(matching_terms(query_forms, term_words(entry["category"])))
        matched_phrases = [value for value in entry.get("signals", [])
                           if phrase(value) in query_phrase]
        matches = name_hits | desc_hits | signal_hits
        if not (explicit_name or matched_phrases or len(matches) >= 2
                or any(len(term) <= 3 and weight(term) > 1 for term in name_hits)
                or (len(query_forms) == 1 and (matches or category_match))):
            continue
        score = (10 * sum(map(weight, name_hits)) + 3 * sum(map(weight, desc_hits))
                 + 4 * sum(map(weight, signal_hits)) + int(category_match)
                 + max((12 * min(len(words(value)), 5) for value in matched_phrases), default=0)
                 + 42 * explicit_name
                 + 80 * (name_phrase == query_phrase))
        ranked.append({**entry, "score": score, "reason": {
            "name_phrase": explicit_name, "intent_phrases": matched_phrases,
            "name_terms": sorted(name_hits), "description_terms": sorted(desc_hits),
            "signal_terms": sorted(signal_hits), "category_match": category_match,
        }})
    ranked.sort(key=lambda item: (-item["score"],
                                  item["execution"] != "dispatcher-plan-required",
                                  item["name"]))
    return ranked


def discover(query: str, *, root: Path = ROOT, category: str | None = None,
             status: str | None = None, limit: int = 10) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if len(query) > 4096:
        raise ValueError("Query exceeds 4096 characters")
    entries = discovery_entries(root)
    matches = rank(entries, query, category=category, status=status)
    return {"query": query, "candidate_count": len(entries),
            "match_count": len(matches), "results": matches[:limit],
            "trust_boundary": DISCOVERY_BOUNDARY}


def retrieve(name: str, root: Path = ROOT) -> dict:
    """Read just one named descriptor from its expected repository location."""
    if not NAME.fullmatch(name):
        raise ValueError("Invalid skill identifier")
    root = Path(root)
    if name in REGISTRY:
        entry = host_entry(root, name, curated=True)
    elif name.startswith("shards-native-"):
        entry = host_entry(root, name, curated=False)
    else:
        folder = "skills/" + name
        path = descriptor_path(root, folder)
        if path.stat().st_size > MAX_DESCRIPTOR_BYTES:
            raise ValueError("Skill descriptor exceeds retrieval size limit")
        entry = catalogue_entry(path, root)
        entry.update(source="catalogue", execution="not-dispatchable")
    path = descriptor_path(root, entry["path"])
    if path.stat().st_size > MAX_DESCRIPTOR_BYTES:
        raise ValueError("Skill descriptor exceeds retrieval size limit")
    return {**entry, "descriptor_path": path.relative_to(root).as_posix(),
            "descriptor": path.read_text(encoding="utf-8"),
            "trust_boundary": "Skill instructions inform workflow. The host controls permission and execution."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="Task terms to match against metadata")
    mode.add_argument("--skill", help="Retrieve one exact skill descriptor")
    parser.add_argument("--category", help="Exact category filter")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES | {"curated", "candidate"}))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        if args.skill is not None:
            if args.category or args.status or args.limit != 10:
                parser.error("Filters are only available with --query")
            result = retrieve(args.skill)
        else:
            result = discover(args.query, category=args.category, status=args.status, limit=args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
