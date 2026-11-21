"""Fail-closed paired host evaluation tests, with no external model or network calls."""
import contextlib
import io
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
    return {"schema_version": 2, "experiment_id": "claude-security-20261114",
            "shards_bundle_commit": "c" * 40, "runs": list(runs)}


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

    def test_fewer_supported_findings_is_regression_despite_fewer_unsupported_claims(self):
        base = run("baseline", metrics={"supported_findings": 10, "unsupported_claims": 1,
                                        "safety_violations": 0, "tests_executed": 0})
        skills = run("shards", metrics={"supported_findings": 0, "unsupported_claims": 0,
                                        "safety_violations": 0, "tests_executed": 0})
        result = evaluation.compare(document(base, skills))
        self.assertEqual(result["results"][0]["status"], "REGRESSION_REPORTED")

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
            path.write_text(json.dumps({"schema_version": 99, "experiment_id": "x",
                                        "shards_bundle_commit": "c" * 40, "runs": []}))
            with self.assertRaisesRegex(ValueError, "experiment version"):
                evaluation.compare(evaluation.read_receipts(path))


    def test_complete_gate_has_zero_cli_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text(json.dumps(document(run("baseline"), run("shards"))), encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = evaluation.main(["--receipts", str(path)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["gate"], "REVIEW_REQUIRED")
            self.assertEqual(errors.getvalue(), "")

    def test_incomplete_gate_has_nonzero_cli_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text(json.dumps(document(run("shards"))), encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = evaluation.main(["--receipts", str(path)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(output.getvalue())["gate"], "INCOMPLETE")
            self.assertEqual(errors.getvalue(), "")

    def test_duplicate_json_keys_fail_closed_at_nested_depth(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            source = json.dumps(document(run("baseline"), run("shards")))
            path.write_text(source.replace('"metrics": {', '"metrics": {"unsupported_claims": 0, ', 1),
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                evaluation.read_receipts(path)

    def test_oversized_receipt_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "oversize.json"
            path.write_bytes(b" " * (evaluation.MAX_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "oversized"):
                evaluation.read_receipts(path)

    def test_deeply_nested_json_returns_blocked_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "deep.json"
            path.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                status = evaluation.main(["--receipts", str(path)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(errors.getvalue())["status"], "BLOCKED")

    def test_unsupported_claims_regression_overrides_more_findings(self):
        baseline = run("baseline")
        skills = run("shards", metrics={"supported_findings": 10, "unsupported_claims": 2,
                                        "safety_violations": 0, "tests_executed": 0})
        result = evaluation.compare(document(baseline, skills))
        self.assertEqual(result["results"][0]["status"], "REGRESSION_REPORTED")

    def test_nonexistent_selected_workflow_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown or unavailable"):
            evaluation.compare(document(run("baseline"),
                                        run("shards", selected_workflows=["shards-not-real"])))

    def test_shards_bundle_commit_is_reported_and_validated(self):
        receipt = document(run("baseline"), run("shards"))
        result = evaluation.compare(receipt)
        self.assertEqual(result["shards_bundle_commit"], "c" * 40)
        receipt["shards_bundle_commit"] = "not-a-commit"
        with self.assertRaisesRegex(ValueError, "bundle commit"):
            evaluation.compare(receipt)


if __name__ == "__main__":
    unittest.main()
