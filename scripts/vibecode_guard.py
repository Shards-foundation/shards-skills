#!/usr/bin/env python3
"""Read-only, heuristic checks for tracked local source. Never executes project code."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_FILES = 3000
MAX_INDEX_BYTES = 1_000_000
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
    root = root.resolve()
    try:
        # Disable inherited Git overrides, FS monitors and hooks. Track files
        # only from the exact checkout root, not a nested path within a repo.
        env = {key: os.environ[key] for key in ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMPDIR", "LANG")
               if key in os.environ}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
        base = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                "-c", "core.hooksPath=" + os.devnull, "-C", str(root)]
        top = subprocess.run(base + ["rev-parse", "--show-toplevel"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=15, check=False, env=env)
        if top.returncode or Path(top.stdout.decode("utf-8", errors="surrogateescape").strip()).resolve() != root:
            raise ValueError("Target must be exact Git repository top-level")
        # Don't retain an unbounded attacker-controlled index in RAM.
        with tempfile.TemporaryFile() as output:
            proc = subprocess.run(base + ["ls-files", "-z", "--cached"],
                                  stdout=output, stderr=subprocess.DEVNULL,
                                  timeout=15, check=False, env=env)
            output.seek(0, 2)
            if output.tell() > MAX_INDEX_BYTES:
                raise ValueError("Git tracked-file index exceeds safe budget")
            output.seek(0)
            raw = output.read(MAX_INDEX_BYTES + 1)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise ValueError("Cannot enumerate tracked files") from exc
    if proc.returncode:
        raise ValueError("Target is not a readable Git repository")
    names = raw.decode("utf-8", errors="surrogateescape").split("\0")
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
        try:
            path = relative_file(root, name)
        except (ValueError, OSError, UnicodeError):
            # Preserve useful results for other files. Never follow a symlink.
            findings.append({"id": "SKIPPED-UNSAFE-PATH", "severity": "medium",
                             "path": name.encode("unicode_escape").decode("ascii"),
                             "line": None,
                             "advice": "Tracked path could not be inspected safely; review independently"})
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True)
            continue
        if not path.is_file():
            findings.append({"id": "SKIPPED-MISSING-PATH", "severity": "medium", "path": name, "line": None,
                             "advice": "Tracked path unavailable in working tree; inspect checkout completeness"})
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True)
            continue
        if path.name.startswith(".env") and path.name not in {".env.example", ".env.sample", ".env.template"}:
            findings.append({"id": "TRACKED-ENV", "severity": "high", "path": name, "line": None,
                "advice": "A tracked environment file may disclose credentials; inspect privately and rotate exposed values"})
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True)
            continue
        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            findings.append({"id": "TRACKED-KEY-MATERIAL", "severity": "high", "path": name, "line": None,
                "advice": "Review whether tracked key or certificate material is private; never expose its contents"})
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True)
            continue
        if path.suffix.lower() not in SOURCE_EXT:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            findings.append({"id": "SKIPPED-OVERSIZE-SOURCE", "severity": "medium", "path": name,
                             "line": None, "advice": "Source exceeds per-file scan limit; inspect independently"})
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True)
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
        for number, line in enumerate(body.split("\n"), 1):
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
