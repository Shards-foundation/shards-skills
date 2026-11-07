"""Adversarial and functional tests for bounded local multi-agent delegation."""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dispatch_skills
import shards_agent_harness as harness


def fake_receipt(plan: dict, outcome: str = "pass") -> dict:
    return {
        "observation": {"status": outcome, "exit_code": 0 if outcome == "pass" else 1,
                        "stdout_tail": '{"checked":true}', "stderr_tail": ""},
        "receipt_id": "mock-" + plan["skill"],
        "script_sha256": plan["script_sha256"],
    }


class AgentHarnessTests(unittest.TestCase):
    def test_four_curated_skills_have_distinct_fixed_actions(self):
        self.assertEqual(set(harness.FIXED_ACTIONS), {
            "a2a-check", "dual-channel-check", "subagent-check", "swarm-check"})
        for name, (effect, script, operation) in dispatch_skills.REGISTRY.items():
            if name not in dispatch_skills.HARNESS_SKILLS:
                continue
            self.assertEqual(effect, "read-only")
            self.assertEqual(script, "scripts/shards_agent_harness.py")
            self.assertIn(operation, harness.FIXED_ACTIONS)
            plan = dispatch_skills.describe(name)
            self.assertEqual(plan["command"][-2:], [operation, "--execute"])
            self.assertEqual(plan["timeout_seconds"], 420)
            dispatch_skills._check_plan_integrity(plan)

    def test_profile_plan_contains_bounded_unique_subagents(self):
        for profile in harness.PRESETS:
            with self.subTest(profile=profile):
                plan = harness.build_plan(profile)
                self.assertFalse(plan["executed"])
                self.assertFalse(plan["a2a_network_compatible"])
                self.assertEqual(plan["channels"], ["control", "data"])
                self.assertEqual(len({task["task_id"] for task in plan["tasks"]}),
                                 len(plan["tasks"]))
                self.assertEqual(len({task["agent_id"] for task in plan["tasks"]}),
                                 len(plan["tasks"]))
                self.assertLessEqual(plan["workers"], harness.MAX_WORKERS)
                self.assertTrue(all(task["skill"] in harness.ALLOWED
                                    for task in plan["tasks"]))

    def test_custom_plan_accepts_only_allowlisted_targets(self):
        p = harness.build_plan("custom", skills=[
            "shards-skill-dispatch", "shards-catalogue-sync"], workers=2)
        self.assertEqual(p["workers"], 2)
        with self.assertRaisesRegex(ValueError, "requires at least"):
            harness.build_plan("custom")
        for bad in ("shards-agent-handoff", "shards-automation-operator",
                    "rebelytics-observer-rebelytics-observer",
                    "shards-parallel-swarm", "../escape", "unknown"):
            with self.subTest(skill=bad):
                with self.assertRaises(ValueError):
                    harness.build_plan("custom", skills=[bad])

    def test_concurrency_and_task_limits_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Workers must"):
            harness.build_plan("swarm", workers=0)
        with self.assertRaisesRegex(ValueError, "Workers must"):
            harness.build_plan("swarm", workers=5)
        with self.assertRaisesRegex(ValueError, "sequentially"):
            harness.build_plan("subagents", workers=2)
        with self.assertRaisesRegex(ValueError, "bounded agent limit"):
            harness.build_plan("custom", skills=[
                "shards-catalogue-sync"] * (harness.MAX_TASKS + 1))
        with self.assertRaisesRegex(ValueError, "does not accept"):
            harness.build_plan("swarm", skills=["shards-skill-dispatch"])

    def test_control_and_data_are_disjoint_with_stable_task_mapping(self):
        plan = harness.build_plan("subagents")
        record = harness.execute(plan, runner=fake_receipt)
        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["summary"], {"total": 2, "passed": 2, "failed": 0})
        control, data = record["control_channel"], record["data_channel"]
        self.assertTrue(all(entry["channel"] == "control" for entry in control))
        self.assertTrue(all("artifact" not in entry for entry in control))
        self.assertTrue(all(entry["channel"] == "data" for entry in data))
        self.assertTrue(all("event" not in entry for entry in data))
        self.assertEqual([e["task_id"] for e in data],
                         [e["task_id"] for e in plan["tasks"]])
        self.assertEqual([e["agent_id"] for e in data],
                         [e["agent_id"] for e in plan["tasks"]])
        self.assertEqual([entry["sequence"] for entry in control],
                         list(range(len(control))))
        checksum = dict(record)
        checksum.pop("receipt_sha256")
        self.assertEqual(record["receipt_sha256"], harness.fingerprint(checksum))

    def test_swarm_actually_runs_in_parallel_and_joins_ordered_results(self):
        barrier = threading.Barrier(3)
        seen: list[str] = []
        lock = threading.Lock()

        def parallel_worker(plan):
            with lock:
                seen.append(plan["skill"])
            barrier.wait(timeout=5)
            return fake_receipt(plan)

        plan = harness.build_plan("swarm")
        self.assertEqual(plan["workers"], 3)
        record = harness.execute(plan, runner=parallel_worker)
        self.assertEqual(record["status"], "pass")
        self.assertEqual(len(seen), 3)
        self.assertEqual([item["skill"] for item in record["data_channel"]],
                         list(harness.PRESETS["swarm"]))

    def test_failing_delegate_makes_entire_swarm_fail(self):
        def worker(plan):
            result = "fail" if plan["skill"] == "shards-catalogue-sync" else "pass"
            return fake_receipt(plan, result)
        record = harness.execute(harness.build_plan("swarm"), runner=worker)
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["summary"], {"total": 3, "passed": 2, "failed": 1})
        failed = [event for event in record["control_channel"]
                  if event.get("event") == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["task_id"], "task-002")

    def test_delegate_validation_error_is_attributed_not_silently_ignored(self):
        def broken(_):
            raise ValueError("script hash changed")
        record = harness.execute(harness.build_plan("dual-channel"), runner=broken)
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["summary"]["failed"], 2)
        self.assertTrue(all(entry["artifact"]["error_type"] == "ValueError"
                            for entry in record["data_channel"]))

    def test_delegate_receipt_rejects_false_success_and_digest_mismatch(self):
        plan = harness.build_plan("a2a")
        def invalid(delegate, mode):
            receipt = fake_receipt(delegate)
            if mode == "digest":
                receipt["script_sha256"] = "0" * 64
            elif mode == "nonzero":
                receipt["observation"]["exit_code"] = 17
            elif mode == "missing":
                receipt["observation"].pop("exit_code")
            elif mode == "false_failure":
                receipt["observation"]["status"] = "fail"
            return receipt
        for mode in ("digest", "nonzero", "missing", "false_failure"):
            with self.subTest(mode=mode):
                result = harness.execute(plan, runner=lambda p: invalid(p, mode))
                self.assertEqual(result["status"], "fail")
                self.assertEqual(result["summary"]["failed"], 2)
                self.assertTrue(all(entry["artifact"]["error_type"] == "ValueError"
                                    for entry in result["data_channel"]))

    def test_delegate_receipt_accepts_consistent_nonzero_failure(self):
        result = harness.execute(harness.build_plan("a2a"),
                                 runner=lambda p: fake_receipt(p, "fail"))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(all(entry["artifact"]["status"] == "fail"
                            for entry in result["data_channel"]))

    def test_tampered_plan_and_regenerated_digest_denied(self):
        plan = harness.build_plan("swarm")
        tasks = [dict(task) for task in plan["tasks"]]
        tasks[0]["task_id"] = "forged-coordinator-task"
        changed = dict(plan, tasks=tasks)
        changed["plan_sha256"] = harness.fingerprint(
            {k: v for k, v in changed.items() if k != "plan_sha256"})
        with self.assertRaisesRegex(ValueError, "changed"):
            harness.execute(changed, runner=fake_receipt)
        changed = dict(plan, plan_sha256="f" * 64)
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            harness.execute(changed, runner=fake_receipt)

    def test_receipt_saved_exclusively(self):
        record = harness.execute(harness.build_plan("a2a"), runner=fake_receipt)
        with tempfile.TemporaryDirectory() as temp:
            path = harness.persist(record, Path(temp))
            self.assertEqual(json.loads(path.read_text())["run_id"], record["run_id"])
            with self.assertRaises(FileExistsError):
                harness.persist(record, Path(temp))

    def test_cli_saved_receipt_matches_stdout_and_checksum(self):
        record = harness.execute(harness.build_plan("a2a"), runner=fake_receipt)
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with patch.object(harness, "execute", return_value=record), \
                 patch.object(harness, "REPORTS", Path(temp)), \
                 redirect_stdout(output):
                self.assertEqual(harness.main([
                    "run", "--profile", "a2a", "--execute", "--save-receipt"
                ]), 0)
            printed = json.loads(output.getvalue())
            saved = json.loads((Path(temp) / (record["run_id"] + ".json")).read_text())
            self.assertEqual(printed, saved)
            self.assertNotIn("report_path", printed)
            digest = printed.pop("receipt_sha256")
            self.assertEqual(digest, harness.fingerprint(printed))

    def test_cli_failed_receipt_is_still_saved_consistently(self):
        record = harness.execute(harness.build_plan("a2a"),
                                 runner=lambda plan: fake_receipt(plan, "fail"))
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with patch.object(harness, "execute", return_value=record), \
                 patch.object(harness, "REPORTS", Path(temp)), \
                 redirect_stdout(output):
                self.assertEqual(harness.main([
                    "run", "--profile", "a2a", "--execute", "--save-receipt"
                ]), 1)
            self.assertEqual(json.loads(output.getvalue()),
                             json.loads((Path(temp) / (record["run_id"] + ".json")).read_text()))

    def test_cli_is_dry_by_default(self):
        script = str(ROOT / "scripts/shards_agent_harness.py")
        listing = subprocess.run([sys.executable, script, "list"],
                                 capture_output=True, text=True, timeout=15)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("swarm", json.loads(listing.stdout)["profiles"])
        plan = subprocess.run([sys.executable, script, "plan", "--profile", "swarm"],
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertFalse(json.loads(plan.stdout)["executed"])
        denied = subprocess.run([sys.executable, script, "run", "--profile", "swarm"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(denied.returncode, 2)
        denied = subprocess.run([sys.executable, script, "swarm-check"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(denied.returncode, 2)


if __name__ == "__main__":
    unittest.main()
