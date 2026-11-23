"""Validate the advisory YAML 1.2/JSON-subset skill index without extra dependencies.

This tests metadata integrity only, not runtime invocation, host permissions,
agent routing accuracy or skill safety.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "agent-index.yaml"
VALID_MODES = {"read", "local_write", "local_execute", "external_write", "sensitive"}


def reject_duplicate_keys(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError(f"duplicate YAML/JSON key: {key}")
        values[key] = value
    return values


def path_exists_within_repo(path):
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    candidate = (ROOT / path).resolve()
    if not candidate.is_relative_to(ROOT.resolve()):
        return False
    return candidate.is_file()


class AgentIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(
            INDEX.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )

    def test_contract_and_authority_flags(self):
        idx = self.index
        self.assertEqual(idx["schema_version"], 1)
        self.assertEqual(idx["kind"], "shards.skills.agent-routing-index")
        self.assertEqual(idx["format"], "yaml-1.2-json-subset")
        authority = idx["authority"]
        self.assertFalse(authority["grants_tool_access"])
        self.assertFalse(authority["permits_automatic_execution"])
        self.assertTrue(authority["host_permissions_required"])
        self.assertEqual(
            authority["canonical"],
            ["AGENTS.md", "agent.md", "SECURITY.md"],
        )

    def test_references_resolve_to_existing_files(self):
        idx = self.index
        references = list(idx["authority"]["canonical"])
        references.extend(idx["guides"].values())
        for route in idx["routes"]:
            references.append(route["primary_path"])
            references.extend(route["helper_paths"])
            references.append(route["guide"])
        for ref in references:
            with self.subTest(ref=ref):
                self.assertTrue(path_exists_within_repo(ref), ref)

    def test_route_ids_skill_paths_and_effects(self):
        routes = self.index["routes"]
        required = {
            "review_pull_request", "debug_and_fix", "resume_or_handoff",
            "security_scope", "curated_local_check", "measure_host_adoption",
        }
        self.assertTrue(required.issubset({route["id"] for route in routes}))
        ids = set()
        for route in routes:
            with self.subTest(route=route["id"]):
                rid = route["id"]
                self.assertRegex(rid, r"^[a-z][a-z0-9_]*$")
                self.assertNotIn(rid, ids)
                ids.add(rid)
                for key in ("keywords", "evidence", "stop_on"):
                    values = route[key]
                    self.assertIsInstance(values, list, key)
                    self.assertGreater(len(values), 0, key)
                    self.assertTrue(all(isinstance(v, str) and v.strip() for v in values), key)
                for key in ("helper_skills", "helper_paths"):
                    values = route[key]
                    self.assertIsInstance(values, list, key)
                    self.assertTrue(all(isinstance(v, str) and v.strip() for v in values), key)
                if "additional_permissions" in route:
                    values = route["additional_permissions"]
                    self.assertIsInstance(values, list)
                    self.assertTrue(all(v in VALID_MODES for v in values))
                self.assertIn(route["mode"], VALID_MODES)
                # Routing metadata does not authorise external or sensitive work.
                self.assertIn(route["mode"], {"read", "local_write", "local_execute"})
                self.assertIsInstance(route["primary_skill"], str)
                self.assertTrue(route["primary_skill"].strip())
                self.assertEqual(
                    Path(route["primary_path"]).parent.name,
                    route["primary_skill"],
                )
                self.assertEqual(
                    Path(route["primary_path"]).name, "SKILL.md"
                )
                self.assertEqual(
                    len(route["helper_skills"]),
                    len(route["helper_paths"]),
                )
                for name, path in zip(route["helper_skills"], route["helper_paths"]):
                    self.assertEqual(Path(path).parent.name, name)

    def test_debug_route_requires_both_local_permissions(self):
        route = next(r for r in self.index["routes"] if r["id"] == "debug_and_fix")
        self.assertEqual(route["mode"], "local_execute")
        self.assertIn("local_write", route["additional_permissions"])

    def test_metadata_is_advisory_not_auto_execution(self):
        self.assertTrue(self.index["discovery"]["results_are_instructions_not_invocations"])
        for source in ("catalogue", "curated", "native_candidates"):
            self.assertIn(source, self.index["skill_types"])
        self.assertFalse(self.index["skill_types"]["catalogue"]["dispatchable"])
        self.assertTrue(self.index["selection_rules"])
        self.assertTrue(self.index["known_non_capabilities"])

    def test_entrypoints_link_to_the_index(self):
        for path in ("README.md", "AGENTS.md"):
            with self.subTest(path=path):
                self.assertIn(
                    "agent-index.yaml",
                    (ROOT / path).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
