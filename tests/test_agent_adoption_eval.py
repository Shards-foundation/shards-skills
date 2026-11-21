"""Regression coverage for the skill adoption evidence boundary."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_adoption_eval as evaluator


class AgentAdoptionEvalTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            {"skill": "tdd", "should_trigger": True, "prompt": "Fix a regression with tests"},
            {"skill": "broker", "should_trigger": False, "prompt": "Do not place orders"},
        ]
        self.entries = [
            {"name": "tdd", "description": "Fix regression tests", "category": "engineering", "status": "draft", "execution": "not-dispatchable"},
            {"name": "broker", "description": "Place orders", "category": "finance", "status": "review", "execution": "not-dispatchable"},
        ]

    def test_retrieval_separates_agent_use_from_ranking(self):
        report = evaluator.retrieval_report(self.cases, self.entries)
        self.assertEqual(report["evaluation"], "metadata_retrieval_only")
        self.assertEqual(report["positive_count"], 1)
        self.assertEqual(report["recall_at_3"], 1.0)
        self.assertFalse(report["negative_trigger_assessed"])
        self.assertTrue(all(not r["agent_activation_verified"] for r in report["results"]))

    def test_real_catalogue_trigger_recall_regression(self):
        cases = evaluator.load_cases(ROOT / "evals" / "trigger-cases.json")
        entries = evaluator.catalogue_entries() + evaluator.curated_entries()
        report = evaluator.retrieval_report(cases, entries)
        self.assertEqual(report["positive_count"], 7)
        self.assertGreaterEqual(report["recall_at_3"], 6 / 7)
        self.assertEqual(report["recall_at_5"], 1.0)
        self.assertFalse(report["negative_trigger_assessed"])

    def test_missing_host_trace_does_not_count_as_use(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1, "host": "Claude Code",
                    "repository_commit": "a" * 40, "runs": []})
        self.assertEqual([r["result"] for r in report["results"]], ["not_run", "not_run"])
        self.assertFalse(report["independently_verified"])

    def test_host_reports_use_and_abstention_separately(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1, "host": "Codex",
            "repository_commit": "a" * 40, "runs": [
                {"case_id": "1", "selected_skill": "tdd", "skill_opened": True,
                 "procedure_applied": True, "trace_reference": "local:run-123", "task_outcome": "pass"},
                {"case_id": "2", "selected_skill": None, "skill_opened": False,
                 "procedure_applied": False, "trace_reference": "local:run-124", "task_outcome": "pass"}]})
        self.assertEqual([r["result"] for r in report["results"]],
                         ["reported_use", "reported_appropriate_abstention"])

    def test_no_trace_cannot_demonstrate_use_and_false_trigger_is_flagged(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1, "host": "Codex",
            "repository_commit": "b" * 40, "runs": [
                {"case_id": "1", "selected_skill": "tdd", "skill_opened": True,
                 "procedure_applied": True, "trace_reference": "", "task_outcome": "pass"},
                {"case_id": "2", "selected_skill": "broker", "skill_opened": True,
                 "procedure_applied": True, "trace_reference": "trace", "task_outcome": "pass"}]})
        self.assertEqual([r["result"] for r in report["results"]],
                         ["not_demonstrated", "reported_false_trigger"])

    def test_negative_selection_without_application_is_false_trigger(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1, "host": "Codex",
            "repository_commit": "d" * 40, "runs": [
                {"case_id": "2", "selected_skill": "broker", "skill_opened": True,
                 "procedure_applied": False, "trace_reference": "host:case-2", "task_outcome": "pass"}]})
        self.assertEqual(report["results"][1]["result"], "reported_false_trigger")

    def test_unknown_opened_skill_is_unverified_not_a_false_trigger(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1,
            "host": "Codex", "repository_commit": "e" * 40, "runs": [
                {"case_id": "2", "selected_skill": None, "skill_opened": True,
                 "procedure_applied": False, "trace_reference": "host:ambiguous",
                 "task_outcome": "pass"}]})
        self.assertEqual(report["results"][1]["result"], "not_demonstrated")

    def test_negative_abstention_requires_host_trace(self):
        report = evaluator.host_report(self.cases, {"schema_version": 1, "host": "Codex",
            "repository_commit": "c" * 40, "runs": [
                {"case_id": "2", "selected_skill": None, "skill_opened": False,
                 "procedure_applied": False, "trace_reference": "", "task_outcome": "pass"}]})
        self.assertEqual(report["results"][1]["result"], "not_demonstrated")

    def test_reject_forged_or_malformed_receipts(self):
        baseline = {"schema_version": 1, "host": "Codex", "repository_commit": "a" * 40,
                    "runs": []}
        for changes in ({"repository_commit": "latest"}, {"host": " "},
                        {"runs": [{"case_id": "1"}]},
                        {"runs": [{"case_id": "99"}]},
                        {"runs": [{"case_id": "1"}, {"case_id": "1"}]}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    evaluator.host_report(self.cases, {**baseline, **changes})

    def test_bad_cases_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "cases.json"
            for payload in ([], {"schema_version": 1, "cases": []},
                            {"schema_version": 1, "cases": [{"skill": "x", "prompt": "y",
                                                                "should_trigger": "false"}]}):
                target.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    evaluator.load_cases(target)


if __name__ == "__main__":
    unittest.main()
