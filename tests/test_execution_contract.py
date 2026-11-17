"""Offline tests for Shards execution-contract structural gates."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_execution_contract.py"
EXAMPLE = ROOT / "plugins/shards-core/skills/shards-execution-contract/references/contract-example.json"
spec = importlib.util.spec_from_file_location("shards_execution_contract", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ContractValidationTests(unittest.TestCase):
    def setUp(self):
        self.example = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def approved(self):
        record = copy.deepcopy(self.example)
        record["reviews"] = [{
            "reviewer": "reviewer-agent",
            "revision": record["scope"]["head_sha"],
            "verdict": "APPROVED",
            "open_findings": 0,
            "evidence_ids": ["review-1"],
        }]
        record["evidence"].append({
            "id": "review-1", "kind": "review", "ref": "local:fictional-review",
            "revision": record["scope"]["head_sha"], "observed_by": "reviewer-agent",
        })
        return record

    def test_example_holds_before_review(self):
        self.assertEqual(validator.validate(self.example)["decision"], "HOLD")

    def test_full_claim_is_evidence_ready_but_never_authorized(self):
        result = validator.validate(self.approved())
        self.assertEqual(result["decision"], "EVIDENCE_READY")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["approval_verified"])
        self.assertFalse(result["independent_review_verified"])

    def test_material_ambiguity_blocks(self):
        record = self.approved()
        record["intent"]["ambiguities"].append({
            "description": "Which production tenant?", "material": True, "resolved": False,
        })
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_stale_revision_blocks(self):
        record = self.approved()
        record["scope"]["head_sha"] = "b" * 40
        result = validator.validate(record)
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(any("current head SHA" in s for s in result["reasons"]))

    def test_self_review_is_not_independent(self):
        record = self.approved()
        record["reviews"][0]["reviewer"] = "builder-agent"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_open_findings_block(self):
        record = self.approved()
        record["reviews"][0]["open_findings"] = 1
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_external_effects_require_separate_host_authorization(self):
        record = self.approved()
        record["constraints"]["allow_merge"] = True
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_executed_external_write_beyond_scope_fails(self):
        record = self.approved()
        record["steps"][0]["effect"] = "external-write"
        self.assertEqual(validator.validate(record)["decision"], "FAIL")

    def test_unknown_effect_class_rejected(self):
        record = self.approved()
        record["steps"][0]["effect"] = "shell-anything"
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_failed_check_fails(self):
        record = self.approved()
        record["checks"][0]["result"] = "FAIL"
        self.assertEqual(validator.validate(record)["decision"], "FAIL")

    def test_unverified_step_holds(self):
        record = self.approved()
        record["steps"][0]["status"] = "EXECUTED"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_pass_without_evidence_is_invalid(self):
        record = self.approved()
        record["checks"][0]["evidence_ids"] = []
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_unknown_evidence_reference_is_invalid(self):
        record = self.approved()
        record["checks"][0]["evidence_ids"] = ["missing"]
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_credential_content_is_invalid(self):
        record = self.approved()
        record["intent"]["goal"] = "token " + "ghp_" + "a" * 25
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_bad_schema_and_bool_fail_closed(self):
        for key, value in (("schema_version", 2), ("schema_version", True)):
            record = self.approved()
            record[key] = value
            with self.assertRaises(ValueError):
                validator.validate(record)
        record = self.approved()
        record["constraints"]["allow_paid"] = "false"
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_cli_holds_on_example_and_never_executes(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "validate", "--input", str(EXAMPLE)],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["execution_performed"])

    def test_cli_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text("{invalid", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--input", str(path)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(json.loads(proc.stdout)["structural_status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
