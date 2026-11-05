#!/usr/bin/env python3
"""Local CLI adapter to the centrally governed Shards Agent Core workflow."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    sys.argv.insert(1, "audit-skill")
    runpy.run_path(str(root / "plugins/shards-core/scripts/run.py"), run_name="__main__")
