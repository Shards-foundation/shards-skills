#!/usr/bin/env python3
"""Dependency-free structural and heuristic security validation for SKILL.md packages."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Heuristic flags for human review. These are not proof of maliciousness or safety.
RISK_PATTERNS = [
    ("credential-exfiltration", re.compile(r"(?i)(send|upload|post|exfiltrat\w*).{0,80}(token|secret|credential|private key|\.env)")),
    ("safeguard-bypass", re.compile(r"(?i)(ignore|bypass|disable|evade).{0,60}(security|policy|approval|safeguard|permission)")),
    ("destructive-shell", re.compile(r"(?i)\b(rm\s+-rf\s+/(?:\s|$)|mkfs\.|dd\s+if=|curl\S*\s+[^\n|]+\|\s*(sh|bash))")),
    ("secret-disclosure", re.compile(r"(?i)(print|reveal|expose|dump).{0,50}(system prompt|environment variables|api keys|secrets)")),
]

def parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        raise ValueError("frontmatter must start at line 1 with ---")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("frontmatter closing --- is missing")
    meta = {}
    for line in parts[1].strip().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line!r}; use simple key: value fields")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or key in meta:
            raise ValueError(f"empty or duplicate metadata key: {key!r}")
        if value.startswith(("[", "{", "|", ">")):
            raise ValueError(f"complex YAML is not supported by baseline validator: {key}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key] = value
    return meta, parts[2].lstrip("\n")

def validate_one(path: Path):
    errors, warnings = [], []
    try:
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"{path.relative_to(ROOT)}: {exc}"], []
    expected = path.parent.name
    name = meta.get("name", "")
    desc = meta.get("description", "")
    if not NAME_RE.fullmatch(expected): errors.append(f"{path}: directory name must be kebab-case")
    if name != expected: errors.append(f"{path}: metadata name {name!r} must match directory {expected!r}")
    if not NAME_RE.fullmatch(name): errors.append(f"{path}: invalid skill name")
    if len(desc) < 20: errors.append(f"{path}: description must be at least 20 characters")
    if len(desc) > 1024: errors.append(f"{path}: description exceeds 1024 characters")
    if len(body.strip()) < 100: errors.append(f"{path}: body too short to be an actionable skill")
    for heading in ("## Workflow", "## Output contract", "## Verification", "## Failure handling"):
        if heading.lower() not in body.lower(): warnings.append(f"{path}: recommended section missing: {heading}")
    for code, pattern in RISK_PATTERNS:
        if pattern.search(text): warnings.append(f"{path}: security review flag [{code}] — inspect context manually")
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body):
        if link.startswith(("http://", "https://", "mailto:")) or link.startswith("#"):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        if not target.exists(): errors.append(f"{path}: broken relative link {link!r}")
    return errors, warnings

def main():
    if not SKILLS.exists():
        print("ERROR: skills/ directory does not exist", file=sys.stderr); return 2
    files = sorted(SKILLS.glob("*/SKILL.md"))
    errors, warnings, names = [], [], []
    for path in files:
        e, w = validate_one(path); errors += e; warnings += w
        try:
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8")); names.append(meta.get("name", ""))
        except Exception:
            pass
    if len(names) != len(set(names)): errors.append("duplicate skill names found")
    cat_path = ROOT / "catalogue" / "catalogue.json"
    try:
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        actual = [str(p.parent.relative_to(ROOT)) for p in files]
        if sorted(cat.get("skill_paths", [])) != sorted(actual): errors.append("catalogue/catalogue.json skill_paths do not match discovered skills")
        if cat.get("skill_count") != len(files): errors.append("catalogue/catalogue.json skill_count does not match discovered skills")
    except Exception as exc: errors.append(f"catalogue invalid: {exc}")
    for msg in warnings: print("WARN: " + msg)
    for msg in errors: print("ERROR: " + msg)
    print(f"Validated {len(files)} skills; {len(errors)} errors; {len(warnings)} review warnings.")
    return 1 if errors else 0

if __name__ == "__main__": raise SystemExit(main())
