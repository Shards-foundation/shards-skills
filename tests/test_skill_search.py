"""Tests for read-only skills catalogue discovery and trust labels."""
import json
import subprocess
import sys
import tempfile
import unittest
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

    def test_bad_query_limit_rejected(self):
        with self.assertRaises(ValueError):
            discovery.rank([], "!?!")
        with self.assertRaises(ValueError):
            discovery.discover("skill", limit=101)


if __name__ == "__main__":
    unittest.main()
