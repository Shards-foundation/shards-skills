import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/checksums.py"


class ChecksumTests(unittest.TestCase):
    def test_repository_manifest_matches_index(self):
        subprocess.run([sys.executable, str(SCRIPT)], cwd=SCRIPT.parents[1], check=True)

    def test_manifest_matches_only_indexed_files_and_detects_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "file").write_bytes(b"first")
            (root / "untracked").write_bytes(b"ignore")
            (root / "__pycache__").mkdir()
            (root / "__pycache__/cache.pyc").write_bytes(b"ignore")
            subprocess.run(["git", "add", "-f", "file", "__pycache__"], cwd=root, check=True)
            cli = [sys.executable, str(SCRIPT)]
            subprocess.run(cli + ["--write"], cwd=root, check=True)
            manifest = root / "SHA256SUMS.json"
            self.assertEqual(json.loads(manifest.read_bytes()), [
                {"path": "file", "sha256": hashlib.sha256(b"first").hexdigest(), "bytes": 5}
            ])
            subprocess.run(["git", "add", "SHA256SUMS.json"], cwd=root, check=True)
            subprocess.run(cli, cwd=root, check=True)
            (root / "file").write_bytes(b"updated")
            subprocess.run(["git", "add", "file"], cwd=root, check=True)
            self.assertEqual(subprocess.run(cli, cwd=root).returncode, 1)
            subprocess.run(cli + ["--write"], cwd=root, check=True)
            self.assertEqual(subprocess.run(cli, cwd=root).returncode, 1)
            subprocess.run(["git", "add", "SHA256SUMS.json"], cwd=root, check=True)
            subprocess.run(cli, cwd=root, check=True)
