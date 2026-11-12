"""Structural and adoption contracts for the first-party Shards security suite."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    "shards-sec-intake",
    "shards-sec-vibecoding-gate",
    "shards-sec-business-threat-model",
    "shards-sec-identity-access",
    "shards-sec-secrets-keys",
    "shards-sec-web-api",
    "shards-sec-cloud-devsecops",
    "shards-sec-supply-chain",
    "shards-sec-vulnerability-management",
    "shards-sec-incident-response",
    "shards-sec-detection-response",
    "shards-sec-human-fraud",
    "shards-sec-privacy-dpia",
    "shards-sec-governance-policy",
    "shards-sec-jurisdiction-scope",
    "shards-sec-compliance-evidence",
    "shards-sec-third-party-risk",
    "shards-sec-resilience-recovery",
    "shards-sec-fintech-payments",
    "shards-sec-crypto-custody",
    "shards-sec-defi-protocol",
    "shards-sec-ai-agent-boundaries",
    "shards-sec-prompt-injection",
    "shards-sec-authorized-testing",
    "shards-sec-crypto-fincrime",
}

class SecuritySuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = json.loads((ROOT / "catalogue/catalogue.json").read_text())
        cls.controls = json.loads((ROOT / "catalogue/shards-security-controls.json").read_text())
        cls.readme = (ROOT / "README.md").read_text()

    def test_all_25_workflow_descriptors_exist(self):
        actual = {p.parent.name for p in (ROOT / "skills").glob("shards-sec-*/SKILL.md")}
        self.assertEqual(actual, NAMES)

    def test_workflows_are_first_party_structured_and_safe(self):
        content_fingerprints = set()
        for slug in sorted(NAMES):
            folder = ROOT / "skills" / slug
            source = (folder / "SKILL.md").read_text()
            front = source.split("---", 2)[1]
            self.assertIn("name: " + slug + "\n", front)
            self.assertIn("author: Shards Foundation\n", front)
            self.assertIn("status: draft\n", front)
            self.assertIn("license: MIT\n", front)
            for heading in ("## Trigger", "## Required inputs", "## Workflow",
                            "## Output contract", "## Verification",
                            "## Failure handling", "## Authority and safe use"):
                self.assertIn(heading, source, slug)
            self.assertGreaterEqual(len(re.findall(r"(?m)^\d+\. ", source)), 6, slug)
            self.assertFalse((folder / "UPSTREAM.md").exists())
            content_fingerprints.add(source.split("## Workflow\n", 1)[1].split("\n## Output contract", 1)[0])
        self.assertEqual(len(content_fingerprints), 25)

    def test_catalogue_lists_all_packages_consistently(self):
        by_name = {item["name"]: item for item in self.catalogue["skills"]}
        self.assertTrue(NAMES.issubset(by_name))
        self.assertEqual(len(self.catalogue["skills"]), self.catalogue["skill_count"])
        self.assertEqual(self.catalogue["skill_count"], len(self.catalogue["skill_paths"]))
        for name in NAMES:
            item = by_name[name]
            self.assertEqual(item["path"], "skills/" + name)
            self.assertEqual(item["status"], "draft")
            self.assertIn(item["category"], {"security", "finance", "blockchain", "agents"})

    def test_control_profiles_cover_all_sectors(self):
        profiles = set(self.controls["profiles"])
        self.assertEqual(profiles, {"base", "web", "ai", "crypto", "fintech",
                                    "cloud", "privacy", "governance"})
        self.assertEqual(self.controls["schema_version"], 1)
        entries = self.controls["controls"]
        self.assertEqual(len(entries), 45)
        self.assertEqual(len({c["id"] for c in entries}), 45)
        self.assertIn("critical", {c["severity"] for c in entries})

    def test_readme_linked_first_party_skills(self):
        for name in NAMES:
            self.assertIn("skills/" + name + "/SKILL.md", self.readme, name)
        for name in ("shards-repository-health", "shards-skill-dispatch",
                     "shards-parallel-swarm", "shards-a2a-harness"):
            self.assertIn(name, self.readme)
        self.assertIn("PR #16", self.readme)
        self.assertIn("not yet merged", self.readme)

    def test_sources_and_operator_instructions_present(self):
        sources = (ROOT / "docs/security-frameworks.md").read_text()
        operator = (ROOT / "docs/security-assurance.md").read_text()
        for source in ("nist.gov", "asvs.owasp.org", "ico.org.uk", "fatf-gafi.org", "esma.europa.eu"):
            self.assertIn(source, sources)
        for signal in ("REPORTED_PASS", "BLOCKED", "REVIEW_READY_NOT_CERTIFIED", "not automatically"):
            self.assertIn(signal, operator)

if __name__ == "__main__":
    unittest.main()
