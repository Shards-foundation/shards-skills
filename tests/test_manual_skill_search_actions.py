"""Regression contract for the manual, metadata-only skill-search Action."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/search-shards-skills.yml"


def choices(content: str, field: str, next_field: str | None = None) -> set[str]:
    start = f"      {field}:\n"
    part = content.split(start, 1)[1]
    if next_field:
        part = part.split(f"      {next_field}:\n", 1)[0]
    else:
        part = part.split("\npermissions:", 1)[0]
    return {line.strip()[2:].strip("'") for line in part.splitlines()
            if line.strip().startswith("- ")}


class ManualSearchActionTests(unittest.TestCase):
    def test_manual_read_only_credential_safe(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertNotIn("push:", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("timeout-minutes: 5", text)
        self.assertNotIn("pip install", text)

    def test_filters_are_supported_by_actual_catalogue(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        data = json.loads((ROOT / "catalogue/catalogue.json").read_text(encoding="utf-8"))
        from_file = choices(text, "category", "status")
        self.assertEqual(from_file, set(data["categories"]) | {"all", "curated"})
        self.assertEqual(choices(text, "status", "limit"),
                         {"all", "draft", "review", "verified", "deprecated", "curated"})
        self.assertEqual(choices(text, "limit"), {"5", "10", "20", "50"})

    def test_shell_inputs_are_environment_bound_and_quoted(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('SHARDS_QUERY: ${{ inputs.query }}', text)
        self.assertIn('SHARDS_STATUS: ${{ inputs.status }}', text)
        self.assertIn('args=(--query "$SHARDS_QUERY" --limit "$SHARDS_LIMIT")', text)
        self.assertIn('python scripts/search_skills.py "${args[@]}"', text)
        self.assertNotIn('eval ', text)
        self.assertNotIn('bash -c', text)

    def test_artifact_and_summary_not_execution(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("GITHUB_STEP_SUMMARY", text)
        self.assertIn("reports/search/results.json", text)
        self.assertIn("retention-days: 7", text)
        self.assertNotIn("dispatch_skills.py run", text)
        self.assertNotIn("--execute", text)

    def test_real_metadata_search_with_filters(self):
        proc = subprocess.run([
            sys.executable, str(ROOT / "scripts/search_skills.py"),
            "--query", "blockchain", "--category", "blockchain", "--limit", "5",
        ], capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertGreater(data["match_count"], 0)
        self.assertTrue(all(item["category"] == "blockchain" for item in data["results"]))
        self.assertTrue(all(item["execution"] == "not-dispatchable"
                            for item in data["results"]))


if __name__ == "__main__":
    unittest.main()
