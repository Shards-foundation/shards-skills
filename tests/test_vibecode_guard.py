"""Non-execution and redaction contracts for the Shards vibe-code preflight."""
import importlib.util
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

    def test_does_not_follow_symlink(self):
        original = self.file("real.py", "eval(input())")
        (self.root / "link.py").symlink_to(original)
        with self.assertRaisesRegex(ValueError, "Symlinked"):
            guard.inspect(self.root, ["link.py"])

    def test_cannot_escape_directory(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            guard.inspect(self.root, ["../outside.py"])

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
