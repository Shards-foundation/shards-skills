"""Regression tests for evidence-gated skill revisions."""
import importlib.util
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skill_improver", ROOT / "scripts" / "skill_improver.py")
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)

def content(extra):
    return ("---\nname: sample-skill\ndescription: \"A sample first party skill description long enough\"\n---\n"
            "\n# Sample Skill\n\n## Workflow\nReview evidence and make a scoped change.\n"
            "## Output contract\nReturn evidence.\n## Verification\nRun tests.\n"
            "## Failure handling\nFail closed on ambiguity.\n" + extra).encode()

class ImproverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "skills" / "sample-skill"
        folder.mkdir(parents=True)
        self.target = folder / "SKILL.md"
        self.original = content("original")
        self.candidate = content("improved")
        self.target.write_bytes(self.original)
        self.new = self.root / "candidate.md"
        self.new.write_bytes(self.candidate)
        self.plan_path = self.root / "plan.json"
        self.eval_path = self.root / "eval.json"
        self.patcher = patch.object(imp, "ROOT", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def prepare(self):
        plan = imp.plan(SimpleNamespace(target="skills/sample-skill/SKILL.md",
                     candidate=str(self.new), output=str(self.plan_path)))
        ev = {"baseline_sha256": imp.digest(self.original),
              "candidate_sha256": imp.digest(self.candidate),
              "case_set_sha256": "a" * 64,
              "baseline_passed": 1, "candidate_passed": 2,
              "regressions": 0, "failed_cases": 0}
        self.eval_path.write_text(json.dumps(ev))
        return plan

    def options(self, plan, **overrides):
        fields = {"plan": str(self.plan_path), "candidate": str(self.new),
                  "eval": str(self.eval_path), "approve": True,
                  "expect_plan_sha256": plan["plan_sha256"]}
        fields.update(overrides)
        return SimpleNamespace(**fields)

    def test_plan_apply_rollback(self):
        plan = self.prepare()
        receipt = imp.apply(self.options(plan))
        self.assertEqual(self.target.read_bytes(), self.candidate)
        result = imp.rollback(SimpleNamespace(target="skills/sample-skill/SKILL.md",
                backup=str(self.root / receipt["backup"]), approve=True,
                expect_current_sha256=receipt["after_sha256"]))
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_missing_approval_fails(self):
        plan = self.prepare()
        with self.assertRaisesRegex(ValueError, "approve"):
            imp.apply(self.options(plan, approve=False))
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_failed_evaluation_fails(self):
        plan = self.prepare()
        ev = json.loads(self.eval_path.read_text())
        ev["regressions"] = 1
        self.eval_path.write_text(json.dumps(ev))
        with self.assertRaisesRegex(ValueError, "regression"):
            imp.apply(self.options(plan))
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_stale_target_fails(self):
        plan = self.prepare()
        self.target.write_bytes(content("later edit"))
        with self.assertRaisesRegex(ValueError, "Stale"):
            imp.apply(self.options(plan))

    def test_plan_tamper_fails(self):
        plan = self.prepare()
        altered = json.loads(self.plan_path.read_text())
        altered["diff"] += "\nmalicious"
        self.plan_path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "checksum"):
            imp.apply(self.options(plan))

    def test_stale_candidate_fails(self):
        plan = self.prepare()
        self.new.write_bytes(content("subsequent"))
        with self.assertRaisesRegex(ValueError, "Stale"):
            imp.apply(self.options(plan))

    def test_imported_target_rejected(self):
        (self.target.parent / "UPSTREAM.md").write_text("imported")
        with self.assertRaisesRegex(ValueError, "imported"):
            imp.target_path("skills/sample-skill/SKILL.md")

    def test_symlink_target_rejected(self):
        self.target.unlink()
        self.target.symlink_to(self.new)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            imp.target_path("skills/sample-skill/SKILL.md")

    def test_rollback_rejects_later_edits(self):
        plan = self.prepare()
        receipt = imp.apply(self.options(plan))
        self.target.write_bytes(content("later edit"))
        with self.assertRaisesRegex(ValueError, "changed"):
            imp.rollback(SimpleNamespace(target="skills/sample-skill/SKILL.md",
                backup=str(self.root / receipt["backup"]), approve=True,
                expect_current_sha256=receipt["after_sha256"]))
        self.assertEqual(self.target.read_bytes(), content("later edit"))

    def test_duplicate_apply_fails(self):
        plan = self.prepare()
        imp.apply(self.options(plan))
        with self.assertRaisesRegex(ValueError, "Stale"):
            imp.apply(self.options(plan))

if __name__ == "__main__":
    unittest.main()
