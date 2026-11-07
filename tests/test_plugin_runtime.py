"""Executable skill and plugin regression tests (stdlib only)."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "plugins/shards-core"
RUNNER = PACKAGE / "scripts/run.py"
spec = importlib.util.spec_from_file_location("shards_core_runtime", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class PluginRuntimeTests(unittest.TestCase):
    def test_allowlisted_catalogue(self):
        data = runner.catalogue()
        self.assertEqual(data["count"], 11)
        self.assertEqual({x["name"] for x in data["skills"]}, {
            "shards-repository-health", "shards-skill-audit",
            "shards-release-gate", "shards-agent-handoff",
            "shards-automation-operator", "shards-catalogue-sync",
            "shards-skill-dispatch", "shards-a2a-harness", "shards-dual-channel",
            "shards-subagents", "shards-parallel-swarm"})

    def test_manifests(self):
        for name in ("plugin.json", ".claude-plugin/plugin.json",
                     ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"):
            data = json.loads((PACKAGE / name).read_text(encoding="utf-8"))
            self.assertEqual(data["name"], "shards-agent-core")
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(marketplace["plugins"][0]["source"]["path"], "./plugins/shards-core")

    def test_skill_instructions(self):
        for path in (PACKAGE / "skills").glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(runner.metadata(text)["name"], path.parent.name)
            for section in ("## Workflow", "## Execution", "## Output contract",
                            "## Verification", "## Failure handling"):
                self.assertIn(section, text)

    def test_static_audit_never_executes(self):
        result = runner.audit_skill(PACKAGE / "skills/shards-skill-audit")
        self.assertEqual(result["status"], "METADATA_PASS")
        self.assertFalse(result["executable"])

    def test_imported_review_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "example"
            p.mkdir()
            (p / "SKILL.md").write_text(
                "---\nname: example\ndescription: A sufficient imported testing skill description.\nstatus: review\n---\n# Example\n")
            (p / "UPSTREAM.md").write_text("Unreviewed")
            result = runner.audit_skill(p)
            self.assertEqual(result["status"], "REVIEW")
            self.assertFalse(result["executable"])

    def test_audit_blocks_traversal_link(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "example"
            p.mkdir()
            (p / "SKILL.md").write_text(
                "---\nname: example\ndescription: A sufficient testing skill description.\n---\n[bad](../x.md)")
            self.assertEqual(runner.audit_skill(p)["status"], "BLOCK")

    def test_release_holds_without_execution(self):
        report = runner.release_check(ROOT, False, False)
        self.assertEqual(report["decision"], "HOLD")
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["production_verified"])

    def test_release_requires_explicit_trust(self):
        with self.assertRaises(ValueError):
            runner.release_check(ROOT, True, False)

    def test_checkpoint_validation(self):
        data = dict(goal="task", repo="repo", branch="main", commit="abc",
                    completed=[], decisions=[], evidence=[], blockers=[], pending=[])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            path.write_text(json.dumps(data))
            self.assertEqual(runner.validate_handoff(path)["goal"], "task")
            data["access_token"] = "redacted"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                runner.validate_handoff(path)

    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            runner.write_exclusive(path, "{}")
            with self.assertRaises(FileExistsError):
                runner.write_exclusive(path, "{}")

    def test_cli_catalogue(self):
        proc = subprocess.run([sys.executable, str(RUNNER), "catalogue"],
                              text=True, capture_output=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["count"], 11)

    def test_first_party_workflow_adapters(self):
        cases = (
            ("release-readiness", "--repo", ".", 1),
            ("skill-supply-chain-audit", "--path", "skills/release-readiness", 0),
            ("writing-skill-packages", "--path", "skills/release-readiness", 0),
        )
        for name, switch, value, expected in cases:
            path = ROOT / "skills" / name / "scripts" / "run.py"
            with self.subTest(name=name):
                result = subprocess.run(
                    [sys.executable, str(path), switch, value],
                    cwd=ROOT, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn("workflow", json.loads(result.stdout))

if __name__ == "__main__":
    unittest.main()
