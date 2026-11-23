"""Regression coverage for safe, automated skill maintenance."""
import importlib.util
import json
import os
import shutil
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
        self.assertEqual(data["pending_steps"], list(automate.WORKFLOWS["verify"][1:]))

    def test_missing_later_step_preserves_previous_and_following_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for step in ("catalogue-check", "plugin-integrity", "plugin-audit"):
                path = root / automate.STEPS[step][0][0]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("print('finished')\n", encoding="utf-8")
            with patch.object(automate, "ROOT", root):
                result = automate.run_workflow("quick", execute=True)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["failed_steps"], ["skill-metadata"])
        self.assertEqual([s["status"] for s in result["steps"]],
                         ["passed", "error", "passed", "passed"])
        self.assertIn("scripts/validate_skills.py", result["steps"][1]["error"])

    def test_unknown_later_step_prevents_any_launch(self):
        with patch.dict(automate.WORKFLOWS, {"quick": ("catalogue-check", "unknown")}):
            with patch.object(automate.subprocess, "run") as launch:
                with self.assertRaisesRegex(ValueError, "Untrusted step"):
                    automate.run_workflow("quick", execute=True)
        launch.assert_not_called()

    def test_invalid_utf8_preserves_nonzero_child_exit_and_redaction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / automate.STEPS["catalogue-check"][0][0]
            target.parent.mkdir()
            token = "ghp_" + "a" * 30
            target.write_text(
                "import os, sys\n"
                "if 'GITHUB_TOKEN' in os.environ:\n    sys.exit(9)\n"
                f"sys.stderr.buffer.write({token.encode()!r} + bytes([255]))\n"
                "sys.exit(3)\n", encoding="utf-8")
            with (patch.object(automate, "ROOT", root),
                  patch.dict(os.environ, {"GITHUB_TOKEN": token})):
                result = automate.run_workflow("quick", execute=True, fail_fast=True)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["steps"][0]["exit_code"], 3)
        self.assertEqual(result["steps"][0]["stderr_tail"], "[REDACTED]\ufffd")

    def test_real_subprocess_timeout_fails_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "scripts/catalogue_sync.py"
            target.parent.mkdir()
            target.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
            with (patch.object(automate, "ROOT", root),
                  patch.dict(automate.STEPS, {"catalogue-check": (["scripts/catalogue_sync.py"], 0.1)})):
                result = automate.run_workflow("quick", execute=True, fail_fast=True)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["steps"][0]["status"], "timeout")
        self.assertIsNone(result["steps"][0]["exit_code"])

    def test_timeout_preserves_only_decoded_redacted_tails(self):
        token = "ghp_" + "a" * 30
        cases = (
            (b"x" * 2500 + b"\xff " + token.encode(),
             b"diagnostic\n-----BEGIN PRIVATE KEY-----\nunfinished",
             "x" * 2388 + "\ufffd [REDACTED]", "diagnostic\n[REDACTED]"),
            (None, "text " + token, "", "text [REDACTED]"),
        )
        for stdout, stderr, out_tail, err_tail in cases:
            with self.subTest(stdout_type=type(stdout)):
                def timeout(argv, **kwargs):
                    raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=stdout, stderr=stderr)

                result = automate.run_workflow("quick", execute=True, fail_fast=True,
                                                run_command=timeout)
                self.assertEqual(result["status"], "fail")
                self.assertEqual(result["failed_steps"], ["catalogue-check"])
                entry, = result["steps"]
                self.assertEqual(entry["status"], "timeout")
                self.assertIsNone(entry["exit_code"])
                self.assertEqual(entry["stdout_tail"], out_tail)
                self.assertEqual(entry["stderr_tail"], err_tail)

    def test_start_failure_is_recorded(self):
        with patch.object(automate.sys, "executable", str(ROOT / "absent-python")):
            result = automate.run_workflow("quick", execute=True, fail_fast=True)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["steps"][0]["status"], "error")
        self.assertIsNone(result["steps"][0]["exit_code"])

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
            second = automate.write_report(Path(temp), {"status": "fail"})
            self.assertNotEqual(first, second)
            self.assertEqual(json.loads(first.read_text())["status"], "pass")

    def test_interrupted_report_never_publishes_partial_json(self):
        def interrupt(report, stream, **kwargs):
            stream.write('{"status":')
            stream.flush()
            self.assertEqual(list(directory.glob("automation-*.json")), [])
            raise KeyboardInterrupt

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with patch.object(automate.json, "dump", side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    automate.write_report(directory, {"status": "pass"})
            self.assertEqual(list(directory.iterdir()), [])

    def test_report_collision_does_not_replace_existing_receipt(self):
        moment = automate.datetime.now(automate.timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with patch.object(automate, "datetime") as clock:
                clock.now.return_value = moment
                first = automate.write_report(directory, {"status": "pass"})
                with self.assertRaises(FileExistsError):
                    automate.write_report(directory, {"status": "fail"})
            self.assertEqual(list(directory.iterdir()), [first])
            self.assertEqual(json.loads(first.read_text(encoding="utf-8")), {"status": "pass"})

    def test_report_write_failure_preserves_workflow_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "file-instead-of-directory"
            output.touch()
            proc = self.maintenance("run", "--workflow", "weekly", "--output-dir", str(output))
            self.assertEqual(proc.returncode, 2, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["workflow_status"], "pass")
            self.assertEqual(result["completed"], 5)
            self.assertEqual(output.read_bytes(), b"")

    def test_catalogue_check_rejects_duplicate_or_malformed_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_catalogue(root)
            self.fixture(root)
            expected, _ = catalogue_sync.inspect_catalogue(root)
            catalogue = root / "catalogue/catalogue.json"
            entry = expected["skills"][0]
            for update, diagnostic in (
                    ({"skills": [entry, entry]}, "Duplicate catalogue skill path"),
                    ({"skills": [entry, {}]}, "missing a string path"),
                    ({"skills": [entry, {"path": []}]}, "missing a string path"),
                    ({"skills": None}, "skills must be a list"),
                    ({"schema_version": 2}, "Unsupported catalogue schema"),
                    ({"skill_count": True}, "skill_count must be an integer"),
                    ({"skill_paths": [1]}, "skill_paths must be a list of strings")):
                with self.subTest(update=update):
                    catalogue.write_text(json.dumps(dict(expected, **update)), encoding="utf-8")
                    proc = subprocess.run(
                        [sys.executable, str(ROOT / "scripts/catalogue_sync.py"),
                         "--check", "--root", temp], capture_output=True, text=True, timeout=15)
                    self.assertEqual(proc.returncode, 2, proc.stderr or proc.stdout)
                    report = json.loads(proc.stdout)
                    self.assertEqual(report["status"], "ERROR")
                    self.assertIn(diagnostic, report["error"])

    def test_catalogue_check_rejects_invalid_required_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_catalogue(root)
            self.fixture(root)
            expected, _ = catalogue_sync.inspect_catalogue(root)
            entry, = expected["skills"]
            catalogue = root / "catalogue/catalogue.json"
            for field, value in (
                    ("name", None), ("name", 42), ("name", "Other"),
                    ("name", "other"), ("description", None), ("description", " "),
                    ("description", []), ("category", None), ("category", "\t"),
                    ("category", 42), ("status", None), ("status", ["draft"]),
                    ("status", "unknown")):
                with self.subTest(field=field, value=value):
                    invalid = dict(entry)
                    if value is None:
                        del invalid[field]
                    else:
                        invalid[field] = value
                    catalogue.write_text(json.dumps(dict(expected, skills=[invalid])),
                                         encoding="utf-8")
                    proc = subprocess.run(
                        [sys.executable, str(ROOT / "scripts/catalogue_sync.py"),
                         "--check", "--root", temp], capture_output=True, text=True, timeout=15)
                    self.assertEqual(proc.returncode, 2, proc.stderr or proc.stdout)
                    self.assertEqual(json.loads(proc.stdout)["status"], "ERROR")

    def test_catalogue_commands_reject_invalid_source_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "catalogue").mkdir()
            for name in ("validate_skills.py", "catalogue_sync.py", "build_catalogue.py"):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)

            descriptor = root / "skills/example-skill/SKILL.md"
            descriptor.parent.mkdir(parents=True)
            valid_source = (
                "---\nname: example-skill\n"
                "description: A deterministic fixture for catalogue validation.\n"
                "---\n## Workflow\nRead one local descriptor and check its metadata.\n"
                "## Output contract\nRecord the resulting catalogue entry.\n"
                "## Verification\nCompare the generated fields with the descriptor.\n"
                "## Failure handling\nReport malformed source metadata.\n"
            )
            descriptor.write_text(valid_source, encoding="utf-8")
            catalogue = root / "catalogue/catalogue.json"
            build = subprocess.run([sys.executable, str(root / "scripts/build_catalogue.py")],
                                   capture_output=True, text=True, timeout=15)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            original = catalogue.read_bytes()
            entry, = json.loads(original)["skills"]
            self.assertEqual(entry["status"], "draft")
            self.assertEqual(entry["category"], "uncategorised")

            for metadata, diagnostic in (
                    ("status: experimental", "Expected status"),
                    ("category:", "Expected a nonempty category string")):
                descriptor.write_text(valid_source.replace("\n---\n", f"\n{metadata}\n---\n", 1),
                                      encoding="utf-8")
                for command in (("validate_skills.py",), ("catalogue_sync.py", "--check"),
                                ("build_catalogue.py",)):
                    with self.subTest(metadata=metadata, script=command[0]):
                        proc = subprocess.run(
                            [sys.executable, str(root / "scripts" / command[0]), *command[1:]],
                            capture_output=True, text=True, timeout=15)
                        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                        self.assertIn(diagnostic, proc.stdout + proc.stderr)
                        self.assertEqual(catalogue.read_bytes(), original)
                catalogue.write_bytes(original)

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
        proc = self.maintenance("plan", "--workflow", "weekly")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["executed"])

    @staticmethod
    def maintenance(*args, root=ROOT):
        return subprocess.run([sys.executable, str(root / "scripts/automate.py"), *args],
                              capture_output=True, text=True, timeout=30)

    def test_weekly_plan_run_and_saved_receipt_agree(self):
        plan = json.loads(self.maintenance("plan", "--workflow", "weekly").stdout)
        revision = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True, timeout=5)
        with tempfile.TemporaryDirectory() as temp:
            proc = self.maintenance("run", "--workflow", "weekly", "--output-dir", temp)
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            result = json.loads(proc.stdout)
            receipt = json.loads(Path(result.pop("report_path")).read_text(encoding="utf-8"))
            self.assertEqual(receipt, result)
        self.assertEqual(receipt["commit"], revision.stdout.strip() if revision.returncode == 0 else None)
        self.assertEqual(receipt["commit"], plan["commit"])
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(receipt["completed"], receipt["total"])
        self.assertEqual(receipt["pending_steps"], [])
        self.assertEqual([(s["id"], s["command"], s["exit_code"]) for s in receipt["steps"]],
                         [(s["id"], s["argv"], 0) for s in plan["steps"]])

    def test_weekly_malformed_catalogue_writes_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            for name in ("automate.py", "catalogue_sync.py", "validate_skills.py"):
                shutil.copyfile(ROOT / "scripts" / name, root / "scripts" / name)
            self.make_catalogue(root)
            (root / "catalogue/catalogue.json").write_text("{", encoding="utf-8")
            proc = self.maintenance("run", "--workflow", "weekly", "--fail-fast",
                                    "--output-dir", temp, root=root)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            result = json.loads(proc.stdout)
            receipt = json.loads(Path(result.pop("report_path")).read_text(encoding="utf-8"))
            self.assertEqual(receipt, result)
            self.assertEqual(receipt["status"], "fail")
            self.assertEqual(receipt["failed_steps"], ["catalogue-check"])
            self.assertEqual(receipt["pending_steps"], list(automate.WORKFLOWS["weekly"][1:]))
            self.assertEqual(receipt["steps"][0]["exit_code"], 2)
            self.assertIn("Expecting property name", receipt["steps"][0]["stdout_tail"])

if __name__ == "__main__":
    unittest.main()
