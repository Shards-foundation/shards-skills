"""Offline regression tests for portable Agent Skills ZIPs; no imported code runs."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import package_agent_skill as pack


class PortableSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.skill = self.base / "demo-skill"
        self.skill.mkdir()
        self.descriptor = self.skill / "SKILL.md"
        self.descriptor.write_text(
            "---\nname: demo-skill\ndescription: Use for a deterministic offline demonstration.\n---\n"
            "# Demo\n\nPerform one read-only observation and report the evidence.\n",
            encoding="utf-8",
        )

    def test_valid_package_and_correct_zip_root(self):
        errors, files = pack.audit_skill(self.skill)
        self.assertEqual(errors, [])
        self.assertEqual(len(files), 1)
        report = pack.bundle_skill(self.skill, self.base / "out")
        data = (self.base / "out" / "demo-skill.zip").read_bytes()
        self.assertEqual(report["sha256"], hashlib.sha256(data).hexdigest())
        with zipfile.ZipFile(self.base / "out" / "demo-skill.zip") as zf:
            self.assertEqual(zf.namelist(), ["demo-skill/SKILL.md"])
            self.assertEqual(zf.read("demo-skill/SKILL.md"), self.descriptor.read_bytes())
        receipt = json.loads((self.base / "out" / "demo-skill.receipt.json").read_text())
        self.assertEqual(receipt["result"], "PACKAGE_CREATED_NOT_HOST_VERIFIED")

    def test_deterministic_bytes(self):
        first = pack.bundle_skill(self.skill, self.base / "one")["sha256"]
        second = pack.bundle_skill(self.skill, self.base / "two")["sha256"]
        self.assertEqual(first, second)

    def test_unchanged_output_cannot_be_overwritten_implicitly(self):
        dest = self.base / "out"
        pack.bundle_skill(self.skill, dest)
        with self.assertRaises(FileExistsError):
            pack.bundle_skill(self.skill, dest)
        self.assertEqual(pack.bundle_skill(self.skill, dest, replace=True)["skill"],
                         "demo-skill")

    def test_relative_reference_packaged(self):
        ref = self.skill / "references" / "guide.md"
        ref.parent.mkdir()
        ref.write_text("Evidence template.", encoding="utf-8")
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\nSee [guide](references/guide.md).\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])
        with zipfile.ZipFile(self.base / "out.zip", "w"):
            pass

    def test_out_of_package_link_fails_closed(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[fixture](../../evals/security.json)\n")
        self.assertTrue(any("out-of-package" in x
                            for x in pack.audit_skill(self.skill)[0]))
        with self.assertRaises(ValueError):
            pack.bundle_skill(self.skill, self.base / "out")

    def test_missing_reference_fails_closed(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[guide](references/not-here.md)\n")
        self.assertTrue(pack.audit_skill(self.skill)[0])

    def test_unbundled_script_command_fails_closed(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\nRun python scripts/missing.py locally.\n")
        self.assertTrue(any("external or missing" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_symlink_fails_closed(self):
        target = self.base / "secret.txt"
        target.write_text("not for packaging")
        try:
            (self.skill / "external.txt").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not available")
        self.assertTrue(any("symlink" in x for x in pack.audit_skill(self.skill)[0]))

    def test_invalid_name_fails_closed(self):
        self.descriptor.write_text(self.descriptor.read_text().replace(
            "name: demo-skill", "name: wrong-name"))
        self.assertTrue(pack.audit_skill(self.skill)[0])

    def test_missing_description_fails_closed(self):
        self.descriptor.write_text(self.descriptor.read_text().replace(
            "description: Use for a deterministic offline demonstration.",
            "description:"))
        self.assertTrue(pack.audit_skill(self.skill)[0])

    def test_root_output_inside_source_is_forbidden(self):
        with self.assertRaises(ValueError):
            pack.bundle_skill(self.skill, self.skill / "exports")

    def test_unknown_or_imported_skill_is_not_selectable(self):
        with self.assertRaises(ValueError):
            pack.source_path("addy-agent-skills-code-review-and-quality")

    def test_existing_shards_problem_framing_is_self_contained(self):
        errors, files = pack.audit_skill(ROOT / "skills" / "problem-framing")
        self.assertEqual(errors, [])
        self.assertTrue(any(p.name == "SKILL.md" for p in files))


if __name__ == "__main__":
    unittest.main()
