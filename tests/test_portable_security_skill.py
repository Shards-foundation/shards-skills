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
from unittest.mock import patch
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

    def test_symlinked_parent_directory_is_rejected_for_sync_and_verify(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            self._stage(work)
            source = work / "skills" / portable.NAME / "scripts"
            outside = work / "outside"
            source.rename(outside)
            source.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked"):
                portable.verify(work)
            with self.assertRaisesRegex(ValueError, "symlinked path component"):
                portable.sync(work)

    def test_dangling_output_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            target = work / "skill.zip"
            redirected = work / "outside.zip"
            target.symlink_to(redirected)
            self.assertFalse(redirected.exists())
            with self.assertRaisesRegex(ValueError, "symlinked path component"):
                portable.build_zip(ROOT, target)
            self.assertFalse(redirected.exists())

    def test_sync_repairs_drift_only_from_canonical_source(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location)
            self._stage(work)
            target = work / "skills" / portable.NAME / portable.SOURCES[1]
            target.write_bytes(b"stale")
            portable.sync(work)
            self.assertEqual(portable.verify(work)[portable.SOURCES[1]],
                             hashlib.sha256((work / portable.SOURCES[1]).read_bytes()).hexdigest())

    def test_no_overwrite_existing_output_or_bundle_input(self):
        with tempfile.TemporaryDirectory() as location:
            output = Path(location).resolve() / "existing.zip"
            output.write_bytes(b"keep-existing-file")
            with self.assertRaises(FileExistsError):
                portable.build_zip(ROOT, output)
            self.assertEqual(output.read_bytes(), b"keep-existing-file")
            source = ROOT / "skills" / portable.NAME / "SKILL.md"
            before = source.read_bytes()
            with self.assertRaises(FileExistsError):
                portable.build_zip(ROOT, source)
            self.assertEqual(source.read_bytes(), before)

    def test_unlisted_skill_files_and_links_fail_closed(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location).resolve()
            self._stage(work)
            rogue = work / "skills" / portable.NAME / "unexpected.txt"
            rogue.write_text("not reviewed")
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                portable.verify(work)
            rogue.unlink()
            skill = work / "skills" / portable.NAME / "SKILL.md"
            skill.write_text(skill.read_text() + "\n[Missing](docs/not-present.md)\n")
            with self.assertRaisesRegex(ValueError, "Missing or external"):
                portable.verify(work)

    def test_input_change_between_verify_and_stage_blocks_without_output(self):
        with tempfile.TemporaryDirectory() as location:
            work = Path(location).resolve()
            self._stage(work)
            output = work / "attempt.zip"
            original_verify = portable.verify
            def changed_after_verify(root):
                hashes = original_verify(root)
                destination = work / "skills" / portable.NAME / portable.SOURCES[0]
                destination.write_bytes(b"modified-after-verification")
                return hashes
            with patch.object(portable, "verify", side_effect=changed_after_verify):
                with self.assertRaisesRegex(ValueError, "Changed skill input"):
                    portable.build_zip(work, output)
            self.assertFalse(output.exists())

    def test_zip_is_deterministic_and_manifest_matches_files(self):
        with tempfile.TemporaryDirectory() as location:
            a, b = Path(location).resolve() / "a.zip", Path(location).resolve() / "b.zip"
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

    def test_security_inputs_reject_duplicate_keys_and_boolean_schema(self):
        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        assurance = load("assurance", "security_assurance.py")
        evaluator = load("skill_evaluator", "security_skill_eval.py")
        with tempfile.TemporaryDirectory() as location:
            work = Path(location).resolve()
            receipt = work / "receipt.json"
            receipt.write_text('{"schema_version":1,"schema_version":true}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON object key"):
                assurance.read_json(receipt)
            with self.assertRaisesRegex(ValueError, "Duplicate JSON object key"):
                evaluator.read(receipt)
            original_registry = json.loads((ROOT / "catalogue/shards-security-controls.json").read_text())
            original_registry["schema_version"] = True
            receipt.write_text(json.dumps(original_registry))
            with patch.object(assurance, "REGISTRY", receipt):
                with self.assertRaisesRegex(ValueError, "Unsupported control registry"):
                    assurance.registry()
            original_registry["schema_version"] = 1
            original_registry["controls"] = []
            receipt.write_text(json.dumps(original_registry))
            with patch.object(assurance, "REGISTRY", receipt):
                with self.assertRaisesRegex(ValueError, "Unsupported control registry"):
                    assurance.registry()

    def test_frozen_cases_cannot_be_redefined_silently(self):
        spec = importlib.util.spec_from_file_location("evaluator_case", ROOT / "scripts/security_skill_eval.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as location:
            fixture = Path(location).resolve() / "cases.json"
            original = json.loads((ROOT / "evals/shards-security-workflows.json").read_text())
            original["cases"][0]["prompt"] = "Modified prompt for a different test."
            fixture.write_text(json.dumps(original))
            with patch.object(module, "FIXTURE", fixture):
                with self.assertRaisesRegex(ValueError, "digest changed"):
                    module.caseset()
            original["variants"] = {v: 1 for v in original["variants"]}
            fixture.write_text(json.dumps(original))
            digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
            with patch.object(module, "FIXTURE", fixture), patch.object(module, "FROZEN_CASESET_SHA256", digest):
                with self.assertRaisesRegex(ValueError, "Unrecognized evaluator labels"):
                    module.caseset()

    def test_source_guard_rejects_partial_checkouts_and_oversized_skips(self):
        spec = importlib.util.spec_from_file_location("guard", ROOT / "scripts/vibecode_guard.py")
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as location:
            root = Path(location).resolve()
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / "nested").mkdir()
            (root / "nested" / "small.py").write_text("print(1)")
            (root / "huge.py").write_text("a" * (guard.MAX_FILE_BYTES + 1))
            (root / ".env").write_text("synthetic")
            subprocess.run(["git", "-C", str(root), "add", "--", "."], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "exact Git repository top-level"):
                guard.tracked(root / "nested")
            report = guard.inspect(root, guard.tracked(root))
            self.assertEqual(report["status"], "WARNINGS_FOUND")
            self.assertIn("SKIPPED-OVERSIZE-SOURCE", {x["id"] for x in report["findings"]})
            self.assertIn("TRACKED-ENV", {x["id"] for x in report["findings"]})
            # For special-file findings, the report cap also applies.
            for i in range(guard.MAX_FINDINGS + 2):
                (root / (".env_" + str(i))).write_text("dummy")
            list_report = guard.inspect(root, [".env_" + str(i) for i in range(guard.MAX_FINDINGS + 2)])
            self.assertTrue(list_report["truncated"])
            self.assertLessEqual(len(list_report["findings"]), guard.MAX_FINDINGS)

    @staticmethod
    def _stage(work):
        for path in ("skills/" + portable.NAME + "/SKILL.md", *portable.SOURCES):
            target = work / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        portable.sync(work)


if __name__ == "__main__":
    unittest.main()
