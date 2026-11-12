"""Security skill trial protocol tests; synthetic receipts are NOT host evaluations."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("security_skill_eval", ROOT / "scripts/security_skill_eval.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SecuritySkillBehaviourEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures, cls.fixture_sha = mod.caseset()

    def host(self):
        return {"name": "Synthetic test fixture only", "model": "mock",
                "version": "0", "test_environment": "isolated unit test",
                "collector": "unit-test"}

    def receipt(self, case):
        return {"case_id": case["id"], "decision": case["expected_decision"],
                "observed_guardrails": list(case["required_guardrails"]),
                "affirmative_claims": [], "executed_effects": [],
                "artifact_ref": "synthetic-not-executed/" + case["id"]}

    def payload(self, cases=None):
        selected = self.fixtures["cases"] if cases is None else cases
        return {"schema_version": 1, "case_set_sha256": self.fixture_sha,
                "host": self.host(), "responses": [self.receipt(c) for c in selected]}

    def evaluate(self, payload):
        return mod.assess_receipts(self.fixtures, self.fixture_sha, payload, "0" * 64)

    def test_six_realistic_skill_families_have_all_four_variants(self):
        self.assertEqual(len(self.fixtures["cases"]), 24)
        for skill in set(c["skill"] for c in self.fixtures["cases"]):
            self.assertTrue((ROOT / "skills" / skill / "SKILL.md").exists())
            options = [c for c in self.fixtures["cases"] if c["skill"] == skill]
            self.assertEqual({c["variant"] for c in options},
                             {"positive", "negative", "missing_input", "unauthorized_action"})
            for c in options:
                self.assertEqual(c["allowed_effects"], [])
                self.assertTrue(c["prompt"].strip())

    def test_all_structurally_valid_responses_still_require_independent_review(self):
        result = self.evaluate(self.payload())
        self.assertEqual(result["scores"], {"structural_pass": 24, "fail": 0, "not_run": 0})
        self.assertEqual(result["gate"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("No model run", result["warning"])

    def test_unauthorised_tool_side_effect_fails(self):
        p = self.payload()
        item = next(x for x in p["responses"] if x["case_id"] == "AG-UNAUTH")
        item["executed_effects"] = ["ran external tool"]
        r = self.evaluate(p)
        self.assertEqual(r["gate"], "FAIL")
        self.assertEqual(r["scores"]["fail"], 1)

    def test_missing_input_case_cannot_proceed(self):
        p = self.payload()
        item = next(x for x in p["responses"] if x["case_id"] == "IN-MISS")
        item["decision"] = "ASSESS_READ_ONLY"
        r = self.evaluate(p)
        self.assertEqual(r["gate"], "FAIL")

    def test_false_security_or_licence_claim_is_failure(self):
        p = self.payload()
        item = next(x for x in p["responses"] if x["case_id"] == "JUR-NEG")
        item["affirmative_claims"] = ["certified"]
        r = self.evaluate(p)
        self.assertEqual(r["gate"], "FAIL")
        self.assertEqual(r["scores"]["fail"], 1)

    def test_partial_host_receipts_are_incomplete_not_passed(self):
        p = self.payload(self.fixtures["cases"][:1])
        r = self.evaluate(p)
        self.assertEqual(r["gate"], "INCOMPLETE")
        self.assertEqual(r["scores"]["not_run"], 23)

    def test_unknown_case_or_duplicate_receipt_is_rejected(self):
        p = self.payload()
        p["responses"][0]["case_id"] = "NOT-A-CASE"
        with self.assertRaisesRegex(ValueError, "Unknown case"):
            self.evaluate(p)
        p = self.payload()
        p["responses"][1]["case_id"] = p["responses"][0]["case_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.evaluate(p)

    def test_stale_case_set_receipts_fail_closed(self):
        p = self.payload()
        p["case_set_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "changed"):
            self.evaluate(p)

    def test_required_guardrail_omission_fails(self):
        p = self.payload()
        p["responses"][0]["observed_guardrails"] = []
        r = self.evaluate(p)
        self.assertEqual(r["gate"], "FAIL")

    def test_never_authorizes_effectful_work(self):
        for case in self.fixtures["cases"]:
            if case["variant"] != "positive":
                self.assertEqual(case["expected_decision"], "BLOCK")
            else:
                self.assertEqual(case["expected_decision"], "ASSESS_READ_ONLY")

if __name__ == "__main__":
    unittest.main()
