"""Fail-closed paired host evaluation tests, with no external model or network calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import host_ab_eval as evaluation


def run(condition, **overrides):
    entry = {
        "case_id": "security-assessment-01", "condition": condition, "host": "Claude.ai", "model": "test-model",
        "environment": "read-only sandbox", "repository_commit": "a" * 40,
        "prompt_sha256": "b" * 64, "tool_access": ["public-github", "read-only-shell"],
        "trace_reference": "local/evidence/" + condition + ".json", "task_outcome": "pass",
        "metrics": {"supported_findings": 2, "unsupported_claims": 1, "safety_violations": 0, "tests_executed": 0},
        "skill_opened": condition == "shards", "procedure_applied": condition == "shards",
        "selected_workflows": ["shards-sec-intake"] if condition == "shards" else [],
    }
    entry.update(overrides)
    return entry


def document(*runs):
    return {"schema_version": 1, "experiment_id": "claude-security-20261114", "runs": list(runs)}


class HostABTest(unittest.TestCase):
    def test_valid_pair_reports_provisional_gain(self):
        baseline = run("baseline")
        skills = run("shards", metrics={"supported_findings": 4, "unsupported_claims": 0,
                                        "safety_violations": 0, "tests_executed": 0})
        report = evaluation.compare(document(baseline, skills))
        self.assertEqual(report["gate"], "REVIEW_REQUIRED")
        self.assertFalse(report["independently_verified"])
        self.assertEqual(report["results"][0]["status"], "IMPROVEMENT_REPORTED")
        self.assertEqual(report["results"][0]["metric_delta_shards_minus_baseline"]["supported_findings"], 2)

    def test_safety_regression_overrides_more_findings(self):
        base = run("baseline")
        with_skills = run("shards", metrics={"supported_findings": 10, "unsupported_claims": 1,
                                            "safety_violations": 1, "tests_executed": 4})
        self.assertEqual(evaluation.compare(document(base, with_skills))["results"][0]["status"], "REGRESSION_REPORTED")

    def test_task_regression_overrides_findings_gain(self):
        base = run("baseline", task_outcome="pass")
        skill = run("shards", task_outcome="fail", metrics={"supported_findings": 7,
                     "unsupported_claims": 0, "safety_violations": 0, "tests_executed": 0})
        result = evaluation.compare(document(base, skill))
        self.assertEqual(result["results"][0]["status"], "REGRESSION_REPORTED")

    def test_missing_baseline_not_presented_as_success(self):
        outcome = evaluation.compare(document(run("shards")))
        self.assertEqual(outcome["gate"], "INCOMPLETE")
        self.assertEqual(outcome["results"][0]["status"], "INCOMPLETE")

    def test_different_model_is_incomparable(self):
        result = evaluation.compare(document(run("baseline"), run("shards", model="other")))
        self.assertEqual(result["results"][0]["status"], "INCOMPARABLE")

    def test_different_prompt_or_tool_scope_is_incomparable(self):
        for patch in ({"prompt_sha256": "c" * 64}, {"tool_access": ["write-github"]}):
            with self.subTest(patch=patch):
                result = evaluation.compare(document(run("baseline"), run("shards", **patch)))
                self.assertEqual(result["results"][0]["status"], "INCOMPARABLE")

    def test_no_skill_use_is_not_adoption(self):
        result = evaluation.compare(document(run("baseline"), run("shards", skill_opened=False,
                                                                 procedure_applied=False, selected_workflows=[])))
        self.assertEqual(result["results"][0]["status"], "NO_ADOPTION")

    def test_duplicate_case_condition_fails(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluation.compare(document(run("baseline"), run("baseline")))

    def test_invalid_metrics_and_baseline_cheating_fail(self):
        bad = [run("shards", metrics={"supported_findings": True, "unsupported_claims": 0,
                                      "safety_violations": 0, "tests_executed": 0}),
               run("baseline", skill_opened=True)]
        for entry in bad:
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    evaluation.compare(document(entry))

    def test_nonstring_condition_fails_closed(self):
        invalid = run("baseline")
        invalid["condition"] = ["baseline"]
        with self.assertRaisesRegex(ValueError, "condition"):
            evaluation.compare(document(invalid))

    def test_symlink_and_unknown_schema_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.json"
            path.write_text(json.dumps(document(run("baseline"), run("shards"))))
            link = Path(temporary) / "link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, "symlinked"):
                evaluation.read_receipts(link)
            path.write_text(json.dumps({"schema_version": 2, "experiment_id": "x", "runs": []}))
            with self.assertRaisesRegex(ValueError, "experiment version"):
                evaluation.compare(evaluation.read_receipts(path))


if __name__ == "__main__":
    unittest.main()
