"""Contract and fail-closed tests for Shards security assurance workflow."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("security_assurance", ROOT / "scripts" / "security_assurance.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SecurityAssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry, cls.registry_sha = mod.registry()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.scope = {"system": "Example test API", "owner": "test operator",
                      "jurisdictions": ["GB"], "revision": "test-sha-001", "environment": "test",
                      "authorised_scope": "synthetic local test", "profiles": ["base", "web"]}

    def payload(self, observations=None):
        return {"schema_version": 1, "scope": copy.deepcopy(self.scope), "observations": observations or []}

    def chosen(self):
        return mod.selection(self.registry["controls"], ["base", "web"])

    def evidence(self, controls=None):
        return [{"control_id": c["id"], "status": "pass",
                 "reference": "test-case:" + c["id"],
                 "revision": self.scope["revision"],
                 "observation": "Safe test record confirming a control was inspected",
                 "approver": None} for c in (controls or self.chosen())]

    def test_registry_has_unique_relevant_controls(self):
        identifiers = [c["id"] for c in self.registry["controls"]]
        self.assertGreaterEqual(len(identifiers), 40)
        self.assertEqual(len(set(identifiers)), len(identifiers))
        for group in ("base", "web", "ai", "crypto", "fintech", "cloud", "privacy", "governance"):
            self.assertIn(group, self.registry["profiles"])

    def test_plan_is_bounded_and_includes_base(self):
        value = mod.plan(self.registry, self.registry_sha, "App", "ai")
        self.assertEqual(value["profiles"], ["base", "ai"])
        self.assertGreater(len(value["controls"]), 10)
        self.assertIn("no tests performed", value["note"])

    def test_unknown_profile_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            mod.plan(self.registry, self.registry_sha, "App", "unauthorised")

    def test_duplicate_profile_rejected(self):
        with self.assertRaisesRegex(ValueError, "Repeated"):
            mod.plan(self.registry, self.registry_sha, "App", "web,web")

    def test_missing_evidence_holds(self):
        report = mod.assess(self.registry, self.registry_sha, self.payload(), "0" * 64)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["counts"]["blocked"], len(self.chosen()))

    def test_reported_pass_requires_external_review(self):
        report = mod.assess(self.registry, self.registry_sha, self.payload(self.evidence()), "0" * 64)
        self.assertEqual(report["verdict"], "REVIEW_READY_NOT_CERTIFIED")
        self.assertEqual(report["assessment"], "operator-attested-only")
        self.assertEqual(report["counts"]["reported_pass"], len(self.chosen()))

    def test_failure_blocks_release(self):
        observed = self.evidence()
        observed[0]["status"] = "fail"
        report = mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(report["counts"]["fail"], 1)

    def test_critical_na_stays_blocked(self):
        observed = self.evidence()
        item = next(x for x in observed if next(c for c in self.chosen() if c["id"] == x["control_id"])["severity"] == "critical")
        item["status"] = "not_applicable"
        item["approver"] = "named owner"
        report = mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertGreater(report["counts"]["blocked"], 0)

    def test_noncritical_na_requires_approver(self):
        observed = self.evidence()
        item = next(x for x in observed if next(c for c in self.chosen() if c["id"] == x["control_id"])["severity"] != "critical")
        item["status"] = "not_applicable"
        with self.assertRaisesRegex(ValueError, "approver"):
            mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)

    def test_duplicate_control_evidence_rejected(self):
        observed = self.evidence()
        observed[-1] = observed[0]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)

    def test_out_of_scope_control_rejected(self):
        observed = self.evidence()
        observed[0]["control_id"] = "AI-01"
        with self.assertRaisesRegex(ValueError, "Unknown"):
            mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)

    def test_stale_revision_rejected(self):
        observed = self.evidence()
        observed[0]["revision"] = "older-build"
        with self.assertRaisesRegex(ValueError, "revision"):
            mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)

    def test_invalid_scope_rejected(self):
        data = self.payload()
        data["scope"]["jurisdictions"] = []
        with self.assertRaisesRegex(ValueError, "Jurisdictions"):
            mod.assess(self.registry, self.registry_sha, data, "0" * 64)

    def test_credential_like_evidence_rejected(self):
        observed = self.evidence()
        observed[0]["reference"] = "ghp_" + "a" * 30
        with self.assertRaisesRegex(ValueError, "unsafe"):
            mod.assess(self.registry, self.registry_sha, self.payload(observed), "0" * 64)

    def test_symlink_input_rejected(self):
        f = self.tmp / "scope.json"
        f.write_text(json.dumps(self.payload()))
        l = self.tmp / "link.json"
        l.symlink_to(f)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            mod.read_json(l)

    def test_deeply_nested_json_returns_invalid_input_exit_2(self):
        import contextlib
        import io
        source = self.tmp / "nested.json"
        source.write_text("[" * 1600 + "0" + "]" * 1600, encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            exit_code = mod.main(["assess", "--input", str(source)])
        self.assertEqual(exit_code, 2)
        self.assertIn('"status": "BLOCKED"', err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_scope_survives_in_review_ready_report(self):
        observations = self.evidence()
        report = mod.assess(self.registry, self.registry_sha,
                            self.payload(observations), "a" * 64)
        self.assertEqual(report["verdict"], "REVIEW_READY_NOT_CERTIFIED")
        self.assertEqual(report["scope"], self.scope)
        self.assertEqual(report["scope"]["owner"], "test operator")
        self.assertEqual(report["scope"]["environment"], "test")
        self.assertEqual(report["scope"]["authorised_scope"], "synthetic local test")

    def test_scope_survives_in_blocked_report(self):
        report = mod.assess(self.registry, self.registry_sha,
                            self.payload(), "b" * 64)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertEqual(set(report["scope"]), set(self.scope))
        self.assertEqual(report["scope"]["revision"], self.scope["revision"])

    def test_output_is_create_only(self):
        f = self.tmp / "result.json"
        mod.emit({"hello": "world"}, str(f))
        with self.assertRaises(FileExistsError):
            mod.emit({"hello": "other"}, str(f))
        self.assertIn("world", f.read_text())

if __name__ == "__main__":
    unittest.main()
