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

    def test_missing_connector_holds_with_coordinator(self):
        o = sample()
        o["actions"][0].update(access="UNKNOWN", access_issue="MISSING_CONNECTOR")
        out = module.validate(o)
        self.assertEqual(out["decision"], "HOLD")
        self.assertIn("MISSING_CONNECTOR", out["blockers"][0]["reasons"])
        self.assertEqual(out["blockers"][0]["escalate_to"], "coordinator-agent")

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

    def test_write_policy_requires_nontrivial_gate(self):
        o = sample()
        o["actions"][0]["actor"] = "integrator-agent"
        o["actions"][0]["operation"] = "git.push"
        with self.assertRaisesRegex(ValueError, "policy gate"):
            module.validate(o)
        o["actions"][0]["policy"] = "UNKNOWN"
        self.assertIn("POLICY_UNKNOWN", module.validate(o)["blockers"][0]["reasons"])
        o["actions"][0]["policy"] = "VERIFIED"
        self.assertIn("POLICY_EVIDENCE_MISSING_OR_STALE", module.validate(o)["blockers"][0]["reasons"])
        o["evidence"].append({"id":"policy-1","kind":"policy","reference":"local:synthetic-policy","revision":"a"*40,"observed_by":"integrator-agent"})
        o["actions"][0]["evidence_ids"].append("policy-1")
        self.assertEqual(module.validate(o)["decision"], "CLAIMS_COMPLETE")
        self.assertFalse(module.validate(o)["authority_granted_by_validator"])

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
        o = sample()
        o["extra"] = {"api_key": "no-real-value"}
        with self.assertRaisesRegex(ValueError, "Potential sensitive"):
            module.validate(o)
        o = sample()
        o["task"]["goal"] = "do stuff with ghp_" + "x" * 22
        with self.assertRaisesRegex(ValueError, "Potential sensitive"):
            module.validate(o)

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

    def test_cli_exit_codes_and_no_remote_side_effects(self):
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
