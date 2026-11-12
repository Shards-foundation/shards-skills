#!/usr/bin/env python3
"""Read-only, heuristic checks for tracked local source. Never executes project code."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MAX_FILES = 3000
MAX_FILE_BYTES = 256_000
MAX_TOTAL_BYTES = 20_000_000
MAX_FINDINGS = 200
SOURCE_EXT = {".js", ".jsx", ".ts", ".tsx", ".py", ".sql", ".tf", ".yml", ".yaml", ".toml", ".json"}
RULES = [
    ("TLS-VERIFY-DISABLED", "high", re.compile(r"\bverify\s*=\s*False\b|rejectUnauthorized\s*:\s*false\b", re.I), "Review TLS certificate verification; this may permit interception"),
    ("DYNAMIC-EVAL", "medium", re.compile(r"(?<![\w.])eval\s*\("), "Dynamic code evaluation requires a trusted input boundary"),
    ("WEAK-YAML-LOADER", "high", re.compile(r"\byaml\.load\s*\([^\n]*\bLoader\s*=\s*yaml\.(?:Loader|UnsafeLoader)"), "Unsafe deserialisation of untrusted YAML may enable code execution"),
    ("CI-WRITE-ALL", "high", re.compile(r"\bpermissions\s*:\s*write-all\b", re.I), "Broad CI permissions require least-privilege review"),
    ("POTENTIAL-PUBLIC-CORS", "medium", re.compile(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]|(?:origin|Access-Control-Allow-Origin)\s*[:=,]\s*['\"]\*['\"]", re.I), "Wildcard CORS should be reviewed against authentication and credential use"),
    ("DEPLOYMENT-DEBUG", "medium", re.compile(r"(?<![\w])DEBUG\s*=\s*True\b"), "Development debugging must not be exposed in production"),
    ("PERMISSIVE-RLS", "medium", re.compile(r"\bUSING\s*\(\s*true\s*\)", re.I), "Permissive database row policy may expose tenant data"),
]

def relative_file(root: Path, raw: str) -> Path:
    rel = Path(raw)
    if not raw or rel.is_absolute() or ".." in rel.parts or raw.startswith("-") or any(ord(c) < 32 for c in raw):
        raise ValueError("Unsafe tracked path")
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlinked tracked path blocked")
    path = cursor.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Tracked path escapes repository")
    return path

def tracked(root: Path) -> list[str]:
    try:
        proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached"],
                              capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Cannot enumerate tracked files") from exc
    if proc.returncode:
        raise ValueError("Target is not a readable Git repository")
    names = proc.stdout.decode("utf-8").split("\0")
    return [n for n in names if n]

def inspect(root: Path, files: list[str]) -> dict:
    root = root.resolve()
    if not root.is_dir() or len(files) > MAX_FILES:
        raise ValueError("Invalid repository or too many tracked paths")
    findings = []
    consumed = 0
    seen = set()
    for name in sorted(files):
        if name in seen:
            continue
        seen.add(name)
        path = relative_file(root, name)
        if not path.is_file():
            continue
        if path.name.startswith(".env") and path.name not in {".env.example", ".env.sample", ".env.template"}:
            findings.append({"id": "TRACKED-ENV", "severity": "high", "path": name, "line": None,
                "advice": "A tracked environment file may disclose credentials; inspect privately and rotate exposed values"})
            continue
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            findings.append({"id": "TRACKED-KEY-MATERIAL", "severity": "high", "path": name, "line": None,
                "advice": "Review whether tracked key or certificate material is private; never expose its contents"})
            continue
        if path.suffix.lower() not in SOURCE_EXT or path.stat().st_size > MAX_FILE_BYTES:
            continue
        blob = path.read_bytes()
        consumed += len(blob)
        if consumed > MAX_TOTAL_BYTES:
            raise ValueError("Source scan byte budget exceeded")
        if b"\0" in blob:
            continue
        try:
            body = blob.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(body.splitlines(), 1):
            for code, severity, pattern, advice in RULES:
                if pattern.search(line):
                    findings.append({"id": code, "severity": severity, "path": name, "line": number, "advice": advice})
                    if len(findings) >= MAX_FINDINGS:
                        return report(findings, len(seen), consumed, truncated=True)
    return report(findings, len(seen), consumed, truncated=False)

def report(findings: list[dict], inspected: int, byte_count: int, truncated: bool) -> dict:
    return {"schema_version": 1, "status": "WARNINGS_FOUND" if findings else "CLEAR_HEURISTICS_ONLY",
            "risk_boundary": "Heuristic tracked-source inspection only; not a vulnerability scan, safety proof or approval",
            "inspected_paths": inspected, "inspected_source_bytes": byte_count,
            "truncated": truncated, "findings": findings}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo)
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Repository path must be a directory, not symlink")
        result = inspect(root, tracked(root.resolve()))
        content = json.dumps(result, indent=2) + "\n"
        if args.output:
            output = Path(args.output)
            if output.is_symlink():
                raise ValueError("Symlinked output rejected")
            with output.open("x", encoding="utf-8") as stream:
                stream.write(content)
        print(content, end="")
        return 1 if result["findings"] else 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
