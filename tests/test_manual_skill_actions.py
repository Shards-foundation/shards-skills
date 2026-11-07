"""Contract checks for manually dispatched, read-only GitHub skill execution."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dispatch_skills as dispatcher

WORKFLOW = ROOT / ".github/workflows/run-curated-skill.yml"
ALLOWED = {
    "shards-repository-health", "shards-catalogue-sync", "shards-skill-dispatch",
    "shards-a2a-harness", "shards-dual-channel",
    "shards-subagents", "shards-parallel-swarm",
}


class ManualSkillActionTests(unittest.TestCase):
    def test_manual_only_with_read_only_token_and_nonpersistent_credentials(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("timeout-minutes: 7", text)

    def test_ui_choices_equal_shell_allowlist(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"^\s+options:\n(?P<options>(?:\s+- shards-[a-z0-9-]+\n)+)",
            content, re.MULTILINE)
        self.assertIsNotNone(match)
        choices = set(re.findall(r"shards-[a-z0-9-]+", match.group("options")))
        guard = re.search(r"^\s+(shards-[a-z0-9-]+(?:\|shards-[a-z0-9-]+)+)\) ;;",
                          content, re.MULTILINE)
        self.assertIsNotNone(guard)
        guarded = set(guard.group(1).split("|"))
        self.assertEqual(choices, ALLOWED)
        self.assertEqual(guarded, choices)
        self.assertTrue(all(dispatcher.REGISTRY[skill][0] == "read-only"
                            for skill in choices))

    def test_workflow_uses_plan_pinning_and_saves_evidence(self):
        content = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('SHARDS_SKILL: ${{ inputs.skill }}', content)
        self.assertIn('scripts/dispatch_skills.py plan --skill "$SHARDS_SKILL"', content)
        self.assertIn('--expect-plan-sha256 "$PLAN_SHA"', content)
        self.assertIn("--save-receipt", content)
        self.assertIn("GITHUB_STEP_SUMMARY", content)
        self.assertIn("actions/upload-artifact@v4", content)
        self.assertIn("reports/dispatch/", content)

    def test_each_allowlisted_skill_produces_a_valid_pinned_plan(self):
        def fake(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")
        for skill in sorted(ALLOWED):
            with self.subTest(skill=skill):
                plan = dispatcher.describe(skill)
                self.assertEqual(plan["effect"], "read-only")
                self.assertEqual(dispatcher._plan_fingerprint(plan), plan["plan_sha256"])
                receipt = dispatcher.run(plan, executor=fake)
                self.assertEqual(receipt["observation"]["status"], "pass")
                self.assertEqual(receipt["plan_sha256"], plan["plan_sha256"])


if __name__ == "__main__":
    unittest.main()
