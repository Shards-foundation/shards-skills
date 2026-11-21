"""Unit and CLI tests for governed curated skill execution."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dispatch_skills as dispatcher
import verify_plugins as integrity

class SkillDispatchTests(unittest.TestCase):
    def test_registry_exact_curated_skill_names(self):
        self.assertEqual(len(dispatcher.REGISTRY), 13)
        self.assertEqual(set(dispatcher.REGISTRY), {
            "shards-repository-health", "shards-skill-audit",
            "shards-release-gate", "shards-agent-handoff",
            "shards-automation-operator", "shards-catalogue-sync",
            "shards-skill-dispatch", "shards-a2a-harness",
            "shards-a2a-authority-preflight", "shards-execution-contract",
            "shards-dual-channel", "shards-subagents", "shards-parallel-swarm",
        })

    def test_structural_plugin_integrity(self):
        report = integrity.validate()
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["registered_skills"], 13)

    def test_authority_preflight_is_read_only_and_plan_pinned(self):
        with self.assertRaisesRegex(ValueError, "requires --input-file"):
            dispatcher.describe("shards-a2a-authority-preflight")
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-a2a-authority-preflight",
                                input_file="/tmp/untrusted-input.json")
        fixture = ROOT / "plugins/shards-core/skills/shards-a2a-authority-preflight/references/example-readonly.json"
        data = fixture.read_bytes()
        dispatcher.LOCAL_STATE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dispatcher.LOCAL_STATE) as directory:
            sample = Path(directory) / "authority.json"
            sample.write_bytes(data)
            plan = dispatcher.describe("shards-a2a-authority-preflight", input_file=str(sample))
            self.assertEqual(plan["effect"], "read-only")
            self.assertEqual(plan["command"][-3:], ["validate", "--input", "-"])
            self.assertEqual(plan["input_sha256"], hashlib.sha256(data).hexdigest())
            with self.assertRaisesRegex(ValueError, "requires --expect-plan-sha256"):
                dispatcher.run(plan)
            result = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"])
            self.assertEqual(result["observation"]["status"], "pass", result)
            self.assertEqual(json.loads(result["observation"]["stdout_tail"])["decision"], "CLAIMS_COMPLETE")

            forged = dict(plan, command=plan["command"] + ["--unsafe"])
            forged["plan_sha256"] = dispatcher._plan_fingerprint(forged)
            with self.assertRaisesRegex(ValueError, "command differs"):
                dispatcher.run(forged, expect_plan_sha256=forged["plan_sha256"],
                               executor=lambda *args, **kwargs: self.fail("executed"))

            changed = json.loads(data)
            changed["actions"][0]["permission"] = "UNKNOWN"
            sample.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Reviewed input changed"):
                dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"])
            hold = dispatcher.describe("shards-a2a-authority-preflight", input_file=str(sample))
            result = dispatcher.run(hold, expect_plan_sha256=hold["plan_sha256"])
            self.assertEqual(result["observation"]["status"], "hold", result)

    def test_plan_is_read_only(self):
        report = dispatcher.describe("shards-repository-health")
        self.assertFalse(report["executed"])
        self.assertEqual(report["effect"], "read-only")
        self.assertEqual(len(report["script_sha256"]), 64)

    def test_execution_contract_dispatch_requires_pinned_read_only_input(self):
        skill = "shards-execution-contract"
        with self.assertRaisesRegex(ValueError, "requires --input-file"):
            dispatcher.describe(skill)
        fixture = ROOT / "plugins/shards-core/skills/shards-execution-contract/references/contract-example.json"
        data = fixture.read_bytes()
        dispatcher.LOCAL_STATE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dispatcher.LOCAL_STATE) as directory:
            sample = Path(directory) / "contract.json"
            sample.write_bytes(data)
            plan = dispatcher.describe(skill, input_file=str(sample))
            self.assertEqual(plan["effect"], "read-only")
            self.assertEqual(plan["command"][-2:], ["--input", "-"])
            self.assertEqual(plan["input_sha256"], hashlib.sha256(data).hexdigest())
            self.assertNotIn("output_file", plan)
            with self.assertRaisesRegex(ValueError, "requires --expect-plan-sha256"):
                dispatcher.run(plan)
            result = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"])
            self.assertEqual(result["observation"]["status"], "hold", result)
            report = json.loads(result["observation"]["stdout_tail"])
            self.assertFalse(report["execution_performed"])
            self.assertFalse(report["approval_verified"])
            sample.write_bytes(data + b"\n")
            with self.assertRaisesRegex(ValueError, "Reviewed input changed"):
                dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"])

    def test_plan_digest_is_stable_and_covers_command(self):
        plan = dispatcher.describe("shards-repository-health")
        self.assertEqual(len(plan["plan_sha256"]), 64)
        self.assertEqual(plan["plan_sha256"], dispatcher.describe("shards-repository-health")["plan_sha256"])
        altered = dict(plan, command=plan["command"] + ["--unexpected"])
        self.assertNotEqual(plan["plan_sha256"], dispatcher._plan_fingerprint(altered))

    def test_mutated_script_hash_fails_before_subprocess(self):
        plan = dispatcher.describe("shards-repository-health")
        plan["script_sha256"] = "0" * 64
        plan["plan_sha256"] = dispatcher._plan_fingerprint(plan)
        with patch("dispatch_skills.subprocess.run") as executor:
            with self.assertRaisesRegex(ValueError, "executable changed"):
                dispatcher.run(plan, executor=executor)
            executor.assert_not_called()

    def test_launch_executes_verified_entry_point_after_file_changes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            script = Path(directory).resolve() / "check.py"
            script.write_text('print("verified entry point")\n', encoding="utf-8")
            with patch.object(dispatcher, "_repository_path", return_value=script):
                plan = dispatcher.describe("shards-repository-health")

                def change_at_launch(argv, **options):
                    script.write_text('print("changed entry point")\n', encoding="utf-8")
                    return subprocess.run(argv, **options)

                receipt = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"], executor=change_at_launch)
        self.assertEqual(receipt["observation"]["status"], "pass", receipt)
        self.assertEqual(receipt["observation"]["stdout_tail"].strip(), "verified entry point")

    def test_launch_imports_verified_local_module_after_file_changes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            entry = root / "check.py"
            dependency = root / "dispatch_skills.py"
            entry.write_text("from dispatch_skills import LABEL\nprint(LABEL)\n", encoding="utf-8")
            dependency.write_text('LABEL = "verified module"\n', encoding="utf-8")
            paths = {"scripts/verify_plugins.py": entry, "scripts/dispatch_skills.py": dependency}
            with patch.object(dispatcher, "_repository_path", side_effect=paths.__getitem__):
                plan = dispatcher.describe("shards-skill-dispatch")

                def change_at_launch(argv, **options):
                    dependency.write_text('LABEL = "changed module"\n', encoding="utf-8")
                    return subprocess.run(argv, **options)

                receipt = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"], executor=change_at_launch)
        self.assertEqual(receipt["observation"]["status"], "pass", receipt)
        self.assertEqual(receipt["observation"]["stdout_tail"].strip(), "verified module")

    def test_mutated_plan_or_revision_fails_before_subprocess(self):
        plan = dispatcher.describe("shards-repository-health")
        changed = dict(plan, timeout_seconds=9000)
        with self.assertRaisesRegex(ValueError, "timeout differs"):
            dispatcher.run(changed, executor=lambda *a, **k: self.fail("executed"))
        with patch.object(dispatcher, "_source_revision", return_value="other-revision"):
            with self.assertRaisesRegex(ValueError, "revision changed"):
                dispatcher.run(plan, executor=lambda *a, **k: self.fail("executed"))

    def test_forged_arguments_rejected_even_with_recomputed_digest(self):
        plan = dispatcher.describe("shards-repository-health")
        altered = dict(plan, command=plan["command"] + ["--unsafe-override"])
        altered["plan_sha256"] = dispatcher._plan_fingerprint(altered)
        with patch("dispatch_skills.subprocess.run") as executor:
            with self.assertRaisesRegex(ValueError, "command differs"):
                dispatcher.run(altered, executor=executor)
            executor.assert_not_called()

    def test_effect_and_authorization_metadata_are_immutable(self):
        plan = dispatcher.describe("shards-repository-health")
        for change, message in (
                ({"effect": "local-write"}, "effect differs"),
                ({"approved_by": "agent-approved"}, "authorization metadata"),
                ({"executed": True}, "authorization metadata")):
            altered = dict(plan, **change)
            altered["plan_sha256"] = dispatcher._plan_fingerprint(altered)
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, message):
                    dispatcher.run(altered, executor=lambda *a, **k: self.fail("executed"))

    def test_valid_read_only_audit_still_executes(self):
        plan = dispatcher.describe("shards-skill-audit",
                                   target_skill="rebelytics-observer-rebelytics-observer")
        def fake(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        receipt = dispatcher.run(plan, executor=fake)
        self.assertEqual(receipt["observation"]["status"], "pass")

    def test_unapproved_cli_plan_digest_fails_closed(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/dispatch_skills.py"),
             "run", "--skill", "shards-repository-health", "--execute",
             "--expect-plan-sha256", "0" * 64],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("does not match", proc.stderr)

    def test_unknown_registry_action_denied(self):
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-unknown-action")

    def test_path_traversal_target_denied(self):
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-skill-audit", target_skill="../outside")
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-skill-audit")

    def test_imported_skill_can_be_audited_not_executed(self):
        target = "rebelytics-observer-rebelytics-observer"
        report = dispatcher.describe("shards-skill-audit", target_skill=target)
        self.assertIn(target, report["command"][-1])
        with self.assertRaises(ValueError):
            dispatcher.describe(target)

    def test_checkpoint_writes_require_extra_flag(self):
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-agent-handoff")
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-agent-handoff", allow_local_write=True,
                                input_file="/tmp/not-allowed.json",
                                output_file="/tmp/not-allowed-out.json")

    def test_fixed_maintenance_profile(self):
        valid = dispatcher.describe("shards-automation-operator", profile="quick")
        self.assertEqual(valid["command"][-2:], ["--workflow", "quick"])
        with self.assertRaises(ValueError):
            dispatcher.describe("shards-automation-operator", profile="deploy")

    def test_receipt_and_secret_redaction(self):
        captured = []
        secret = "ghp_" + "a" * 28
        def fake(argv, **kwargs):
            captured.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="key=" + secret, stderr="")
        plan = dispatcher.describe("shards-repository-health")
        with patch.dict(os.environ, {"GITHUB_TOKEN": secret, "PYTHONPATH": "/tmp/inject"}):
            receipt = dispatcher.run(plan, executor=fake)
        self.assertEqual(receipt["observation"]["status"], "pass")
        self.assertNotIn(secret, receipt["observation"]["stdout_tail"])
        self.assertEqual(len(receipt["receipt_id"]), 36)
        self.assertNotIn("GITHUB_TOKEN", captured[0][1]["env"])
        self.assertNotIn("PYTHONPATH", captured[0][1]["env"])
        self.assertNotIn("shell", captured[0][1])

    def test_expected_hold_is_not_success(self):
        plan = dispatcher.describe("shards-release-gate")
        def fake(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout='{"decision":"HOLD"}', stderr="")
        receipt = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"], executor=fake)
        self.assertEqual(receipt["observation"]["status"], "hold")
        self.assertFalse(receipt["production_verified"])

    def test_timeout_recorded(self):
        plan = dispatcher.describe("shards-repository-health")
        def fake(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, timeout=1)
        receipt = dispatcher.run(plan, executor=fake)
        self.assertEqual(receipt["observation"]["status"], "timeout")

    def test_cli_list_plan_and_execution_gate(self):
        script = str(ROOT / "scripts/dispatch_skills.py")
        listing = subprocess.run([sys.executable, script, "list"],
                                 capture_output=True, text=True, timeout=15)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(len(json.loads(listing.stdout)["skills"]), 13)
        plan = subprocess.run([sys.executable, script, "plan", "--skill", "shards-repository-health"],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertFalse(json.loads(plan.stdout)["executed"])
        denied = subprocess.run([sys.executable, script, "run", "--skill", "shards-repository-health"],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(denied.returncode, 2)

    def test_integrity_cli(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/verify_plugins.py"), "--check"],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
