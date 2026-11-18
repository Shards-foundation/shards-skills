"""Tests for operating contract persistence, integrity and progress checks."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("operating_ledger", ROOT / "scripts" / "operating_ledger.py")
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = {"outcome": "Ship one verifiable fix", "scope": "One repository",
                         "authority": "Local repository files only",
                         "criteria": [{"id": "C1", "acceptance": "Tests pass on the target revision"}]}

    def start(self):
        return ledger.init(self.root, "case-1", self.contract)

    def test_initial_contract_is_incomplete(self):
        self.start()
        summary = ledger.summary(self.root, "case-1")
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["criteria"]["C1"]["status"], "unverified")

    def test_legacy_reference_alone_is_unverified(self):
        self.start()
        ledger.append(self.root, "case-1", "evidence", {"criterion_id": "C1",
            "status": "tested", "reference": "ci/run/1", "revision": "abc123",
            "observation": "All configured checks succeeded"})
        self.assertFalse(ledger.summary(self.root, "case-1")["complete"])

    def test_criterion_requires_matching_verified_test_and_independent_approval(self):
        revision = "a" * 40
        criterion = self.contract["criteria"][0]
        criterion.update(target_revision=revision, resource="org/repo",
                         subject_actor="builder", required_evidence=["tested", "reviewed"])
        self.start()
        current_test = {"criterion_id": "C1", "status": "tested", "reference": "ci/1",
                        "revision": revision, "observation": "suite succeeded",
                        "observed_by": "ci", "subject_actor": "builder", "resource": "org/repo"}
        approval = dict(current_test, status="reviewed", observed_by="reviewer",
                        reference="formal-review/2", observation="approved", decision="APPROVED")
        expected_records = [current_test, approval]

        def verifier(task, spec, record):
            return task == "case-1" and spec == criterion and record in expected_records

        def complete():
            return ledger.summary(self.root, "case-1", verify_observation=verifier)["complete"]

        for mismatch in [dict(current_test, revision="b" * 40), dict(approval, observed_by="builder"),
                         dict(approval, decision="COMMENTED"), dict(approval, resource="org/other")]:
            ledger.append(self.root, "case-1", "evidence", mismatch)
            self.assertFalse(complete())
        ledger.append(self.root, "case-1", "evidence", approval)
        self.assertFalse(complete(), "stale passing test cannot satisfy current test requirement")
        ledger.append(self.root, "case-1", "evidence", current_test)
        self.assertFalse(ledger.summary(self.root, "case-1")["complete"], "local claims alone")
        self.assertTrue(complete())
        blocker = ledger.append(self.root, "case-1", "evidence", dict(current_test, status="blocked", evidence_type="tested", reference="failed/1"))
        ledger.append(self.root, "case-1", "evidence", current_test)
        report = ledger.summary(self.root, "case-1", verify_observation=verifier)
        self.assertFalse(report["complete"])
        self.assertEqual(len(report["criteria"]["C1"]["blockers"]), 1)
        resolution = dict(current_test, resolves=[blocker["event_sha256"]])
        ledger.append(self.root, "case-1", "evidence", resolution)
        self.assertFalse(complete(), "self-reported resolution alone")
        expected_records.append(resolution)
        self.assertTrue(complete(), "host-confirmed resolution for this exact blocker")

    def test_test_receipt_cannot_restore_a_dismissed_approval(self):
        self.contract["criteria"][0].update(target_revision="a" * 40, resource="org/repo",
            subject_actor="builder", required_evidence=["tested", "reviewed"])
        self.start()
        evidence = {"criterion_id": "C1", "status": "tested", "revision": "a" * 40,
                    "reference": "test/1", "observation": "passed", "observed_by": "ci",
                    "subject_actor": "builder", "resource": "org/repo"}
        approval = dict(evidence, status="reviewed", decision="APPROVED", observed_by="reviewer",
                        reference="review/5", observation="approved")
        def record(payload):
            return ledger.append(self.root, "case-1", "evidence", payload)["event_sha256"]
        def complete():
            return ledger.summary(self.root, "case-1", verify_observation=lambda *args: True)["complete"]
        record(evidence)
        record(approval)
        self.assertTrue(complete())
        dismissed = record(dict(approval, decision="DISMISSED", observation="approval withdrawn"))
        record(dict(evidence, reference="test/2", resolves=[dismissed]))
        self.assertFalse(complete(), "test cannot clear a review blocker")
        record(dict(approval, reference="review/6", resolves=[dismissed]))
        self.assertTrue(complete())

    def test_current_evidence_cannot_substitute_for_another_requirement(self):
        self.contract["criteria"][0].update(target_revision="a" * 40, resource="org/repo",
            subject_actor="builder", required_evidence=["tested", "production-verified"])
        self.start()
        current = {"criterion_id": "C1", "status": "tested", "revision": "a" * 40,
                   "reference": "receipt/7", "observation": "tests passed",
                   "observed_by": "ci", "subject_actor": "builder", "resource": "org/repo"}
        ledger.append(self.root, "case-1", "evidence", current)
        for mismatch in [dict(revision="b" * 40), dict(resource="wrong"), dict(subject_actor="other")]:
            claim = dict(current, status="production-verified")
            ledger.append(self.root, "case-1", "evidence", dict(claim, **mismatch))
        summary = ledger.summary(self.root, "case-1", verify_observation=lambda *args: True)
        self.assertEqual(summary["criteria"]["C1"]["missing_verified_evidence"], ["production-verified"])
        self.assertFalse(summary["complete"])

    def test_verifier_cannot_waive_self_review(self):
        self.contract["criteria"][0].update(target_revision="a" * 40, resource="org/repo",
            subject_actor="owner", required_evidence=["reviewed"])
        self.start()
        ledger.append(self.root, "case-1", "evidence", {"criterion_id": "C1", "status": "reviewed",
            "reference": "review/1", "revision": "a" * 40, "observation": "approved",
            "observed_by": "owner", "subject_actor": "owner", "resource": "org/repo",
            "decision": "APPROVED"})
        report = ledger.summary(self.root, "case-1", verify_observation=lambda *args: True)
        self.assertFalse(report["complete"])

    def test_implementation_alone_does_not_complete(self):
        self.start()
        ledger.append(self.root, "case-1", "evidence", {"criterion_id": "C1",
            "status": "implemented", "reference": "git/abc123", "revision": "abc123",
            "observation": "File changed"})
        self.assertFalse(ledger.summary(self.root, "case-1")["complete"])

    def test_immutable_original_criteria(self):
        self.start()
        with self.assertRaisesRegex(ValueError, "rewrite"):
            ledger.append(self.root, "case-1", "amendment", {"reason": "Changed outcome",
                "authority": "Approved amendment",
                "criteria": [{"id": "C1", "acceptance": "Easier task"}]})
        self.assertEqual(ledger.summary(self.root, "case-1")["event_count"], 1)

    def test_append_new_criterion_requires_evidence(self):
        self.start()
        ledger.append(self.root, "case-1", "amendment", {"reason": "Explicit new scope",
            "authority": "operator approved",
            "criteria": [{"id": "C2", "acceptance": "Second check passes"}]})
        self.assertIn("C2", ledger.summary(self.root, "case-1")["criteria"])

    def test_tampered_chain_rejected(self):
        self.start()
        file = self.root / "case-1.jsonl"
        data = file.read_text().replace("Ship one verifiable fix", "Ship fake success")
        file.write_text(data)
        with self.assertRaisesRegex(ValueError, "chain invalid"):
            ledger.summary(self.root, "case-1")

    def test_repeat_attempt_warning(self):
        self.start()
        payload = {"criterion_id": "C1", "action": "rerun same failed command",
                   "result": "same error", "reference": "log/ref1"}
        for _ in range(3):
            ledger.append(self.root, "case-1", "attempt", payload)
        self.assertEqual(ledger.summary(self.root, "case-1")["repetition_warnings"][0]["count"], 3)

    def test_duplicate_task_rejected(self):
        self.start()
        with self.assertRaises(FileExistsError):
            self.start()

    def test_unknown_criterion_rejected(self):
        self.start()
        with self.assertRaisesRegex(ValueError, "Unknown criterion"):
            ledger.append(self.root, "case-1", "evidence",
                {"criterion_id": "missing", "status": "tested",
                 "reference": "r", "revision": "c", "observation": "o"})

    def test_invalid_authority_rejected(self):
        self.contract["authority"] = ""
        with self.assertRaisesRegex(ValueError, "authority"):
            self.start()

if __name__ == "__main__":
    unittest.main()
