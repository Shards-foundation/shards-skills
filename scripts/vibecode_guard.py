#!/usr/bin/env python3
"""Read-only, heuristic checks for tracked local source. Never executes project code."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
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
        # Git index reads can invoke core.fsmonitor from local Git config.
        # Override it, disable optional locks and drop inherited GIT_* overrides.
        env = {key: os.environ[key] for key in ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMPDIR", "LANG")
               if key in os.environ}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
        proc = subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
             "-c", "core.hooksPath=" + os.devnull, "-C", str(root),
             "ls-files", "-z", "--cached"],
            capture_output=True, timeout=15, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Cannot enumerate tracked files") from exc
    if proc.returncode:
        raise ValueError("Target is not a readable Git repository")
    # Git paths are byte sequences, not guaranteed UTF-8.
    names = proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return [n for n in names if n]

def open_source(path, flags):
    # Prevent a replaced leaf from redirecting the read or blocking on a FIFO on POSIX.
    return os.open(path, flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))


def source_findings(name, body):
    for number, line in enumerate(body.splitlines(), 1):
        for code, severity, pattern, advice in RULES:
            if pattern.search(line):
                yield {"id": code, "severity": severity, "path": name, "line": number, "advice": advice}


def inspect(root: Path, files: list[str]) -> dict:
    root = root.resolve()
    if not root.is_dir() or len(files) > MAX_FILES:
        raise ValueError("Invalid repository or too many tracked paths")
    names = sorted(set(files))
    findings = []
    skipped = []
    truncated_paths = []
    out_of_scope = inspected = inspected_bytes = bytes_read = 0

    def record(name, matches):
        for finding in matches:
            if len(findings) == MAX_FINDINGS:
                truncated_paths.append(name)
                return False
            findings.append(finding)
        return True

    for name in names:
        try:
            path = relative_file(root, name)
        except (ValueError, OSError, UnicodeError):
            safe_name = name.encode("unicode_escape").decode("ascii")
            skipped.append({"path": safe_name, "reason": "Unsafe or symlinked tracked path"})
            record(safe_name, [{"id": "SKIPPED-UNSAFE-PATH", "severity": "medium", "path": safe_name,
                                "line": None, "advice": "Tracked path could not be inspected safely; review independently"}])
            continue

        size = 0
        try:
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Tracked path is not a regular file")
            if path.name.startswith(".env") and path.name not in {".env.example", ".env.sample", ".env.template"}:
                matches = [{"id": "TRACKED-ENV", "severity": "high", "path": name, "line": None,
                            "advice": "A tracked environment file may disclose credentials; inspect privately and rotate exposed values"}]
            elif path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
                matches = [{"id": "TRACKED-KEY-MATERIAL", "severity": "high", "path": name, "line": None,
                            "advice": "Review whether tracked key or certificate material is private; never expose its contents"}]
            elif path.suffix.lower() not in SOURCE_EXT:
                out_of_scope += 1
                continue
            else:
                size = info.st_size
                if size > MAX_FILE_BYTES:
                    raise ValueError("Source file exceeds per-file byte limit")
                if size > MAX_TOTAL_BYTES - bytes_read:
                    raise ValueError("Remaining scan byte budget is insufficient")
                with open(path, "rb", opener=open_source) as stream:
                    opened = os.fstat(stream.fileno())
                    if not os.path.samestat(info, opened) or opened.st_size != size:
                        raise ValueError("Source file changed before inspection")
                    blob = stream.read(size)
                    bytes_read += len(blob)
                    observed = os.fstat(stream.fileno())
                if (len(blob) != size or observed.st_size != size or not os.path.samestat(info, observed)
                        or observed.st_mtime_ns != info.st_mtime_ns):
                    raise ValueError("Source file changed during inspection")
                if b"\0" in blob:
                    raise ValueError("Source file contains NUL bytes")
                matches = source_findings(name, blob.decode("utf-8"))
        except OSError:
            skipped.append({"path": name, "reason": "Tracked path missing or unreadable"})
            continue
        except UnicodeDecodeError:
            skipped.append({"path": name, "reason": "Source file is not UTF-8"})
            continue
        except ValueError as exc:
            skipped.append({"path": name, "reason": str(exc)})
            continue

        if record(name, matches):
            inspected += 1
            inspected_bytes += size

    incomplete = bool(skipped or truncated_paths)
    status = ("INCOMPLETE_SCAN" if incomplete else
              "WARNINGS_FOUND" if findings else "CLEAR_HEURISTICS_ONLY")
    return {"schema_version": 1, "status": status,
            "risk_boundary": "Heuristic tracked-source inspection only; not a vulnerability scan, safety proof or approval",
            "enumerated_paths": len(names), "out_of_scope_paths": out_of_scope,
            "inspected_paths": inspected, "inspected_source_bytes": inspected_bytes,
            "skipped_paths": skipped, "truncated_paths": truncated_paths,
            "truncated": bool(truncated_paths), "incomplete": incomplete, "findings": findings}


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
        return 2 if result["incomplete"] else (1 if result["findings"] else 0)
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
