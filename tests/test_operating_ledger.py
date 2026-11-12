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

    def test_verified_criterion_completes(self):
        self.start()
        ledger.append(self.root, "case-1", "evidence", {"criterion_id": "C1",
            "status": "tested", "reference": "ci/run/1", "revision": "abc123",
            "observation": "All configured checks succeeded"})
        self.assertTrue(ledger.summary(self.root, "case-1")["complete"])

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
