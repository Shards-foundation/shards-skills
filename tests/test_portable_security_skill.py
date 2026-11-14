"""Offline acceptance checks for the self-contained Shards Manus skill."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("portable", ROOT / "scripts" / "build_portable_security_skill.py")
portable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portable)


class PortableSkillTests(unittest.TestCase):
    def test_checked_in_bundle_is_complete_and_current(self):
        hashes = portable.verify(ROOT)
        self.assertEqual(len(hashes), 8)
        self.assertIn("scripts/security_assurance.py", hashes)

    def test_skill_references_are_self_contained(self):
        root = ROOT / "skills" / portable.NAME
        description = (root / "SKILL.md").read_text()
        for path in portable.SOURCES:
            self.assertTrue((root / path).exists(), path)
        self.assertIn("evals/shards-security-workflows.json", description)
        self.assertNotIn("../../evals/", description)
        self.assertIn("mark executable verification BLOCKED", description)

    def test_corrupt_copy_fails_closed(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            self._stage(work)
            target = work / "skills" / portable.NAME / portable.SOURCES[0]
            target.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "Stale portable copy"):
                portable.verify(work)

    def test_missing_or_symlinked_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            self._stage(work)
            target = work / "skills" / portable.NAME / portable.SOURCES[0]
            target.unlink()
            with self.assertRaisesRegex(ValueError, "Missing"):
                portable.verify(work)
            target.symlink_to(work / portable.SOURCES[0])
            with self.assertRaisesRegex(ValueError, "symlinked"):
                portable.verify(work)

    def test_sync_repairs_drift_only_from_canonical_source(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            self._stage(work)
            target = work / "skills" / portable.NAME / portable.SOURCES[1]
            target.write_bytes(b"stale")
            portable.sync(work)
            self.assertEqual(portable.verify(work)[portable.SOURCES[1]],
                             hashlib.sha256((work / portable.SOURCES[1]).read_bytes()).hexdigest())

    def test_zip_is_deterministic_and_manifest_matches_files(self):
        with tempfile.TemporaryDirectory() as location:
            a, b = Path(location) / "a.zip", Path(location) / "b.zip"
            portable.build_zip(ROOT, a)
            portable.build_zip(ROOT, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                expected = {f"{portable.NAME}/{p}" for p in ("SKILL.md", *portable.SOURCES, "MANIFEST.json")}
                self.assertEqual(set(archive.namelist()), expected)
                manifest = json.loads(archive.read(f"{portable.NAME}/MANIFEST.json"))
                self.assertFalse(manifest["host_traces_verified"])
                for path, digest in manifest["file_sha256"].items():
                    self.assertEqual(hashlib.sha256(archive.read(f"{portable.NAME}/{path}")).hexdigest(), digest)

    def test_isolated_zip_runs_real_offline_plan_and_frozen_cases(self):
        with tempfile.TemporaryDirectory() as location:
            path = Path(location)
            archive = path / "skill.zip"
            portable.build_zip(ROOT, archive)
            with zipfile.ZipFile(archive) as skill:
                skill.extractall(path / "isolated")
            skillroot = path / "isolated" / portable.NAME
            def cli(script, *args):
                result = subprocess.run([sys.executable, str(skillroot / "scripts" / script), *args],
                                        cwd=skillroot, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            capabilities = cli("security_assurance.py", "list")
            self.assertIn("ai", json.dumps(capabilities))
            plan = cli("security_assurance.py", "plan", "--system", "Sandbox agent",
                       "--profiles", "base,ai")
            self.assertIn("ai", json.dumps(plan))
            self.assertGreater(len(plan.get("controls", [])), 0)
            cases = cli("security_skill_eval.py", "cases")
            self.assertEqual(cases["case_count"], 24)
            self.assertEqual(cases["skill_count"], 6)
            result = subprocess.run([sys.executable, str(skillroot / "scripts" / "vibecode_guard.py"), "--help"],
                                    cwd=skillroot, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    @staticmethod
    def _stage(work):
        for path in ("skills/" + portable.NAME + "/SKILL.md", *portable.SOURCES):
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        portable.sync(work)


if __name__ == "__main__":
    unittest.main()
