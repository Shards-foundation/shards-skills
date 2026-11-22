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
            "open_findings": 0, "step_ids": ["implement"],
            "evidence_ids": ["review-1"],
        }]
        record["evidence"].append({
            "id": "review-1", "kind": "formal-review", "verdict": "APPROVED",
            "step_ids": ["implement"], "ref": "local:fictional-review",
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

    def test_reviewer_must_be_independent_of_reviewed_step_owner(self):
        record = self.approved()
        record["steps"][0]["owner"] = " Reviewer-Agent "
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_review_must_cover_every_step_but_can_be_split(self):
        record = self.approved()
        record["steps"].append(dict(record["steps"][0], id="docs", owner="reviewer-agent", evidence_ids=["docs-test"]))
        record["evidence"][0]["step_ids"] = ["implement"]
        record["evidence"].append(dict(record["evidence"][0], id="docs-test", step_ids=["docs"],
                                       observed_by="reviewer-agent", ref="local:docs-test"))
        self.assertEqual(validator.validate(record)["decision"], "HOLD")
        record["reviews"].append(dict(record["reviews"][0], reviewer="docs-reviewer",
                                      step_ids=["docs"], evidence_ids=["review-docs"]))
        record["evidence"].append(dict(record["evidence"][1], id="review-docs",
                                       step_ids=["docs"], observed_by="docs-reviewer",
                                       ref="local:fictional-docs-review"))
        self.assertEqual(validator.validate(record)["decision"], "EVIDENCE_READY")

    def test_review_requires_applicable_formal_artifact(self):
        for change in ({"kind": "self-reported-test"}, {"kind": "execution"},
                       {"kind": "bot-comment"}, {"kind": "review"},
                       {"observed_by": "builder-agent"}, {"verdict": "CHANGES_REQUESTED"},
                       {"revision": "b" * 40}):
            with self.subTest(change=change):
                record = self.approved()
                record["evidence"][1].update(change)
                self.assertEqual(validator.validate(record)["decision"], "HOLD")
        record = self.approved()
        record["reviews"][0]["evidence_ids"] = ["test-1"]
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_same_test_receipt_cannot_be_relabelled_as_a_formal_review(self):
        record = self.approved()
        record["evidence"][1]["ref"] = record["evidence"][0]["ref"]
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_formal_artifact_alone_cannot_verify_work_or_tests(self):
        record = self.approved()
        record["evidence"] = record["evidence"][1:]
        record["steps"][0]["evidence_ids"] = ["review-1"]
        record["checks"][0]["evidence_ids"] = ["review-1"]
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_work_and_check_evidence_matches_reported_scope_and_actor(self):
        for change in ({"kind": "comment"}, {"observed_by": "other-agent"},
                       {"result": "FAIL"}, {"branch": "release"}, {"repository": "foreign/repo"},
                       {"ref": "https://github.com/elsewhere/repo/actions/runs/123"}):
            with self.subTest(change=change):
                record = self.approved()
                record["evidence"][0].update(change)
                self.assertEqual(validator.validate(record)["decision"], "HOLD")
        record = self.approved()
        record["checks"][0]["observed_by"] = "ci-observer"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")
        record["evidence"][0].update(observed_by="ci-observer", subject_actor="builder-agent")
        self.assertEqual(validator.validate(record)["decision"], "EVIDENCE_READY")

    def test_unscoped_work_receipt_cannot_widen_to_a_second_step_or_check(self):
        for field, scope_field, identifier in (("steps", "step_ids", "implement"),
                                               ("checks", "check_ids", "tests")):
            with self.subTest(field=field):
                record = self.approved()
                record[field].append(dict(record[field][0], id="extra"))
                if field == "steps":
                    record["reviews"][0]["step_ids"].append("extra")
                    record["evidence"][1]["step_ids"].append("extra")
                self.assertEqual(validator.validate(record)["decision"], "HOLD")
                record["evidence"][0][scope_field] = [identifier]
                self.assertEqual(validator.validate(record)["decision"], "HOLD")
                record["evidence"][0][scope_field].append("extra")
                self.assertEqual(validator.validate(record)["decision"], "EVIDENCE_READY")

    def test_artifact_identity_and_github_review_resource(self):
        record = self.approved()
        record["evidence"][1]["ref"] = " " + record["evidence"][0]["ref"] + " "
        with self.assertRaises(ValueError):
            validator.validate(record)
        for ref, expected in (
            ("https://github.com/Example-Org/Example-Repository/pull/12#pullrequestreview-19", "EVIDENCE_READY"),
            ("https://api.github.com/repos/example-org/example-repository/pulls/12/reviews/19", "EVIDENCE_READY"),
            ("https://github.com/example-org/example-repository/pull/12#issuecomment-19", "HOLD"),
            ("https://github.com/example-org/example-repository/pull/12#discussion_r19", "HOLD"),
            ("https://github.com/example-org/foreign/pull/12#pullrequestreview-19", "HOLD"),
        ):
            with self.subTest(ref=ref):
                record = self.approved()
                record["evidence"][1]["ref"] = ref
                self.assertEqual(validator.validate(record)["decision"], expected)
        record = self.approved()
        record["evidence"][1]["repository"] = "foreign/repo"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")
        record = self.approved()
        record["scope"]["repository"] = "not an owner/repo"
        with self.assertRaises(ValueError):
            validator.validate(record)

    def test_one_github_review_event_cannot_back_two_claims_via_different_urls(self):
        record = self.approved()
        record["evidence"][0]["ref"] = "https://api.github.com/repos/Example-org/example-repository/pulls/12/reviews/19"
        record["evidence"][1]["ref"] = "https://github.com/example-org/example-repository/pull/12#pullrequestreview-19"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_case_alias_cannot_self_review(self):
        record = self.approved()
        record["steps"][0]["owner"] = "@Reviewer-Agent"
        record["reviews"][0]["reviewer"] = "reviewer-agent"
        record["evidence"][1]["observed_by"] = "reviewer-agent"
        record["evidence"][0]["observed_by"] = "@Reviewer-Agent"
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_artifact_and_review_scopes_must_match(self):
        record = self.approved()
        record["steps"].append(dict(record["steps"][0], id="docs"))
        record["reviews"][0]["step_ids"].append("docs")
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_legacy_review_without_scope_cannot_cover_steps(self):
        record = self.approved()
        del record["reviews"][0]["step_ids"]
        self.assertEqual(validator.validate(record)["decision"], "HOLD")

    def test_invalid_review_scope(self):
        for invalid in (None, [], [None], ["absent"], ["implement", "implement"]):
            with self.subTest(invalid=invalid):
                record = self.approved()
                record["reviews"][0]["step_ids"] = invalid
                with self.assertRaises(ValueError):
                    validator.validate(record)

    def test_failed_step_and_check_identified(self):
        record = self.approved()
        record["checks"][0]["result"] = "FAIL"
        record["steps"][0]["status"] = "FAILED"
        report = validator.validate(record)
        self.assertEqual(report["decision"], "FAIL")
        for name in ("tests", "implement"):
            self.assertTrue(any(name in reason for reason in report["reasons"]))

    def test_cli_returns_invalid_for_nested_malformed_data(self):
        cases = []
        for field in ("reviews", "steps", "checks", "evidence"):
            record = self.approved()
            record[field] = [None]
            cases.append(json.dumps(record))
        for depth in (70, 1500):
            cases.append(json.dumps(self.approved())[:-1] + ', "extra":'
                         + "[" * depth + "0" + "]" * depth + "}")
        valid = json.dumps(self.approved())
        cases.extend([valid.replace('"schema_version": 1', '"schema_version": 2, "schema_version": 1'),
                      valid[:-1] + ', "extra": NaN}'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            for index, payload in enumerate(cases):
                with self.subTest(index=index):
                    path.write_text(payload, encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(SCRIPT), "validate",
                                           "--input", str(path)], capture_output=True,
                                          text=True, timeout=15)
                    self.assertEqual(proc.returncode, 2)
                    self.assertNotIn("Traceback", proc.stderr)
                    result = json.loads(proc.stdout)
                    self.assertEqual(result["structural_status"], "INVALID")
                    self.assertEqual(result["decision"], "INVALID")

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
        with self.assertRaisesRegex(ValueError, "Credential-like"):
            validator.validate(record)
        for field in ("token", "refreshToken", "credentials"):
            with self.subTest(field=field):
                record = self.approved()
                record["evidence"][0][field] = "synthetic placeholder"
                with self.assertRaisesRegex(ValueError, "Sensitive field"):
                    validator.validate(record)
        for locator in ("https://fixture-user:fixture-pass@example.invalid/receipt",
                        "https://example.invalid/receipt?access_token=placeholder",
                        "https://example.invalid/receipt?client_secret=placeholder",
                        "https://example.invalid/receipt?password=placeholder"):
            with self.subTest(locator=locator):
                record = self.approved()
                record["evidence"][0]["ref"] = locator
                with self.assertRaisesRegex(ValueError, "Credential-like"):
                    validator.validate(record)
        record = self.approved()
        record["intent"]["goal"] = "Document procedures to rotate Bearer tokens"
        self.assertEqual(validator.validate(record)["decision"], "EVIDENCE_READY")

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
