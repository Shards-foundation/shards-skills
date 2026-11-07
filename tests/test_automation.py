"""Regression coverage for safe, automated skill maintenance."""
import importlib.util
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

def script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

automate = script("automate.py")
catalogue_sync = script("catalogue_sync.py")
portfolio = script("audit_portfolio.py")

class AutomationTests(unittest.TestCase):
    def fixture(self, root, imported=False):
        name = "sample-import" if imported else "sample-first"
        skill = root / "skills" / name
        skill.mkdir(parents=True)
        body = ("---\nname: " + name +
                "\ndescription: Deterministic test fixture with a sufficient description.\n" +
                "status: " + ("review" if imported else "draft") +
                "\ncategory: testing\n---\n# Sample\n## Workflow\nPerform a local check.\n")
        (skill / "SKILL.md").write_text(body, encoding="utf-8")
        if imported:
            (skill / "UPSTREAM.md").write_text("Provenance pending review", encoding="utf-8")
            scripts = skill / "scripts"
            scripts.mkdir()
            (scripts / "untrusted.py").write_text("raise RuntimeError('must never execute')",
                                                  encoding="utf-8")
        return skill

    def make_catalogue(self, root):
        (root / "catalogue").mkdir()
        (root / "catalogue/catalogue.json").write_text(json.dumps({
            "schema_version": 1, "name": "Shards Skills", "version": "0.1.0",
            "status": "bootstrap", "skill_count": 0, "skill_paths": [],
            "categories": [], "skills": []}), encoding="utf-8")

    def test_plan_cannot_run(self):
        for name in automate.WORKFLOWS:
            result = automate.run_workflow(name, execute=False)
            self.assertFalse(result["executed"])
            self.assertEqual(len(result["steps"]), len(automate.WORKFLOWS[name]))

    def test_workflow_rejects_unknown_step(self):
        with self.assertRaises(ValueError):
            automate.command_for("scripts/arbitrary.py")

    def test_workflow_rejects_unknown_name(self):
        with self.assertRaises(ValueError):
            automate.plan("remote-deploy")

    def test_successful_execution_uses_approved_commands_only(self):
        seen = []
        def fake(argv, **kwargs):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="checked", stderr="")
        data = automate.run_workflow("quick", execute=True, run_command=fake)
        self.assertEqual(data["status"], "pass")
        self.assertEqual(len(seen), len(automate.WORKFLOWS["quick"]))
        self.assertTrue(all(cmd[0] == sys.executable for cmd in seen))
        self.assertTrue(all("untrusted.py" not in " ".join(cmd) for cmd in seen))

    def test_fail_fast(self):
        calls = []
        def fake(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 3, stdout="", stderr="failed")
        data = automate.run_workflow("verify", execute=True, fail_fast=True, run_command=fake)
        self.assertEqual(data["status"], "fail")
        self.assertEqual(len(calls), 1)
        self.assertEqual(data["completed"], 1)

    def test_credential_redaction(self):
        secret = "ghp_" + "a" * 30
        self.assertNotIn(secret, automate.safe_tail(secret + " found"))
        self.assertIn("[REDACTED]", automate.safe_tail(secret))

    def test_subprocess_environment_is_minimal(self):
        observed = []
        secret = "ghp_" + "s" * 28
        def fake(argv, **kwargs):
            observed.append(kwargs["env"])
            return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")
        with patch.dict(os.environ, {
                "GITHUB_TOKEN": secret, "AWS_SECRET_ACCESS_KEY": secret,
                "PYTHONPATH": "/tmp/attacker", "LD_PRELOAD": "/tmp/inject",
                "PATH": os.environ.get("PATH", ""), "CI": "true"}):
            result = automate.run_workflow("quick", execute=True, run_command=fake)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(len(observed), len(automate.WORKFLOWS["quick"]))
        for env in observed:
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
            self.assertNotIn("PYTHONPATH", env)
            self.assertNotIn("LD_PRELOAD", env)
            self.assertEqual(env["PYTHONNOUSERSITE"], "1")
            self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
            self.assertEqual(env["CI"], "true")

    def test_missing_or_symlinked_trusted_script_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "checkout"
            scripts = checkout / "scripts"
            scripts.mkdir(parents=True)
            external = Path(directory) / "external.py"
            external.write_text("raise RuntimeError('should never run')", encoding="utf-8")
            with patch.object(automate, "ROOT", checkout):
                with self.assertRaisesRegex(ValueError, "missing, symlinked"):
                    automate.command_for("catalogue-check")
                target = scripts / "catalogue_sync.py"
                target.symlink_to(external)
                with self.assertRaisesRegex(ValueError, "missing, symlinked"):
                    automate.command_for("catalogue-check")
                target.unlink()
                target.write_text("print('trusted fixture')", encoding="utf-8")
                cmd, limit = automate.command_for("catalogue-check")
                self.assertEqual(cmd[1], str(target))
                self.assertEqual(limit, 45)

    def test_log_redaction_covers_pats_and_private_keys(self):
        token = "github_pat_" + "x" * 40
        pem = "-----BEGIN PRIVATE KEY-----\nSENSITIVE_MATERIAL\n-----END PRIVATE KEY-----"
        self.assertNotIn(token, automate.safe_tail(token))
        self.assertNotIn("SENSITIVE_MATERIAL", automate.safe_tail(pem))
        unterminated = "-----BEGIN PRIVATE KEY-----\nSECRET_UNTERMINATED"
        self.assertNotIn("SECRET_UNTERMINATED", automate.safe_tail(unterminated))

    def test_report_writes_create_only(self):
        with tempfile.TemporaryDirectory() as temp:
            first = automate.write_report(Path(temp), {"status": "pass"})
            self.assertTrue(first.is_file())
            self.assertEqual(json.loads(first.read_text())["status"], "pass")

    def test_catalogue_drift_can_be_read_without_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_catalogue(root)
            self.fixture(root)
            before = (root / "catalogue/catalogue.json").read_text()
            expected, report = catalogue_sync.inspect_catalogue(root)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["observed_skills"], 1)
            self.assertEqual(before, (root / "catalogue/catalogue.json").read_text())
            self.assertEqual(expected["skill_count"], 1)

    def test_catalogue_repair_is_explicit_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_catalogue(root)
            self.fixture(root)
            with self.assertRaises(ValueError):
                catalogue_sync.repair(root)
            # Initial missing entry cannot be silently repaired; create complete catalogue fixture.
            expected, _ = catalogue_sync.inspect_catalogue(root)
            (root / "catalogue/catalogue.json").write_text(json.dumps(expected))
            fixed = catalogue_sync.repair(root)
            self.assertFalse(fixed["repaired"])
            self.assertEqual(catalogue_sync.inspect_catalogue(root)[1]["status"], "PASS")

    def test_catalogue_metadata_change_requires_explicit_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_catalogue(root)
            self.fixture(root)
            expected, _ = catalogue_sync.inspect_catalogue(root)
            expected["skills"][0]["description"] = "Outdated description"
            (root / "catalogue/catalogue.json").write_text(json.dumps(expected))
            report = catalogue_sync.inspect_catalogue(root)[1]
            self.assertEqual(report["status"], "DRIFT")
            self.assertFalse(report["errors"])
            self.assertTrue(catalogue_sync.repair(root)["repaired"])
            self.assertEqual(catalogue_sync.inspect_catalogue(root)[1]["status"], "PASS")

    def test_portfolio_audit_never_executes_scripts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root, imported=True)
            self.fixture(root)
            result = portfolio.assess(root)
            self.assertEqual(result["status"], "OBSERVED")
            self.assertEqual(result["summary"]["skills"], 2)
            self.assertEqual(result["summary"]["imported"], 1)
            self.assertEqual(result["summary"]["script_files"], 1)
            self.assertTrue(any(x["code"] == "imported-unverified" for x in result["issues"]))
            self.assertIn("Review", portfolio.markdown(result))

    def test_portfolio_invalid_skill_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "skills" / "broken"
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text("no metadata")
            result = portfolio.assess(root.parents[1])
            self.assertEqual(result["status"], "FAIL")

    def test_cli_plan(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/automate.py"),
                               "plan", "--workflow", "weekly"],
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["executed"])

if __name__ == "__main__":
    unittest.main()
