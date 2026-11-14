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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST_PARTY = set("""
problem-framing implementation-planning systematic-debugging
test-driven-development code-review secure-code-review threat-modeling
skill-supply-chain-audit smart-contract-review release-readiness
incident-runbook agent-system-design tool-contract-design
evidence-based-research reproducible-data-analysis
frontend-accessibility-review web-application-testing writing-skill-packages
shards-sec-intake shards-sec-vibecoding-gate
shards-sec-business-threat-model shards-sec-identity-access
shards-sec-secrets-keys shards-sec-web-api shards-sec-cloud-devsecops
shards-sec-supply-chain shards-sec-vulnerability-management
shards-sec-incident-response shards-sec-detection-response
shards-sec-human-fraud shards-sec-privacy-dpia
shards-sec-governance-policy shards-sec-jurisdiction-scope
shards-sec-compliance-evidence shards-sec-third-party-risk
shards-sec-resilience-recovery shards-sec-fintech-payments
shards-sec-crypto-custody shards-sec-defi-protocol
shards-sec-ai-agent-boundaries shards-sec-prompt-injection
shards-sec-authorized-testing shards-sec-crypto-fincrime
""".split())
CURATED = set("""
shards-repository-health shards-skill-audit shards-release-gate
shards-agent-handoff shards-automation-operator shards-catalogue-sync
shards-skill-dispatch shards-a2a-harness shards-dual-channel
shards-subagents shards-parallel-swarm
""".split())
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PATHS = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:scripts|references|assets|docs|evals)/"
    r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.(?:py|md|json|sh|yml|yaml))"
)
LINKS = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MAX_FILES = 1000
MAX_BYTES = 25 * 1024 * 1024


def source_path(name: str) -> Path:
    if name in FIRST_PARTY:
        return ROOT / "skills" / name
    if name in CURATED:
        return ROOT / "plugins" / "shards-core" / "skills" / name
    raise ValueError("not in the explicit Shards first-party allowlist")


def audit_skill(folder: Path) -> tuple[list[str], list[Path]]:
    """Validate a skill as an independent upload, not merely within a checkout."""
    errors: list[str] = []
    files: list[Path] = []
    if folder.is_symlink() or not folder.is_dir():
        return ["skill root is missing, not a directory or is a symlink"], files
    root = folder.resolve()
    descriptor = folder / "SKILL.md"
    if descriptor.is_symlink() or not descriptor.is_file():
        return ["SKILL.md missing or is a symlink"], files
    try:
        text = descriptor.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ["SKILL.md cannot be decoded as UTF-8"], files
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append("SKILL.md must start with YAML frontmatter")
    else:
        try:
            end = lines.index("---", 1)
        except ValueError:
            errors.append("SKILL.md has no closing frontmatter delimiter")
        else:
            metadata: dict[str, str] = {}
            for line in lines[1:end]:
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if line[0].isspace() or ":" not in line:
                    continue  # Nested optional YAML is permitted by the standard.
                key, value = line.split(":", 1)
                if key in metadata:
                    errors.append(f"duplicate metadata field: {key}")
                metadata[key] = value.strip().strip("'\"")
            name = metadata.get("name", "")
            description = metadata.get("description", "")
            if not NAME.fullmatch(name) or len(name) > 64 or name != folder.name:
                errors.append("frontmatter name must match kebab-case directory (max 64)")
            if not 1 <= len(description) <= 1024:
                errors.append("description must contain 1-1024 characters")
            if not "\n".join(lines[end + 1:]).strip():
                errors.append("SKILL.md requires a nonempty instruction body")

    for p in sorted(folder.rglob("*")):
        if p.is_symlink():
            errors.append(f"symlink is forbidden in portable bundle: {p.relative_to(folder)}")
            continue
        if not p.resolve().is_relative_to(root):
            errors.append("package path escapes skill root")
            continue
        if p.is_file():
            files.append(p)
        elif not p.is_dir():
            errors.append(f"unsupported file type: {p.relative_to(folder)}")
    if len(files) > MAX_FILES:
        errors.append(f"package exceeds {MAX_FILES} files")
    if sum(p.stat().st_size for p in files) > MAX_BYTES:
        errors.append(f"package exceeds {MAX_BYTES} bytes")

    for raw in LINKS.findall(text):
        link = raw.split("#", 1)[0].strip()
        if not link or re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or link.startswith("//"):
            continue
        # URL-escaped paths and links with titles need review, not an invented pass.
        if "%" in link or (" " in link and not (folder / link).exists()):
            errors.append(f"cannot resolve portable relative link: {raw}")
            continue
        target = (root / link).resolve()
        if not target.is_relative_to(root):
            errors.append(f"out-of-package link: {raw}")
        elif not target.exists() or target.is_symlink():
            errors.append(f"missing or symlinked package link: {raw}")
    # Catch bare repo-root script/reference commands that are not Markdown links.
    for ref in sorted(set(PATHS.findall(text))):
        target = root / ref
        if not target.is_file() or target.is_symlink():
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
    if not replace and (archive.exists() or receipt.exists()):
        raise FileExistsError("output exists; use --replace after reviewing it")
    file_hashes = {}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            rel = file.relative_to(root).as_posix()
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
    fd, tmp = tempfile.mkstemp(prefix=".shards-skill-", dir=dest)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp, archive)
        receipt.write_bytes(receipt_bytes)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
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
