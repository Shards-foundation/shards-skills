"""Non-execution and redaction contracts for the Shards vibe-code preflight."""
import importlib.util
import os
from unittest.mock import patch
from types import SimpleNamespace
import tempfile
import shutil
import subprocess
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
                         ["SYMLINK-INTERNAL", "DYNAMIC-EVAL"])

    def test_unsafe_path_is_recorded_without_aborting(self):
        self.file("safe.py", "eval(input())")
        report = guard.inspect(self.root, ["../outside.py", "safe.py"])
        self.assertIn("SKIPPED-UNSAFE-PATH", [x["id"] for x in report["findings"]])
        self.assertIn("DYNAMIC-EVAL", [x["id"] for x in report["findings"]])

    @unittest.skipUnless(shutil.which("git") and shutil.which("sh"), "Git and POSIX shell required")
    def test_actual_git_repo_with_hostile_local_fsmonitor_never_runs_it(self):
        """A real local config must not execute its fsmonitor command when scanned."""
        root = self.root / "hostile-checkout"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True, timeout=10)
        sample = root / "safe.py"
        sample.write_text("print('hello')", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "safe.py"], check=True, timeout=10)
        sentinel = self.root / "fsmonitor-was-invoked"
        fsmonitor = self.root / "hostile-fsmonitor.sh"
        fsmonitor.write_text(
            "#!/bin/sh\n"
            f"touch '{sentinel}'\n",
            encoding="utf-8",
        )
        fsmonitor.chmod(0o700)
        # Prove the fixture itself executes and writes the marker.
        subprocess.run([str(fsmonitor)], check=True, timeout=10)
        self.assertTrue(sentinel.exists(), "Hostile fixture must be executable")
        sentinel.unlink()
        subprocess.run(["git", "-C", str(root), "config", "--local",
                        "core.fsmonitor", str(fsmonitor)], check=True, timeout=10)
        self.assertFalse(sentinel.exists())
        names = guard.tracked(root)
        self.assertIn("safe.py", names)
        self.assertFalse(sentinel.exists(), "The untrusted fsmonitor command executed")

    def test_non_utf8_git_path_is_retained_for_safe_skip(self):
        metadata = b"100644 " + b"a" * 40 + b" 0\t"
        fake = SimpleNamespace(returncode=0, stdout=metadata + b"valid.py\0" + metadata + b"bad-\xff.py\0")
        with patch.object(guard.subprocess, "run", return_value=fake):
            names = guard.tracked(self.root)
        self.assertEqual(len(names), 2)
        self.assertEqual(names[0], "valid.py")
        self.assertEqual(names[1].encode("utf-8", "surrogateescape"), b"bad-\xff.py")

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


    def test_cap_blocks_clean_exit_even_when_later_tls_unseen(self):
        for i in range(guard.MAX_FINDINGS):
            self.file(f"a/key{i:04}.key", "fixture")
        self.file("z/unsafe.py", "request.get(url, verify=False)")
        names = [f"a/key{i:04}.key" for i in range(guard.MAX_FINDINGS)] + ["z/unsafe.py"]
        r = guard.inspect(self.root, names)
        self.assertEqual(r["status"], "INCOMPLETE_SCAN")
        self.assertTrue(r["truncated"])
        self.assertTrue(r["incomplete"])
        with patch.object(guard, "tracked", return_value=names), patch("sys.stdout"):
            self.assertEqual(guard.main(["--repo", str(self.root)]), 2)

    def test_skipped_source_must_block_clean_exit(self):
        self.file("oversized.py", "x" * (guard.MAX_FILE_BYTES + 1))
        r = guard.inspect(self.root, ["oversized.py", "missing.py"])
        self.assertEqual(r["status"], "INCOMPLETE_SCAN")
        self.assertEqual(len(r["skipped_paths"]), 2)
        with patch.object(guard, "tracked", return_value=["oversized.py"]), patch("sys.stdout"):
            self.assertEqual(guard.main(["--repo", str(self.root)]), 2)

    def test_tracked_env_findings_count_towards_limit(self):
        names = [f".env.fixture-{i}" for i in range(3)]
        for name in names:
            self.file(name, "EXAMPLE=fixture")
        with patch.object(guard, "MAX_FINDINGS", 2):
            result = guard.inspect(self.root, names)
        self.assertEqual(result["status"], "INCOMPLETE_SCAN")
        self.assertTrue(result["truncated"])
        self.assertEqual([finding["id"] for finding in result["findings"]], ["TRACKED-ENV"] * 2)

    def test_unreadable_source_preserves_findings_from_other_files(self):
        unreadable = self.file("a.py", "# unreadable fixture")
        self.file("b.py", "DEBUG = True")
        read_source = guard.read_source

        def read(path):
            if path == unreadable.resolve():
                raise PermissionError("denied")
            return read_source(path)

        with patch.object(guard, "read_source", side_effect=read):
            result = guard.inspect(self.root, ["a.py", "b.py"])
        self.assertEqual(result["status"], "INCOMPLETE_SCAN")
        self.assertEqual([entry["path"] for entry in result["skipped_paths"]], ["a.py"])
        self.assertEqual([finding["id"] for finding in result["findings"]], ["DEPLOYMENT-DEBUG"])

    def test_changed_source_is_incomplete(self):
        source = self.file("sample.py", "# original fixture")
        replaced = self.file("replacement.txt", "# replacement fixture")
        fstat = os.fstat
        observations = 0

        def replace_after_read(fd):
            nonlocal observations
            observations += 1
            if observations == 2:
                replaced.replace(source)
            return fstat(fd)

        with patch.object(guard.os, "fstat", side_effect=replace_after_read):
            result = guard.inspect(self.root, ["sample.py"])
        self.assertEqual(result["status"], "INCOMPLETE_SCAN")
        self.assertEqual([entry["path"] for entry in result["skipped_paths"]], ["sample.py"])

    def test_invalid_source_content_must_not_pass(self):
        self.file("nul.py", "a\x00b")
        (self.root / "nonutf8.py").write_bytes(b"\xff\xfe")
        r = guard.inspect(self.root, ["nul.py", "nonutf8.py"])
        self.assertEqual(r["status"], "INCOMPLETE_SCAN")
        self.assertEqual(len(r["skipped_paths"]), 2)

    def test_unsafe_symlink_is_incomplete_even_when_other_findings_exist(self):
        original = self.file("real.py", "eval(input())")
        (self.root / "link.py").symlink_to(original)
        r = guard.inspect(self.root, ["link.py", "real.py"])
        self.assertEqual(r["status"], "INCOMPLETE_SCAN")
        self.assertEqual([f["id"] for f in r["findings"]], ["SYMLINK-INTERNAL", "DYNAMIC-EVAL"])
        self.assertEqual([entry["path"] for entry in r["skipped_paths"]], ["link.py"])

    def test_exit_codes_preserve_complete_warning_and_clean(self):
        self.file("warning.py", "request.get(url, verify=False)")
        self.file("clean.py", "print('ok')")
        with patch.object(guard, "tracked", return_value=["warning.py"]), patch("sys.stdout"):
            self.assertEqual(guard.main(["--repo", str(self.root)]), 1)
        with patch.object(guard, "tracked", return_value=["clean.py"]), patch("sys.stdout"):
            self.assertEqual(guard.main(["--repo", str(self.root)]), 0)

if __name__ == "__main__":
    unittest.main()
