#!/usr/bin/env python3
"""Check or refresh SHA256SUMS.json for the files staged in the current repository."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


MANIFEST = "SHA256SUMS.json"


def indexed_manifest() -> bytes:
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"]).split(b"\0")
    records = []
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        path = Path(os.fsdecode(raw_path))
        if stage != b"0":
            raise ValueError(f"Unresolved index entry: {path}")
        if path.as_posix() == MANIFEST or "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
            continue
        if mode not in (b"100644", b"100755", b"120000"):
            raise ValueError(f"Unsupported index mode for {path}: {os.fsdecode(mode)}")
        data = subprocess.check_output(["git", "cat-file", "blob", oid])
        records.append({"path": path.as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return (json.dumps(records, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Replace the manifest from the current Git index")
    args = parser.parse_args()
    root = Path(os.fsdecode(subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).rstrip(b"\n")))
    os.chdir(root)
    expected = indexed_manifest()
    path = root / MANIFEST
    if args.write:
        descriptor, temp = tempfile.mkstemp(dir=root)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(expected)
            os.replace(temp, path)
        finally:
            Path(temp).unlink(missing_ok=True)
    elif path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
        print(f"{MANIFEST} differs from the indexed files", file=sys.stderr)
        return 1
    else:
        staged = subprocess.run(["git", "show", ":" + MANIFEST], capture_output=True)
        if staged.returncode or staged.stdout != expected:
            print(f"Stage the refreshed {MANIFEST}", file=sys.stderr)
            return 1
    print(f"{MANIFEST} matches the indexed files")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
