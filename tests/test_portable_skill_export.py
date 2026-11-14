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
        pack.bundle_skill(self.skill, self.base / "out")
        with zipfile.ZipFile(self.base / "out" / "demo-skill.zip") as zf:
            self.assertIn("demo-skill/references/guide.md", zf.namelist())
            self.assertEqual(zf.read("demo-skill/references/guide.md"), b"Evidence template.")

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

    def test_reject_parent_script_reference(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\nRun python ../../scripts/runner.py\n")
        self.assertTrue(any("out-of-package resource" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_reject_dot_slash_missing_script(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\nRun python ./scripts/missing.py\n")
        self.assertTrue(any("external or missing packaged resource" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_nested_markdown_link_scanned(self):
        ref = self.skill / "references" / "notes.md"
        ref.parent.mkdir()
        ref.write_text("Follow [bad](../../outside.md)\n")
        self.assertTrue(any("out-of-package link" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_malformed_yaml_is_blocked(self):
        self.descriptor.write_text(self.descriptor.read_text().replace(
            "description: Use for a deterministic offline demonstration.",
            "description: [unterminated"))
        self.assertTrue(any("invalid SKILL.md frontmatter" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_cross_platform_filename_is_rejected(self):
        (self.skill / "..\\\\escape.txt").write_text("archive escape attempt")
        self.assertTrue(any("unsafe ZIP member" in x
                            for x in pack.audit_skill(self.skill)[0]))
        with self.assertRaises(ValueError):
            pack.bundle_skill(self.skill, self.base / "out")

    def test_receipt_symlink_replacement_cannot_overwrite_target(self):
        dest = self.base / "out"
        dest.mkdir()
        outside = self.base / "outside.txt"
        outside.write_text("untouched")
        symlink = dest / "demo-skill.receipt.json"
        try:
            symlink.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not available")
        with self.assertRaises(FileExistsError):
            pack.bundle_skill(self.skill, dest)
        report = pack.bundle_skill(self.skill, dest, replace=True)
        self.assertEqual(report["result"], "PACKAGE_CREATED_NOT_HOST_VERIFIED")
        self.assertEqual(outside.read_text(), "untouched")
        self.assertFalse(symlink.is_symlink())
        self.assertEqual(json.loads(symlink.read_text())["skill"], "demo-skill")

    def test_repo_dependent_adapter_not_exportable(self):
        with self.assertRaises(ValueError):
            pack.source_path("release-readiness")
        with self.assertRaises(ValueError):
            pack.source_path("shards-repository-health")

    def test_external_web_urls_are_not_local_script_dependencies(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[docs](https://example.com/docs/guide.md)\n"
                                   "See https://example.com/scripts/run.py\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_nested_markdown_bare_paths_resolve_at_skill_root(self):
        guide = self.skill / "references" / "guide.md"
        guide.parent.mkdir()
        guide.write_text("Run scripts/check.py for a local check.\n")
        script = self.skill / "scripts" / "check.py"
        script.parent.mkdir()
        script.write_text("print('ok')\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])
        report = pack.bundle_skill(self.skill, self.base / "out")
        with zipfile.ZipFile(report["archive"]) as zf:
            self.assertIn("demo-skill/scripts/check.py", zf.namelist())

    def test_frontmatter_triple_dash_inside_description_is_not_delimiter(self):
        self.descriptor.write_text(self.descriptor.read_text().replace(
            "Use for a deterministic offline demonstration.",
            "Use for inputs --- outputs in a deterministic task."))
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_case_insensitive_duplicate_member_names_are_blocked(self):
        (self.skill / "guide.md").write_text("hello")
        (self.skill / "GUIDE.md").write_text("world")
        self.assertTrue(any("collision" in x for x in pack.audit_skill(self.skill)[0]))

    def test_reference_style_link_respects_package_boundary(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[guide]: ../outside.md\n")
        self.assertTrue(any("out-of-package link" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_html_href_missing_file_is_blocked(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   '\n<a href="references/absent.md">Open</a>\n')
        self.assertTrue(any("missing or symlinked package link" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_gfm_footnote_is_not_a_reference_link(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[^1]: Gruber, J. Evidence cited elsewhere.\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_non_link_bracket_definition_is_not_treated_as_link(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[key]: [value]\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_nested_markdown_link_resolves_only_relative_to_file(self):
        guide = self.skill / "references" / "guide.md"
        guide.parent.mkdir()
        scripts = guide.parent / "scripts"
        scripts.mkdir()
        (scripts / "check.py").write_text("print('ok')\n")
        guide.write_text("[run](scripts/check.py)\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_nested_reference_link_resolves_only_relative_to_file(self):
        guide = self.skill / "references" / "guide.md"
        guide.parent.mkdir()
        scripts = guide.parent / "scripts"
        scripts.mkdir()
        (scripts / "check.py").write_text("print('ok')\n")
        guide.write_text("[run]: scripts/check.py\n")
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_invalid_plain_yaml_scalar_values_fail_closed(self):
        bad = ["null", "~", "true", "false", "42", "Use: this skill", "0x42"]
        for value in bad:
            with self.subTest(value=value):
                text = self.descriptor.read_text().replace(
                    "Use for a deterministic offline demonstration.", value)
                self.descriptor.write_text(text)
                errors, _ = pack.audit_skill(self.skill)
                self.assertTrue(errors, value)
                self.descriptor.write_text(text.replace(
                    "description: " + value,
                    "description: Use for a deterministic offline demonstration."))

    def test_quoted_yaml_string_values_are_accepted(self):
        for value in ['"Use: this skill"', "'null'"]:
            with self.subTest(value=value):
                text = self.descriptor.read_text().replace(
                    "Use for a deterministic offline demonstration.", value)
                self.descriptor.write_text(text)
                self.assertEqual(pack.audit_skill(self.skill)[0], [])
                self.descriptor.write_text(text.replace(
                    "description: " + value,
                    "description: Use for a deterministic offline demonstration."))

    def test_deep_unmatched_brackets_do_not_cause_quadratic_scan(self):
        import time
        self.descriptor.write_text(self.descriptor.read_text() + "[" * 100000)
        started = time.monotonic()
        errors, _ = pack.audit_skill(self.skill)
        self.assertEqual(errors, [])
        self.assertLess(time.monotonic() - started, 5.0)

    def test_nested_image_outer_link_escape_is_blocked(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[![image](references/img.png)](../../outside.md)\n")
        (self.skill / "references").mkdir()
        (self.skill / "references/img.png").write_bytes(b"dummy")
        self.assertTrue(any("out-of-package link" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_spaced_reference_destinations_are_not_silently_skipped(self):
        for destination in ["<references/absent guide.md>",
                            "references/absent guide.md"]:
            with self.subTest(destination=destination):
                text = self.descriptor.read_text() + "\n[guide]: " + destination + "\n"
                self.descriptor.write_text(text)
                self.assertTrue(pack.audit_skill(self.skill)[0])
                self.descriptor.write_text(text[:text.rfind("\n[guide]:")])

    def test_empty_directory_is_not_exportable_as_link_target(self):
        (self.skill / "references/empty").mkdir(parents=True)
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[dir](references/empty)\n")
        self.assertTrue(any("missing or symlinked" in x
                            for x in pack.audit_skill(self.skill)[0]))

    def test_additional_resource_extensions_are_checked(self):
        for ref in ("references/missing.txt", "scripts/tool.js",
                    "assets/table.csv", "assets/img.png", "../AGENTS.md"):
            with self.subTest(ref=ref):
                text = self.descriptor.read_text() + "\nUse " + ref + " now.\n"
                self.descriptor.write_text(text)
                self.assertTrue(pack.audit_skill(self.skill)[0], ref)
                self.descriptor.write_text(text[:text.rfind("\nUse ")])

    def test_oversized_content_is_rejected_before_markdown_scan(self):
        (self.skill / "big.md").write_bytes(b"\xff" * (26 * 1024 * 1024))
        errors, _ = pack.audit_skill(self.skill)
        self.assertTrue(any("exceeds" in e for e in errors))
        self.assertFalse(any("undecodable" in e for e in errors))

    def test_titled_markdown_link_is_accepted(self):
        guide = self.skill / "references" / "guide.md"
        guide.parent.mkdir()
        guide.write_text("Evidence")
        self.descriptor.write_text(self.descriptor.read_text() +
                                   '\n[guide](references/guide.md "A title")\n')
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_bom_frontmatter_does_not_crash_audit(self):
        self.descriptor.write_text("\ufeff" + self.descriptor.read_text())
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_symlinked_ancestor_does_not_raise(self):
        real = self.base / "real"
        real.mkdir()
        (real / "demo-skill").mkdir()
        (real / "demo-skill" / "SKILL.md").write_text(
            self.descriptor.read_text())
        try:
            (self.base / "alias").symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unsupported")
        errors, _ = pack.audit_skill(self.base / "alias" / "demo-skill")
        self.assertEqual(errors, [])

    def test_external_uppercase_schemes_do_not_fail_link_audit(self):
        self.descriptor.write_text(self.descriptor.read_text() +
                                   "\n[website](HTTPS://example.com/scripts/tool.js)\n"
                                   "[resource]: MAILTO:hello@example.com\n"
                                   '<a href="HTTP://example.com/references/guide.md">site</a>\n')
        self.assertEqual(pack.audit_skill(self.skill)[0], [])

    def test_oversized_skill_md_is_blocked_before_utf8_decode(self):
        self.descriptor.write_bytes(b"\xff" * (26 * 1024 * 1024))
        errors, _ = pack.audit_skill(self.skill)
        self.assertTrue(any("exceeds" in e for e in errors))
        self.assertFalse(any("cannot be decoded" in e for e in errors))

    def test_existing_shards_problem_framing_is_self_contained(self):
        errors, files = pack.audit_skill(ROOT / "skills" / "problem-framing")
        self.assertEqual(errors, [])
        self.assertTrue(any(p.name == "SKILL.md" for p in files))


if __name__ == "__main__":
    unittest.main()
