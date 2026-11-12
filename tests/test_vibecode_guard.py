"""Non-execution and redaction contracts for the Shards vibe-code preflight."""
import importlib.util
import os
from unittest.mock import patch
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vibecode_guard", ROOT / "scripts" / "vibecode_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class VibeCodeGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, path, content):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def test_empty_file_set_is_not_security_certification(self):
        result = guard.inspect(self.root, [])
        self.assertEqual(result["status"], "CLEAR_HEURISTICS_ONLY")
        self.assertIn("not a vulnerability scan", result["risk_boundary"])

    def test_tracked_env_is_flagged_without_secret_contents(self):
        self.file(".env.production", "PRIVATE_KEY=never-echo-this-value")
        report = guard.inspect(self.root, [".env.production"])
        self.assertEqual(report["findings"][0]["id"], "TRACKED-ENV")
        self.assertNotIn("never-echo", str(report))

    def test_env_example_is_not_flagged(self):
        self.file(".env.example", "PLACEHOLDER=replace")
        report = guard.inspect(self.root, [".env.example"])
        self.assertFalse(report["findings"])

    def test_tls_verification_disabled(self):
        self.file("app.py", "client.get(url, verify=False)")
        report = guard.inspect(self.root, ["app.py"])
        self.assertEqual(report["findings"][0]["id"], "TLS-VERIFY-DISABLED")
        self.assertNotIn("client.get", str(report))

    def test_tracked_key_material_never_read(self):
        self.file("private.pem", "SECRET KEY MATERIAL NEVER PRINTED")
        report = guard.inspect(self.root, ["private.pem"])
        self.assertEqual(report["findings"][0]["id"], "TRACKED-KEY-MATERIAL")
        self.assertNotIn("SECRET KEY MATERIAL", str(report))

    def test_sql_tenant_policy_is_reviewed_not_certified(self):
        self.file("tenancy.sql", "CREATE POLICY any_reader ON data USING (true);")
        report = guard.inspect(self.root, ["tenancy.sql"])
        self.assertEqual(report["findings"][0]["id"], "PERMISSIVE-RLS")

    def test_does_not_follow_symlink_and_continues(self):
        original = self.file("real.py", "eval(input())")
        (self.root / "link.py").symlink_to(original)
        report = guard.inspect(self.root, ["link.py", "real.py"])
        self.assertEqual([x["id"] for x in report["findings"]],
                         ["SKIPPED-UNSAFE-PATH", "DYNAMIC-EVAL"])

    def test_unsafe_path_is_recorded_without_aborting(self):
        self.file("safe.py", "eval(input())")
        report = guard.inspect(self.root, ["../outside.py", "safe.py"])
        self.assertIn("SKIPPED-UNSAFE-PATH", [x["id"] for x in report["findings"]])
        self.assertIn("DYNAMIC-EVAL", [x["id"] for x in report["findings"]])

    def test_non_utf8_git_path_is_retained_for_safe_skip(self):
        fake = SimpleNamespace(returncode=0, stdout=b"valid.py" + bytes([0]) + b"bad-" + bytes([255]) + b".py" + bytes([0]))
        with patch.object(guard.subprocess, "run", return_value=fake):
            names = guard.tracked(self.root)
        self.assertEqual(len(names), 2)
        self.assertEqual(names[0], "valid.py")

    def test_git_disables_local_fsmonitor_and_untrusted_env(self):
        fake = SimpleNamespace(returncode=0, stdout=b"")
        with patch.dict(os.environ, {"GIT_CONFIG_PARAMETERS": "core.fsmonitor=bad",
                                     "GIT_INDEX_FILE": "/tmp/untrusted-index"}):
            with patch.object(guard.subprocess, "run", return_value=fake) as run:
                guard.tracked(self.root)
        args, kw = run.call_args
        self.assertIn("core.fsmonitor=false", args[0])
        self.assertIn("--no-optional-locks", args[0])
        self.assertEqual(kw["env"]["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertNotIn("GIT_CONFIG_PARAMETERS", kw["env"])
        self.assertNotIn("GIT_INDEX_FILE", kw["env"])


    def test_skips_unlisted_extensions(self):
        self.file("notes.txt", "eval(input())")
        self.assertFalse(guard.inspect(self.root, ["notes.txt"])["findings"])

    def test_bounded_source_bytes(self):
        self.file("verylarge.py", "x" * (guard.MAX_FILE_BYTES + 1))
        result = guard.inspect(self.root, ["verylarge.py"])
        self.assertEqual(result["inspected_source_bytes"], 0)

    def test_findings_are_deterministically_sorted(self):
        self.file("b.py", "eval(input())")
        self.file("a.py", "eval(input())")
        result = guard.inspect(self.root, ["b.py", "a.py"])
        self.assertEqual([item["path"] for item in result["findings"]], ["a.py", "b.py"])

if __name__ == "__main__":
    unittest.main()
