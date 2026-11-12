"""Tests for read-only skills catalogue discovery and trust labels."""
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import search_skills as discovery


class SkillSearchTests(unittest.TestCase):
    def _fixture(self, root, records):
        folder = root / "catalogue"
        folder.mkdir()
        (folder / "catalogue.json").write_text(json.dumps({
            "schema_version": 1, "skill_count": len(records), "skills": records
        }), encoding="utf-8")

    def _entry(self, name, description="Use for code review", status="review"):
        return {"name": name, "path": "skills/" + name,
                "description": description, "category": "engineering",
                "status": status}

    def test_exact_name_outscores_description_only(self):
        records = [
            {**self._entry("code-review", "Safe tests and reviews"),
             "source": "catalogue", "execution": "not-dispatchable"},
            {**self._entry("other-workflow", "This skill helps with code review"),
             "source": "catalogue", "execution": "not-dispatchable"},
        ]
        matches = discovery.rank(records, "code review")
        self.assertEqual(matches[0]["name"], "code-review")
        self.assertGreater(matches[0]["score"], matches[1]["score"])

    def test_catalogue_metadata_not_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root, [self._entry("code-review")])
            entries = discovery.catalogue_entries(root)
            self.assertEqual(entries[0]["execution"], "not-dispatchable")
            self.assertEqual(entries[0]["source"], "catalogue")

    def test_reject_path_traversal_and_duplicates(self):
        for records in (
            [dict(self._entry("code-review"), path="../secrets")],
            [self._entry("code-review"), self._entry("code-review")],
            [dict(self._entry("code-review"), status="curated")],
            [dict(self._entry("code-review"), status=[])],
            [dict(self._entry("code-review"), status={})],
            [dict(self._entry("code-review"), status=None)],
            [dict(self._entry("code-review"), status=42)],
        ):
            with self.subTest(records=records):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self._fixture(root, records)
                    with self.assertRaises(ValueError):
                        discovery.catalogue_entries(root)

    def test_reject_count_mismatch_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._fixture(root, [self._entry("code-review")])
            catalogue = root / "catalogue" / "catalogue.json"
            original = catalogue.read_text(encoding="utf-8")
            document = json.loads(original)
            document["skill_count"] = 99
            catalogue.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "count"):
                discovery.catalogue_entries(root)

    def test_real_catalogue_has_separate_trust_classes(self):
        entries = discovery.catalogue_entries()
        self.assertGreater(len(entries), 200)
        self.assertTrue(all(entry["execution"] == "not-dispatchable" for entry in entries))
        curated = discovery.curated_entries()
        self.assertEqual(len(curated), len(discovery.REGISTRY))
        self.assertTrue(all(entry["execution"] == "dispatcher-plan-required"
                            for entry in curated))

    def test_cli_finds_curated_skill_without_running_it(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/search_skills.py"),
             "--query", "repository health", "--status", "curated", "--limit", "5"],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["candidate_count"], len(discovery.catalogue_entries()) +
                         len(discovery.REGISTRY))
        self.assertIn("shards-repository-health",
                      [item["name"] for item in result["results"]])
        self.assertIn("metadata-only", result["trust_boundary"])

    def test_curated_metadata_comes_only_from_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "shards-repository-health"
            descriptor = root / "plugins" / "shards-core" / "skills" / name / "SKILL.md"
            descriptor.parent.mkdir(parents=True)
            descriptor.write_text(
                "---\nname: " + name + "\ndescription: Trusted description\n---\n"
                "description: Body text must not override metadata\n", encoding="utf-8")
            with mock.patch.object(discovery, "REGISTRY", {name: object()}):
                entries = discovery.curated_entries(root)
                self.assertEqual(entries[0]["description"], "Trusted description")

    def test_curated_rejects_missing_duplicate_and_unclosed_frontmatter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "shards-repository-health"
            descriptor = root / "plugins" / "shards-core" / "skills" / name / "SKILL.md"
            descriptor.parent.mkdir(parents=True)
            invalid = (
                "Some body\nname: " + name + "\ndescription: Spoofed\n",
                "---\nname: " + name + "\ndescription: First\n"
                "description: Second\n---\n",
                "---\nname: " + name + "\ndescription: Missing close\n",
                "---\nname: other\ndescription: Wrong\n---\n",
            )
            with mock.patch.object(discovery, "REGISTRY", {name: object()}):
                for content in invalid:
                    with self.subTest(content=content):
                        descriptor.write_text(content, encoding="utf-8")
                        with self.assertRaises(ValueError):
                            discovery.curated_entries(root)

    def test_curated_rejects_duplicate_name_and_frontmatter_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "shards-repository-health"
            descriptor = root / "plugins" / "shards-core" / "skills" / name / "SKILL.md"
            descriptor.parent.mkdir(parents=True)
            with mock.patch.object(discovery, "REGISTRY", {name: object()}):
                valid = "---\nname: " + name + "\ndescription: Healthy\n---\n"
                descriptor.write_text(valid, encoding="utf-8")
                self.assertEqual(discovery.curated_entries(root)[0]["description"], "Healthy")
                invalid = [
                    "---\nname: " + name + "\nname: " + name +
                    "\ndescription: Duplicate\n---\n",
                    "---\nname: " + name + "\ndescription: " +
                    "x" * 8200 + "\n---\n",
                    "---\nname: " + name + "\ndescription: Healthy\n" +
                    ("# filler\n" * 99) + "---\n",
                ]
                for content in invalid:
                    with self.subTest(length=len(content)):
                        descriptor.write_text(content, encoding="utf-8")
                        with self.assertRaises(ValueError):
                            discovery.curated_entries(root)
                # Exactly 100 lines before the closing delimiter remains accepted.
                descriptor.write_text(
                    "---\nname: " + name + "\ndescription: Healthy\n" +
                    ("# filler\n" * 97) + "---\n", encoding="utf-8")
                self.assertEqual(len(discovery.curated_entries(root)), 1)

    def test_short_query_matches_without_losing_abbreviations(self):
        for term, name in (("ci", "ci-cd-automation"), ("ai", "ai-agent-boundaries"),
                           ("ui", "ui-engineering"), ("go", "go-programming")):
            with self.subTest(term=term):
                entry = {**self._entry(name, "Reviewed workflow"),
                         "execution": "not-dispatchable"}
                found = discovery.rank([entry], term)
                self.assertEqual([match["name"] for match in found], [name])

    def test_short_acronym_survives_mixed_task_query(self):
        for query, name in (("setup ci pipeline", "ci-cd-automation"),
                            ("improve ai workflows", "ai-agent-boundaries"),
                            ("build ui dashboard", "ui-engineering")):
            with self.subTest(query=query):
                entry = {**self._entry(name, "Reviewed workflow"),
                         "execution": "not-dispatchable"}
                found = discovery.rank([entry], query)
                self.assertEqual([item["name"] for item in found], [name])

    def test_negated_broker_actions_do_not_rank_broker_skill(self):
        # Real user task: copying third-party skills, NOT connecting a broker.
        query = ("Import the day-trading skill files into the catalogue; "
                 "do not connect a broker or place orders.")
        entries = discovery.catalogue_entries() + discovery.curated_entries()
        results = discovery.rank(entries, query)
        names = [item["name"] for item in results]
        # The public CLI shows the first ten entries by default. Broad
        # lexical matches far below the shortlist are not recommendations.
        self.assertNotIn("trader-broker", names[:10])
        self.assertIn("skill-supply-chain-audit", names)

    def test_negative_only_instruction_does_not_trigger_skills(self):
        entries = discovery.catalogue_entries()
        self.assertEqual(discovery.rank(entries, "Do not connect a broker or place orders."), [])

    def test_positive_broker_request_still_retrievable(self):
        entries = discovery.catalogue_entries()
        results = discovery.rank(entries, "Connect a broker and place approved orders")
        self.assertIn("trader-broker", [item["name"] for item in results[:3]])
        match = next(item for item in results if item["name"] == "trader-broker")
        self.assertEqual(match["execution"], "not-dispatchable")

    def test_negated_clause_does_not_erase_following_positive_task(self):
        entries = [
            {**self._entry("trader-broker",
                           "Connect a broker, execute and place orders"),
             "execution": "not-dispatchable"},
            {**self._entry("skill-supply-chain-audit",
                           "Audit third-party skill before importing or installing"),
             "execution": "not-dispatchable"},
        ]
        results = discovery.rank(
            entries, "Don't place broker orders; audit this third-party skill before installing")
        self.assertEqual([r["name"] for r in results], ["skill-supply-chain-audit"])

    def test_inflections_match_base_forms_with_final_e(self):
        for query, base in (("releases", "release"), ("images", "image"),
                            ("packages", "package"), ("updated", "update"),
                            ("creating", "create")):
            with self.subTest(query=query):
                entry = {**self._entry("target-workflow", "Use for " + base + " analysis"),
                         "execution": "not-dispatchable"}
                self.assertEqual(discovery.rank([entry], query)[0]["name"], "target-workflow")

    def test_bad_query_limit_rejected(self):
        with self.assertRaises(ValueError):
            discovery.rank([], "!?!")
        with self.assertRaises(ValueError):
            discovery.discover("skill", limit=101)


if __name__ == "__main__":
    unittest.main()
