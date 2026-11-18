"""Structural and fixture tests only; do not claim real agent-host compliance."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "shards-a2a-conditional-offer",
    "shards-a2a-leakage-audit",
    "shards-a2a-closed-loop-circuit",
    "shards-a2a-self-preservation",
    "shards-a2a-clear-demonstration",
)

class A2AFiveWorkflowTests(unittest.TestCase):
    def _read(self, name):
        p = ROOT / "skills" / name / "SKILL.md"
        self.assertTrue(p.is_file(), name)
        return p.read_text(encoding="utf-8")

    def test_all_five_portable_draft_skills_exist(self):
        for name in NAMES:
            with self.subTest(name=name):
                body = self._read(name)
                self.assertTrue(body.startswith("---\n"))
                self.assertIn(f"name: {name}\n", body)
                self.assertIn("status: draft\n", body)
                self.assertIn("license: MIT\n", body)
                for h in ("## Trigger", "## Required inputs", "## Workflow", "## Execution", "## Output contract", "## Verification", "## Failure handling", "## Trust boundary"):
                    self.assertIn(h, body)
                self.assertIn("shards-a2a-five-workflows.json", body)
                self.assertNotIn("APPROVED_BY_THIS_SKILL", body)

    def test_each_workflow_has_boundaries_and_no_autonomous_external_action(self):
        for name in NAMES:
            with self.subTest(name=name):
                s = self._read(name).lower()
                self.assertTrue("authoris" in s or "authoriz" in s)
                self.assertTrue("evidence" in s)
                self.assertTrue("not" in s)
                self.assertTrue("host" in s)

    def test_frozen_cases_cover_all_skills_with_positive_and_negative_inputs(self):
        data = json.loads((ROOT / "evals/shards-a2a-five-workflows.json").read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["status"], "SCENARIOS_ONLY_NOT_EXECUTED")
        cases = data["cases"]
        self.assertEqual(len(cases), 15)
        self.assertEqual({case["skill"] for case in cases}, set(NAMES))
        self.assertEqual(len({case["id"] for case in cases}), 15)
        for name in NAMES:
            self.assertEqual(sum(c["skill"] == name for c in cases), 3)
        for case in cases:
            self.assertTrue(case["input"].strip())
            self.assertTrue(case["expected_decision"].strip())
            self.assertIsInstance(case["forbidden_claims"], list)

    def test_catalogue_contains_all_five_draft_descriptors(self):
        catalogue = json.loads((ROOT / "catalogue/catalogue.json").read_text(encoding="utf-8"))
        records = {x["name"]: x for x in catalogue["skills"]}
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(records[name]["path"], "skills/" + name)
                self.assertEqual(records[name]["status"], "draft")
                self.assertEqual(records[name]["category"], "agents")
        self.assertEqual(catalogue["skill_count"], len(catalogue["skills"]))
        self.assertEqual(len(catalogue["skill_paths"]), len(catalogue["skills"]))

    def test_receipts_do_not_self_grant_permission(self):
        records = {name: self._read(name) for name in NAMES}
        self.assertIn("EXECUTION_AUTHORIZATION: NOT_GRANTED", records["shards-a2a-conditional-offer"])
        self.assertIn("REUSE_BY_REF", records["shards-a2a-self-preservation"])
        self.assertIn("HOLD_UNVERIFIED", records["shards-a2a-leakage-audit"])
        self.assertIn("MAX_CORRECTION_ROUNDS", records["shards-a2a-closed-loop-circuit"])
        self.assertIn("NEGATIVE_CASE", records["shards-a2a-clear-demonstration"])

if __name__ == "__main__":
    unittest.main()
