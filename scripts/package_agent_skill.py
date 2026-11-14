#!/usr/bin/env python3
"""Create a self-contained, deterministic Agent Skills ZIP without executing skill code.

Only explicit Shards-authored skills are selectable. A structurally valid ZIP is
not evidence of host discovery, tool access, safety or task-level effectiveness.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import zipfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# A narrow release allowlist. Other Shards packages are NOT yet standalone:
# several first-party adapters depend on the repository-level runtime.
FIRST_PARTY = set("""
problem-framing implementation-planning systematic-debugging
test-driven-development code-review secure-code-review evidence-based-research
""".split())
CURATED: set[str] = set()  # not independently exportable yet
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PATHS = re.compile(
    r"(?<![A-Za-z0-9_./:-])"
    r"((?:(?:\.\./)|(?:\./))*(?:scripts|references|assets|docs|evals)/"
    r"[A-Za-z0-9_./-]+\.[A-Za-z0-9_-]+|"
    r"(?:\.\./)[A-Za-z0-9_./-]+)"
)
HTML_LINKS = re.compile(r"""(?i)\b(?:href|src)\s*=\s*["']([^"']+)["']""")
EXTERNAL_URLS = re.compile(r"""(?i)(?:https?://|mailto:|www\.|//)[^\s<>)'"]+""")
MAX_FILES = 1000
MAX_BYTES = 25 * 1024 * 1024


def _yaml_string(value: str) -> str:
    """Fail closed on ambiguous YAML scalars; the packager supports flat strings."""
    if not value:
        raise ValueError("empty YAML scalar")
    if value[0] == '"':
        try:
            parsed = json.loads(value)
        except ValueError as exc:
            raise ValueError("invalid double-quoted YAML scalar") from exc
        if not isinstance(parsed, str):
            raise ValueError("expected YAML string")
        return parsed
    if value[0] == "'":
        if len(value) < 2 or value[-1] != "'":
            raise ValueError("unterminated single-quoted YAML scalar")
        inner = value[1:-1]
        if "'" in inner.replace("''", ""):
            raise ValueError("invalid single-quoted YAML escape")
        return inner.replace("''", "'")
    if (value[0] in "[{|>&*!%@" or value[0] == chr(96) or
            value[-1] in "\"'" or re.search(r":(?:\s|$)|\s#", value) or
            value.strip() != value):
        raise ValueError("ambiguous or unsupported unquoted YAML")
    if (value.lower() in {"null", "~", "true", "false", "yes", "no", "on", "off",
                          ".nan", ".inf", "+.inf", "-.inf"} or
            re.fullmatch(r"[-+]?(?:0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|"
                         r"[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][-+]?[0-9]+)?)", value)):
        raise ValueError("YAML scalar is not unambiguously a string")
    return value


def parse_strict_skill_header(text: str) -> tuple[dict[str, str], str]:
    """Parse the conservative Agent Skills YAML scalar subset."""
    rows = text.lstrip("\ufeff").splitlines()
    if not rows or rows[0].strip() != "---":
        raise ValueError("frontmatter must begin on first line")
    try:
        end = next(i for i in range(1, len(rows)) if rows[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("frontmatter closing delimiter missing") from exc
    meta: dict[str, str] = {}
    for row in rows[1:end]:
        if not row.strip() or row.lstrip().startswith("#"):
            continue
        m = re.fullmatch(r"([a-zA-Z][a-zA-Z0-9_-]*):[ \t]*(.*)", row)
        if not m:
            raise ValueError("unsupported or malformed YAML frontmatter field")
        key, val = m.groups()
        if key in meta:
            raise ValueError("duplicate metadata key")
        meta[key] = _yaml_string(val)
    return meta, "\n".join(rows[end + 1:])


def _inline_destinations(markdown: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Linear scan for nested Markdown inline links without regex backtracking."""
    links: list[str] = []
    spans: list[tuple[int, int]] = []
    opened: list[int] = []
    i = 0
    n = len(markdown)
    while i < n:
        ch = markdown[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "[":
            opened.append(i)
        elif ch == "]" and opened:
            begin = opened.pop()
            if i + 1 < n and markdown[i + 1] == "(":
                start = i + 2
                j, depth, angle, quote = start, 1, False, None
                while j < n:
                    cj = markdown[j]
                    if cj == "\\":
                        j += 2
                        continue
                    if cj == "<" and not quote:
                        angle = True
                    elif cj == ">" and not quote:
                        angle = False
                    elif cj in ("'", '"') and not angle:
                        quote = None if quote == cj else (quote or cj)
                    elif not angle and not quote:
                        if cj == "(":
                            depth += 1
                        elif cj == ")":
                            depth -= 1
                            if depth == 0:
                                break
                    j += 1
                if j < n:
                    links.append(markdown[start:j])
                    spans.append((begin, j + 1))
                    i = j
                else:
                    links.append("UNTERMINATED_MARKDOWN_LINK(")
                    i = n
                    continue
        i += 1
    return links, spans


def _reference_destinations(markdown: str) -> tuple[list[str], list[tuple[int, int]]]:
    links: list[str] = []
    spans: list[tuple[int, int]] = []
    offset = 0
    for line in markdown.splitlines(keepends=True):
        match = re.match(r"^[ \t]{0,3}\[([^\]\n]+)\]:[ \t]*(.*)$",
                         line.rstrip("\r\n"))
        if match and not match.group(1).startswith("^") and not match.group(2).startswith("["):
            raw = match.group(2).strip()
            if raw:
                links.append(raw)
                spans.append((offset, offset + len(line)))
        offset += len(line)
    return links, spans


def _target(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("empty link destination")
    if value.startswith("<"):
        end = value.find(">")
        if end < 1:
            raise ValueError("unterminated bracketed destination")
        dest, rest = value[1:end], value[end + 1:].strip()
    else:
        parts = value.split(None, 1)
        dest = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
    if rest and not (
        len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in ("'", '"')
        or rest.startswith("(") and rest.endswith(")")
    ):
        raise ValueError("ambiguous destination or unquoted title")
    return dest


def _validate_target(raw: str, file: Path, root: Path) -> str | None:
    try:
        link = _target(raw).split("#", 1)[0]
    except ValueError as exc:
        return f"unsupported or ambiguous local link: {raw}: {exc}"
    if not link:
        return None
    if link.lower().startswith(("http://", "https://", "mailto:", "//", "www.")):
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or "%" in link:
        return f"unsupported or ambiguous local link: {raw}"
    candidate = file.parent / link
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        return f"out-of-package link: {raw}"
    if not resolved.is_file() or candidate.is_symlink():
        return f"missing or symlinked package link: {raw}"
    return None


def source_path(name: str) -> Path:
    if name in FIRST_PARTY:
        return ROOT / "skills" / name
    if name in CURATED:
        return ROOT / "plugins" / "shards-core" / "skills" / name
    raise ValueError("not in the explicit Shards first-party allowlist")


def _safe_archive_name(path: Path) -> bool:
    """Protect against ZIP traversal and cross-platform filename reinterpretation."""
    if path.is_absolute():
        return False
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"COM{i}" for i in range(1, 10))
    reserved.update(f"LPT{i}" for i in range(1, 10))
    for part in path.parts:
        if (part in {"", ".", ".."} or "\\" in part or ":" in part
                or part.endswith((".", " "))
                or any(ord(char) < 32 for char in part)
                or part.upper().split(".", 1)[0] in reserved):
            return False
    return True


def audit_skill(folder: Path) -> tuple[list[str], list[Path]]:
    """Validate conservative, standalone instruction-only uploads; no script execution."""
    errors: list[str] = []
    files: list[Path] = []
    if folder.is_symlink() or not folder.is_dir():
        return ["skill root is missing, not a directory or is a symlink"], files
    folder = folder.resolve()  # canonicalise symlinked parent directories
    root = folder
    if not _safe_archive_name(Path(folder.name)):
        errors.append("unsafe cross-platform skill directory name")
    descriptor = folder / "SKILL.md"
    if descriptor.is_symlink() or not descriptor.is_file():
        return ["SKILL.md missing or is a symlink"], files
    try:
        if descriptor.stat().st_size > MAX_BYTES:
            return [f"package exceeds {MAX_BYTES} bytes"], files
        text = descriptor.read_text(encoding="utf-8")
        metadata, body = parse_strict_skill_header(text)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"invalid SKILL.md frontmatter: {exc}"], files
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not NAME.fullmatch(name) or len(name) > 64 or name != folder.name:
        errors.append("frontmatter name must match kebab-case directory (max 64)")
    if not 1 <= len(description) <= 1024:
        errors.append("description must contain 1-1024 characters")
    if not body.strip():
        errors.append("SKILL.md requires a nonempty instruction body")

    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if p.is_symlink():
            errors.append(f"symlink forbidden in portable bundle: {rel}")
            continue
        if not _safe_archive_name(rel):
            errors.append(f"unsafe ZIP member path: {rel}")
            continue
        if not p.resolve().is_relative_to(root):
            errors.append(f"package path escapes skill root: {rel}")
            continue
        if p.is_file():
            files.append(p)
        elif not p.is_dir():
            errors.append(f"unsupported file type: {rel}")
    names_seen: set[str] = set()
    for p in files:
        relative_name = p.relative_to(root).as_posix()
        normalized = unicodedata.normalize("NFC", relative_name).casefold()
        if normalized in names_seen:
            errors.append(f"case-insensitive or Unicode-normalized member collision: {relative_name}")
        names_seen.add(normalized)
    if len(files) > MAX_FILES:
        return [f"package exceeds {MAX_FILES} files"], files
    if sum(p.stat().st_size for p in files) > MAX_BYTES:
        return [f"package exceeds {MAX_BYTES} bytes"], files

    # Read all packaged Markdown, including nested references, not just SKILL.md.
    for file in files:
        if file.suffix.lower() != ".md":
            continue
        try:
            markdown = file.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"undecodable packaged Markdown: {file.relative_to(root)}")
            continue
        inline, inline_spans = _inline_destinations(markdown)
        references, reference_spans = _reference_destinations(markdown)
        html = list(HTML_LINKS.finditer(markdown))
        for raw in inline + references + [m.group(1) for m in html]:
            finding = _validate_target(raw, file, root)
            if finding:
                errors.append(finding)
        scrubbed = list(markdown)
        for start, end in inline_spans + reference_spans:
            scrubbed[start:end] = " " * (end - start)
        for m in html:
            start, end = m.span()
            scrubbed[start:end] = " " * (end - start)
        clean = EXTERNAL_URLS.sub("", "".join(scrubbed))
        for ref in sorted(set(PATHS.findall(clean))):
            explicit_relative = ref.startswith(("./", "../"))
            candidate = (file.parent if explicit_relative else root) / ref
            target = candidate.resolve()
            if not target.is_relative_to(root):
                errors.append(f"out-of-package resource: {ref}")
            elif not target.is_file() or candidate.is_symlink():
                errors.append(f"external or missing packaged resource: {ref}")

    return sorted(set(errors)), sorted(files, key=lambda p: p.relative_to(root).as_posix())


def bundle_skill(folder: Path, out_dir: Path, replace: bool = False) -> dict:
    errors, files = audit_skill(folder)
    if errors:
        raise ValueError("; ".join(errors))
    root = folder.resolve()
    dest = out_dir.resolve()
    if dest == root or root in dest.parents:
        raise ValueError("output directory cannot be inside the skill package")
    dest.mkdir(parents=True, exist_ok=True)
    archive = dest / f"{folder.name}.zip"
    receipt = dest / f"{folder.name}.receipt.json"
    if not replace and (os.path.lexists(archive) or os.path.lexists(receipt)):
        raise FileExistsError("output exists; use --replace after reviewing it")
    file_hashes = {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            rel = file.relative_to(root).as_posix()
            if not _safe_archive_name(Path(rel)) or file.is_symlink() or not file.resolve().is_relative_to(root):
                raise ValueError(f"unsafe resource changed during packaging: {rel}")
            data = file.read_bytes()
            file_hashes[rel] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo(f"{folder.name}/{rel}", (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    payload = buffer.getvalue()
    result = {
        "result": "PACKAGE_CREATED_NOT_HOST_VERIFIED",
        "skill": folder.name,
        "archive": str(archive),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "source_commit": os.environ.get("GITHUB_SHA", "not-recorded"),
        "files": file_hashes,
        "note": "ZIP validated for structural portability only; no tool permissions or host execution tested.",
    }
    receipt_bytes = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    # Prepare both files before publishing either; os.replace replaces symlinks
    # instead of writing through them. Two-file replacement is not transactional.
    staged: list[tuple[str, Path]] = []
    try:
        for data, final in ((payload, archive), (receipt_bytes, receipt)):
            fd, temporary = tempfile.mkstemp(prefix=".shards-skill-", dir=dest)
            staged.append((temporary, final))
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        for temporary, final in staged:
            os.replace(temporary, final)
    finally:
        for temporary, _ in staged:
            if os.path.lexists(temporary):
                os.unlink(temporary)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", help="One explicitly selected Shards first-party skill")
    parser.add_argument("--list", action="store_true", help="List allowlisted names; readiness is not implied")
    parser.add_argument("--check", action="store_true", help="Check self-containment without making a ZIP")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist" / "portable-skills")
    parser.add_argument("--replace", action="store_true", help="Explicitly replace prior ZIP and receipt")
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps({"first_party": sorted(FIRST_PARTY), "curated": sorted(CURATED),
                          "warning": "An allowlisted skill may still fail self-containment."}, indent=2))
        return 0
    if not args.skill:
        parser.error("--skill is required unless --list is used")
    try:
        folder = source_path(args.skill)
        errors, files = audit_skill(folder)
        if errors:
            raise ValueError("; ".join(errors))
        if args.check:
            result = {"result": "STRUCTURAL_CHECK_PASS_NOT_HOST_VERIFIED",
                      "skill": args.skill, "file_count": len(files)}
        else:
            result = bundle_skill(folder, args.out_dir, args.replace)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, FileExistsError, OSError) as exc:
        print(json.dumps({"result": "BLOCKED", "skill": args.skill, "reason": str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
