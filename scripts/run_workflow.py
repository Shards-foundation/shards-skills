#!/usr/bin/env python3
"""Repository-root entry point for the curated Shards workflows."""
from pathlib import Path
import runpy
if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "plugins/shards-core/scripts/run.py"
    runpy.run_path(str(target), run_name="__main__")
