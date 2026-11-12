"""Reviewer counterexamples: no certificate or credential false negatives."""
import importlib.util
import tempfile
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vibecode_guard_review", ROOT / "scripts" / "vibecode_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class ReviewerRegressionTests(unittest.TestCase):
    def test_test_identity_uses_tokens_not_substrings_or_project_names(self):
        for label in ("Latest Holdings", "Attestation Bank", "Contest Ltd", "PSF", "python-requests"):
            with self.subTest(label=label):
                self.assertFalse(guard._test_identity({"organizationName": label}))
        self.assertTrue(guard._test_identity({"commonName": "localhost"}))
        self.assertTrue(guard._test_identity({"commonName": "service.example"}))

    def test_sibling_certificate_never_excuses_an_unrelated_key(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tests" / "certs").mkdir(parents=True)
            (root / "tests" / "conftest.py").write_text("# fixture declaration\n")
            (root / "tests" / "certs" / "localhost.pem").write_text("-----BEGIN CERTIFICATE-----\nfixture\n")
            (root / "tests" / "certs" / "unrelated.key").write_text("-----BEGIN PRIVATE KEY-----\nunrelated\n")
            result = guard.inspect(root, ["tests/certs/localhost.pem", "tests/certs/unrelated.key", "tests/conftest.py"])
            key = next(f for f in result["findings"] if f["path"].endswith("unrelated.key"))
            self.assertEqual(key["classification"], "CONFIRMED")
            self.assertGreaterEqual(result["summary"]["actionable"], 1)

    def test_all_tracked_key_material_remains_actionable_even_if_likely_fixture(self):
        for category in ("TEST_FIXTURE_LIKELY_INTENTIONAL", "TEST_FIXTURE_UNCONFIRMED_DIRECTORY"):
            with self.subTest(category=category):
                f = guard._finding("TRACKED-KEY-MATERIAL", "high", "tests/certs/example.pem", None,
                                   "review", category, "low", "heuristic fixture hint")
                result = guard.report([f], 1, 0, truncated=False)
                self.assertEqual(result["status"], "WARNINGS_FOUND")
                self.assertEqual(result["summary"]["actionable"], 1)

    def test_missing_non_scanned_file_does_not_block_completion(self):
        with tempfile.TemporaryDirectory() as d:
            result = guard.inspect(Path(d), ["README.md"])
            self.assertEqual(result["status"], "CLEAR_HEURISTICS_ONLY")
            self.assertFalse(result["incomplete"])

    def test_multiline_tls_keyword_is_actionable(self):
        source = 'import requests\nrequests.get("https://x", verify = ' + chr(92) + '\n    False)\n'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "multiline.py").write_text(source)
            result = guard.inspect(root, ["src/multiline.py"])
            self.assertEqual(result["status"], "WARNINGS_FOUND")
            self.assertTrue(any(f["id"] == "TLS-VERIFY-DISABLED" for f in result["findings"]))

    def test_source_like_submodule_directory_is_not_missing_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "libs" / "highlight.js").mkdir(parents=True)
            result = guard.inspect(root, ["libs/highlight.js"])
            self.assertFalse(result["incomplete"])
            self.assertEqual(result["status"], "CLEAR_HEURISTICS_ONLY")

    def test_dockerfile_reference_is_production_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tests" / "certs").mkdir(parents=True)
            (root / "tests" / "certs" / "server.pem").write_text("fixture")
            (root / "Dockerfile").write_text("COPY tests/certs/server.pem /etc/server.pem\n")
            repo = guard.Repo(root, ["Dockerfile", "tests/certs/server.pem"])
            self.assertEqual(repo.production_references("tests/certs/server.pem"), ["Dockerfile"])

    def test_internal_key_and_env_symlinks_are_actionable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tests").mkdir()
            (root / "config").mkdir()
            (root / "keydata.txt").write_text("-----BEGIN PRIVATE KEY-----\ntest-only\n")
            (root / "settings.txt").write_text("TEST_TOKEN=example\n")
            (root / "tests" / "server.key").symlink_to("../keydata.txt")
            (root / "config" / ".env").symlink_to("../settings.txt")
            result = guard.inspect(root, ["tests/server.key", "keydata.txt",
                                          "config/.env", "settings.txt"])
            findings = {(f["path"], f["id"]): f for f in result["findings"]}
            self.assertIn(("tests/server.key", "TRACKED-KEY-MATERIAL"), findings)
            self.assertIn(("config/.env", "TRACKED-ENV"), findings)
            self.assertEqual(result["summary"]["actionable"], 2)
            self.assertEqual(result["status"], "WARNINGS_FOUND")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO requires a POSIX environment")
    def test_fifo_replacing_tracked_source_does_not_hang_reference_scan(self):
        # Run the actual CLI in a child process with a strict timeout.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "-C", str(root), "init", "-q"],
                           check=True, timeout=5)
            (root / "a.key").write_text("test-only")
            (root / "source.py").write_text("print('hello')\n")
            subprocess.run(["git", "-C", str(root), "add", "a.key", "source.py"],
                           check=True, timeout=5)
            (root / "source.py").unlink()
            os.mkfifo(root / "source.py")
            run = subprocess.run([sys.executable, str(ROOT / "scripts" / "vibecode_guard.py"),
                                  "--repo", str(root)],
                                 capture_output=True, text=True, timeout=5)
            report = json.loads(run.stdout)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(report["status"], "INCOMPLETE_SCAN")
            self.assertIn("source.py", [x["path"] for x in report["skipped_paths"]])
            self.assertTrue(any(x["id"] == "TRACKED-KEY-MATERIAL"
                                for x in report["findings"]))

    def test_form_feed_does_not_shift_python_ast_line_numbers(self):
        source = "import requests\nmarker = 1\f\nrequests.get('https://x', verify=False)\n"
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "source.py").write_text(source)
            report = guard.inspect(root, ["source.py"])
            matches = [f for f in report["findings"] if f["id"] == "TLS-VERIFY-DISABLED"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["line"], 3)
            self.assertEqual(report["status"], "WARNINGS_FOUND")

    def test_parser_resource_failure_marks_incomplete_instead_of_exiting_clean(self):
        for error in (RecursionError, MemoryError, ValueError):
            with self.subTest(error=error):
                with tempfile.TemporaryDirectory() as d:
                    root = Path(d)
                    (root / "source.py").write_text("print('hello')\n")
                    with patch.object(guard.ast, "parse", side_effect=error("synthetic parser limit")):
                        report = guard.inspect(root, ["source.py"])
                    self.assertEqual(report["status"], "INCOMPLETE_SCAN")
                    self.assertEqual(report["skipped_paths"][0]["path"], "source.py")

    def test_nested_function_inside_expected_ssl_error_is_not_suppressed(self):
        source = '''import pytest, requests

def test_case():
    with pytest.raises(requests.exceptions.SSLError):
        def later():
            requests.get("https://x", verify=False)
        raise requests.exceptions.SSLError()
'''
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "tests").mkdir()
            (root / "tests" / "test_case.py").write_text(source)
            result = guard.inspect(root, ["tests/test_case.py"])
            item = next(f for f in result["findings"] if f["id"] == "TLS-VERIFY-DISABLED")
            self.assertEqual(item["classification"], "TEST_CONTEXT_UNPROVEN")
            self.assertEqual(result["summary"]["actionable"], 1)


if __name__ == "__main__":
    unittest.main()
