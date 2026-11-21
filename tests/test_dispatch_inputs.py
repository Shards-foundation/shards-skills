"""The dispatcher binds explicit JSON input bytes to the reviewed plan."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dispatch_skills as dispatcher


class DispatchInputTests(unittest.TestCase):
    def setUp(self):
        dispatcher.LOCAL_STATE.mkdir(parents=True, exist_ok=True)
        state = tempfile.TemporaryDirectory(dir=dispatcher.LOCAL_STATE)
        self.addCleanup(state.cleanup)
        self.source = Path(state.name) / "in.json"
        self.target = Path(state.name) / "out.json"
        self.record = dict(goal="reviewed", repo="repo", branch="main", commit="test",
                           completed=[], decisions=[], evidence=[], blockers=[], pending=[])
        self.source.write_text(json.dumps(self.record), encoding="utf-8")
        self.options = dict(input_file=str(self.source), output_file=str(self.target),
                            allow_local_write=True)

    def handoff(self):
        return dispatcher.describe("shards-agent-handoff", **self.options)

    def test_same_path_different_bytes_refused(self):
        plan = self.handoff()
        self.source.write_text(json.dumps(dict(self.record, goal="later")), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "input changed"):
            dispatcher.run(plan)
        self.assertFalse(self.target.exists())
        self.assertNotEqual(self.handoff()["plan_sha256"], plan["plan_sha256"])

    def test_child_consumes_approved_bytes_during_path_replacement(self):
        plan = self.handoff()

        def replace_at_launch(argv, **kwargs):
            self.source.write_text(json.dumps(dict(self.record, goal="later")), encoding="utf-8")
            return subprocess.run(argv, **kwargs)

        receipt = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"], executor=replace_at_launch)
        self.assertEqual(receipt["observation"]["status"], "pass", receipt)
        self.assertEqual(json.loads(self.target.read_bytes())["checkpoint"], self.record)
        self.assertEqual(receipt["input_sha256"], plan["input_sha256"])

    def test_child_refuses_redirected_output_directory(self):
        output_dir = self.target.parent / "output"
        output_dir.mkdir()
        self.options["output_file"] = str(output_dir / self.target.name)
        plan = self.handoff()

        with tempfile.TemporaryDirectory() as outside:
            def redirect_at_launch(argv, **kwargs):
                output_dir.rmdir()
                output_dir.symlink_to(outside, target_is_directory=True)
                return subprocess.run(argv, **kwargs)

            receipt = dispatcher.run(plan, expect_plan_sha256=plan["plan_sha256"], executor=redirect_at_launch)
            self.assertEqual(receipt["observation"]["status"], "fail", receipt)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_unknown_revision_refuses_execution(self):
        with patch.object(dispatcher, "_source_revision", return_value=None):
            plan = self.handoff()
            with self.assertRaisesRegex(ValueError, "revision"):
                dispatcher.run(plan)
        self.assertFalse(self.target.exists())

    def test_input_symlink_refused(self):
        alias = self.source.with_name("alias.json")
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "symlink"):
            dispatcher.describe("shards-agent-handoff", **dict(self.options, input_file=str(alias)))

    def test_consequential_cli_requires_separately_reviewed_digest(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/dispatch_skills.py"),
                               "run", "--skill", "shards-agent-handoff", "--allow-local-write",
                               "--input-file", str(self.source), "--output-file", str(self.target),
                               "--execute"], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("--expect-plan-sha256", proc.stderr)
        self.assertFalse(self.target.exists())

    def test_consequential_api_requires_separately_reviewed_digest(self):
        plan = self.handoff()
        for digest, message in ((None, "--expect-plan-sha256"), ("f" * 64, "does not match")):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, message):
                dispatcher.run(plan, expect_plan_sha256=digest,
                               executor=lambda *args, **kwargs: self.fail("executed"))
        self.assertFalse(self.target.exists())
