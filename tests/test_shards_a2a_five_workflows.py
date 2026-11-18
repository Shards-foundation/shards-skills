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

FIXTURES = ROOT / "evals/shards-a2a-five-workflows.json"


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

    def test_workflows_document_limits_on_external_effects(self):
        limits = {
            "shards-a2a-conditional-offer": "EXECUTION_AUTHORIZATION: NOT_GRANTED",
            "shards-a2a-leakage-audit": "Never auto-merge",
            "shards-a2a-closed-loop-circuit": "No implicit merge, publication, payment, signing or deployment",
            "shards-a2a-self-preservation": "Never fabricate a cached PASS or repeat side-effecting operations",
            "shards-a2a-clear-demonstration": "cannot establish actual production execution",
        }
        for name, phrase in limits.items():
            with self.subTest(name=name):
                self.assertIn(phrase, self._read(name))

    def test_frozen_cases_cover_all_skills_with_positive_and_negative_inputs(self):
        data = json.loads(FIXTURES.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["status"], "SCENARIOS_ONLY_NOT_EXECUTED")
        cases = data["cases"]
        self.assertEqual({case["skill"] for case in cases}, set(NAMES))
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for name in NAMES:
            skill_cases = [case for case in cases if case["skill"] == name]
            expected_count = 6 if name == "shards-a2a-leakage-audit" else 3
            self.assertEqual(len(skill_cases), expected_count)
            self.assertTrue(any(case["forbidden_claims"] for case in skill_cases))
        for case in cases:
            self.assertTrue(case["input"].strip())
            self.assertIsInstance(case["forbidden_claims"], list)

    def test_fixture_expectations_fit_their_output_contract_field(self):
        cases = json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                contract = self._read(case["skill"]).split("## Output contract\n", 1)[1]
                record = contract.split("```text\n", 1)[1].split("```", 1)[0]
                decision_field = r"^DECISION: ([A-Z_|]+)$"
                if case["skill"] == "shards-a2a-self-preservation":
                    decision_field = r"^CHECK_DECISIONS: .*?action: ([A-Z_|]+),"
                elif case["skill"] == "shards-a2a-clear-demonstration":
                    decision_field = r"^VERDICT: ([A-Z_|]+)$"
                match = re.search(decision_field, record, re.MULTILINE)
                self.assertIsNotNone(match, "missing decision field in output contract")
                self.assertIn(case["expected_decision"], match[1].split("|"))
                if case["skill"] == "shards-a2a-closed-loop-circuit":
                    state = re.search(r"^STATE: ([A-Z_|]+)$", record, re.MULTILINE)
                    self.assertIsNotNone(state)
                    self.assertIn(case["expected_state"], state[1].split("|"))

    def test_leakage_verification_table_matches_frozen_scenarios(self):
        name = "shards-a2a-leakage-audit"
        cases = json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]
        expected = {(c["scenario"], c["expected_decision"]) for c in cases if c["skill"] == name}
        self.assertIn(("false_actor_capability", "FINDING"), expected)
        self.assertIn(("unverified_permission", "HOLD_UNVERIFIED"), expected)
        verification = self._read(name).split("## Verification\n", 1)[1].split("\n## ", 1)[0]
        rows = re.findall(r"^\| `([a-z_]+)` \| `([A-Z_]+)` \|", verification, re.MULTILINE)
        self.assertCountEqual(rows, expected)

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
