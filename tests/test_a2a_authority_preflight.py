"""Offline contract checks; no GitHub credentials, network or LLM services required."""
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
SCRIPT = ROOT / "plugins/shards-core/skills/shards-a2a-authority-preflight/scripts/validate.py"
EXAMPLE = ROOT / "plugins/shards-core/skills/shards-a2a-authority-preflight/references/example-readonly.json"
spec = importlib.util.spec_from_file_location("shards_a2a_authority_validator", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class AuthorityPreflightTests(unittest.TestCase):
    def test_synthetic_readonly_is_only_structurally_complete(self):
        out = module.validate(sample())
        self.assertEqual(out["decision"], "CLAIMS_COMPLETE")
        self.assertFalse(out["authority_granted_by_validator"])
        self.assertFalse(out["external_permissions_verified_by_validator"])
        self.assertFalse(out["execution_performed"])

    def push_claim(self):
        record = sample()
        action = record["actions"][0]
        action.update(actor="integrator-agent", operation="git.push", policy="VERIFIED")
        record["evidence"].append({"id": "policy-1", "kind": "policy",
                                   "reference": "local:destination-policy", "revision": record["task"]["head_sha"],
                                   "observed_by": "human-operator"})
        action["evidence_ids"].append("policy-1")
        for item in record["evidence"]:
            item.update(subject_actor=action["actor"], operation=action["operation"],
                        repository=action["repository"], branch=action["branch"])
        return record

    def test_explicit_observation_by_another_actor(self):
        record = self.push_claim()
        capability = record["evidence"][1]
        self.assertNotEqual(capability["subject_actor"], capability["observed_by"])
        result = module.validate(record)
        self.assertEqual(result["decision"], "CLAIMS_COMPLETE")
        self.assertFalse(result["authority_granted_by_validator"])

    def test_case_variants_cannot_establish_independent_roles(self):
        record = self.push_claim()
        record["roles"]["reviewer"] = "EXECUTOR-AGENT"
        action = record["actions"][0]
        action.update(actor="EXECUTOR-AGENT", operation="pr.approve")
        for item in record["evidence"]:
            item.update(subject_actor=action["actor"], operation=action["operation"])
        with self.assertRaisesRegex(ValueError, "actor ID"):
            module.validate(record)

    def test_relabelling_one_reference_cannot_satisfy_separate_gates(self):
        record = self.push_claim()
        for item in record["evidence"]:
            item["reference"] = "local:observations"
        result = module.validate(record)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("AMBIGUOUS_EVIDENCE_REFERENCE", result["blockers"][0]["reasons"])
        self.assertEqual(result["operations"][0]["matched_evidence"], [])

    def test_copied_capability_reference_cannot_change_subject(self):
        record = self.push_claim()
        capability = record["evidence"][1]
        record["evidence"].append(dict(capability, id="other-subject", subject_actor="executor-agent"))
        self.assertEqual(module.validate(record)["decision"], "HOLD")

    def test_separate_observations_can_share_a_document_and_compatible_roles(self):
        record = self.push_claim()
        record["roles"]["coordinator"] = record["roles"]["integrator"]
        for item in record["evidence"]:
            item["reference"] = "local:observations#" + item["id"]
        result = module.validate(record)
        self.assertEqual(result["decision"], "CLAIMS_COMPLETE")
        self.assertFalse(result["authority_granted_by_validator"])

    def test_inapplicable_capabilities_hold(self):
        cases = {"subject_actor": ["executor-agent", "unknown-agent"], "operation": ["repo.read"],
                 "repository": ["other/project"], "branch": ["other"], "revision": ["b" * 40],
                 "observed_by": ["unknown-agent"]}
        for key, values in cases.items():
            for value in values:
                with self.subTest(field=key, value=value):
                    record = self.push_claim()
                    record["evidence"][1][key] = value
                    self.assertEqual(module.validate(record)["decision"], "HOLD")

    def test_evidence_must_support_each_action_gate(self):
        for index in (0, 1, 2):
            with self.subTest(kind=index):
                record = self.push_claim()
                record["evidence"][index].pop("subject_actor")
                self.assertEqual(module.validate(record)["decision"], "HOLD")
        record = self.push_claim()
        record["actions"][0]["evidence_ids"].remove("access-1")
        result = module.validate(record)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("CAPABILITY_EVIDENCE_MISSING_OR_STALE", result["blockers"][0]["reasons"])

    def test_malformed_nested_values_return_structured_invalid(self):
        cases = []
        for group, key, value in (("evidence", "kind", []), ("evidence", "subject_actor", {}),
                                  ("actions", "policy", {}), ("actions", "permission", []),
                                  ("actions", "access", {}), ("actions", "access_issue", []),
                                  ("actions", "evidence_ids", [["access-1"]])):
            record = self.push_claim()
            record[group][0][key] = value
            cases.append((key, json.dumps(record)))
        nested = "[" * 64 + "0" + "]" * 64
        cases.append(("nested extra field", json.dumps(sample())[:-1] + ',"extra":' + nested + '}'))
        cases.append(("decoder depth", "[" * 3000 + "0" + "]" * 3000))
        cases.append(("size limit", " " * 262144 + json.dumps(sample())))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            for label, contents in cases:
                with self.subTest(label=label):
                    path.write_text(contents, encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(SCRIPT), "--input", str(path)],
                                          capture_output=True, text=True, timeout=5)
                    self.assertEqual(proc.returncode, 2)
                    self.assertEqual(json.loads(proc.stderr)["decision"], "INVALID")
                    self.assertEqual(proc.stdout, "")

    def test_stdin_obeys_same_validation_and_limits_as_file_input(self):
        command = [sys.executable, str(SCRIPT), "validate", "--input", "-"]
        valid = json.dumps(sample()).encode("utf-8")
        duplicate = valid.replace(b'"schema_version": 1', b'"schema_version": 0, "schema_version": 1')
        for payload, expected in ((valid, 0), (b" " * 262144 + valid, 2),
                                  (duplicate, 2), (valid[:-1] + b',"extra":NaN}', 2),
                                  (b"\xff", 2), (b"[" * 40000 + b"]" * 40000, 2)):
            with self.subTest(expected=expected, size=len(payload)):
                proc = subprocess.run(command, input=payload, capture_output=True, timeout=5)
                self.assertEqual(proc.returncode, expected)
                result = json.loads(proc.stderr if expected == 2 else proc.stdout)
                self.assertEqual(result["decision"], "INVALID" if expected == 2 else "CLAIMS_COMPLETE")

    def test_missing_connector_holds_with_coordinator(self):
        o = sample()
        o["actions"][0].update(access="UNKNOWN", access_issue="MISSING_CONNECTOR")
        out = module.validate(o)
        self.assertEqual(out["decision"], "HOLD")
        self.assertIn("MISSING_CONNECTOR", out["blockers"][0]["reasons"])
        self.assertEqual(out["blockers"][0]["escalate_to"], "coordinator-agent")

    def test_blocked_approver_and_merge_decider_escalate_to_another_actor(self):
        for role, operation in (("reviewer", "pr.approve"), ("merge_decider", "pr.merge")):
            with self.subTest(role=role):
                record = sample()
                actor = record["roles"][role]
                record["actions"][0].update(actor=actor, operation=operation, permission="UNKNOWN",
                                             policy="UNKNOWN", evidence_ids=[])
                blocker = module.validate(record)["blockers"][0]
                self.assertEqual(blocker["escalate_to"], "coordinator-agent")
                record["roles"]["coordinator"] = actor
                blocker = module.validate(record)["blockers"][0]
                expected = record["roles"]["delegator"] if role == "reviewer" else None
                self.assertEqual(blocker["escalate_to"], expected)

    def test_missing_credentials_is_a_blocker_not_a_request_for_secret(self):
        o = sample()
        o["actions"][0].update(access="UNKNOWN", access_issue="MISSING_CREDENTIAL")
        out = module.validate(o)
        self.assertIn("MISSING_CREDENTIAL", out["blockers"][0]["reasons"])
        self.assertNotIn("ghp_", json.dumps(out))

    def test_unknown_scope_and_missing_scope_evidence_hold(self):
        o = sample()
        o["actions"][0]["permission"] = "UNKNOWN"
        self.assertIn("SCOPE_UNKNOWN", module.validate(o)["blockers"][0]["reasons"])
        o = sample()
        o["actions"][0]["evidence_ids"].remove("delegation-1")
        self.assertIn("DELEGATION_NOT_VERIFIED", module.validate(o)["blockers"][0]["reasons"])

    def test_stale_evidence_holds(self):
        o = sample()
        o["evidence"][1]["revision"] = "b" * 40
        self.assertIn("CAPABILITY_EVIDENCE_MISSING_OR_STALE", module.validate(o)["blockers"][0]["reasons"])

    def test_write_policy_requires_a_scoped_observation(self):
        o = self.push_claim()
        action = o["actions"][0]
        action["policy"] = "NOT_APPLICABLE"
        with self.assertRaisesRegex(ValueError, "policy gate"):
            module.validate(o)
        action["policy"] = "UNKNOWN"
        self.assertIn("POLICY_UNKNOWN", module.validate(o)["blockers"][0]["reasons"])
        action["policy"] = "VERIFIED"
        o["evidence"][2]["subject_actor"] = "executor-agent"
        result = module.validate(o)
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["blockers"][0]["reasons"], ["POLICY_EVIDENCE_MISSING_OR_STALE"])

    def test_review_and_merge_roles_enforced(self):
        o = sample()
        o["actions"][0]["operation"] = "pr.approve"
        o["actions"][0]["policy"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "reviewer"):
            module.validate(o)
        o["actions"][0]["operation"] = "pr.merge"
        with self.assertRaisesRegex(ValueError, "merge decider"):
            module.validate(o)

    def test_self_review_disallowed(self):
        o = sample()
        o["roles"]["reviewer"] = o["roles"]["executor"]
        with self.assertRaisesRegex(ValueError, "Independent reviewer"):
            module.validate(o)

    def test_reviewer_cannot_review_and_publish_the_candidate(self):
        record = self.push_claim()
        reviewer = record["roles"]["reviewer"]
        record["actions"][0]["actor"] = reviewer
        record["actions"].append(dict(record["actions"][0], operation="pr.approve"))
        with self.assertRaisesRegex(ValueError, "Independent reviewer"):
            module.validate(record)

    def test_merge_decider_can_hold_another_role_with_separate_current_gates(self):
        record = self.push_claim()
        actor = record["roles"]["delegator"]
        self.assertEqual(actor, record["roles"]["merge_decider"])
        record["actions"][0].update(actor=actor, operation="pr.merge")
        for item in record["evidence"]:
            item.update(subject_actor=actor, operation="pr.merge")
        self.assertEqual(module.validate(record)["decision"], "CLAIMS_COMPLETE")
        record["actions"][0].update(policy="UNKNOWN")
        self.assertEqual(module.validate(record)["decision"], "HOLD")

    def test_cross_repository_or_branch_write_rejected(self):
        o = sample()
        o["actions"][0]["repository"] = "elsewhere/repo"
        with self.assertRaisesRegex(ValueError, "target"):
            module.validate(o)
        o = sample()
        o["actions"][0]["branch"] = "main-protected"
        with self.assertRaisesRegex(ValueError, "target"):
            module.validate(o)

    def test_unrecognised_actions_not_downgraded(self):
        o = sample()
        o["actions"][0]["operation"] = "docker.exec"
        with self.assertRaisesRegex(ValueError, "Unknown operation"):
            module.validate(o)

    def test_suspected_secrets_rejected(self):
        for field in ("api_key", "token", "refresh_token", "accessToken", "credentials", "authorization", "cookie"):
            with self.subTest(field=field):
                o = sample()
                o["extra"] = {field: "no-real-value"}
                with self.assertRaisesRegex(ValueError, "Potential sensitive"):
                    module.validate(o)
        o = sample()
        o["task"]["goal"] = "do stuff with ghp_" + "x" * 22
        with self.assertRaisesRegex(ValueError, "Potential sensitive"):
            module.validate(o)
        for locator in ("https://fixture-user:fixture-pass@example.invalid/receipt",
                        "https://example.invalid/receipt?access_token=placeholder",
                        "https://example.invalid/receipt?client_secret=placeholder",
                        "https://example.invalid/receipt?password=placeholder"):
            with self.subTest(locator=locator):
                o = sample()
                o["evidence"][0]["reference"] = locator
                with self.assertRaisesRegex(ValueError, "Potential sensitive"):
                    module.validate(o)

    def test_bearer_prose_and_large_plain_input_remain_valid(self):
        record = sample()
        record["task"]["goal"] = "Document procedures to rotate Bearer tokens"
        record["extra"] = "a" * 250_000
        result = subprocess.run([sys.executable, str(SCRIPT), "validate", "--input", "-"],
                                input=json.dumps(record), capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "CLAIMS_COMPLETE")
        record["task"]["goal"] = "Bearer " + "A" * 32
        with self.assertRaisesRegex(ValueError, "Potential sensitive"):
            module.validate(record)

    def test_observed_access_with_missing_connector_is_invalid(self):
        o = sample()
        o["actions"][0]["access_issue"] = "MISSING_CONNECTOR"
        with self.assertRaisesRegex(ValueError, "Observed access"):
            module.validate(o)

    def test_missing_evidence_id_and_duplicate_actions_rejected(self):
        o = sample()
        o["actions"][0]["evidence_ids"] = ["does-not-exist"]
        with self.assertRaisesRegex(ValueError, "missing evidence"):
            module.validate(o)
        o = sample()
        o["actions"].append(copy.deepcopy(o["actions"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate actor/operation"):
            module.validate(o)

    def test_cli_exit_codes_and_output_contract(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"authority.json"
            p.write_text(json.dumps(sample()), encoding="utf-8")
            ok = subprocess.run([sys.executable, str(SCRIPT), "--input", str(p)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0)
            self.assertFalse(json.loads(ok.stdout)["execution_performed"])
            o = sample(); o["actions"][0].update(access="DENIED", access_issue="PERMISSION_DENIED")
            p.write_text(json.dumps(o), encoding="utf-8")
            hold = subprocess.run([sys.executable, str(SCRIPT), "--input", str(p)], capture_output=True, text=True)
            self.assertEqual(hold.returncode, 1)
            self.assertEqual(json.loads(hold.stdout)["decision"], "HOLD")
            p.write_text("{invalid", encoding="utf-8")
            invalid = subprocess.run([sys.executable, str(SCRIPT), "--input", str(p)], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(json.loads(invalid.stderr)["decision"], "INVALID")
            self.assertNotIn("{invalid", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
