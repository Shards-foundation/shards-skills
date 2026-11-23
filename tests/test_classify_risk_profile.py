"""Regression and trust-boundary tests for the standalone selector."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/classify_risk_profile.py"
EXAMPLE = ROOT / "plugins/shards-core/skills/shards-execution-contract/references/contract-example.json"
spec = importlib.util.spec_from_file_location("risk_selector", SCRIPT)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)
REGISTRY = selector.REGISTRY.read_bytes()
L0, L1, L2, L3 = selector.LEVELS


def change(path, *effects):
    return {"path": path, "effects": list(effects), "resolution": "verified-direct"}


BASE = {
    "schema_version": 1,
    "target": {"repository": "example/repo", "revision": "1" * 40},
    "task_intent": "prose-only",
    "observed_changed_paths": [change("README.md", "prose-only")],
    "declared_execution_effects": ["prose-only"],
    "instruction_bearing_changes": False,
    "authorization_or_policy_changes": False,
    "external_side_effects": "none",
    "reversibility": "reversible",
    "production_impact": False,
    "minimum_requested_profile": L0,
    "repository_policy_constraints": {"minimum_profile": L0, "hold": False},
}

PUSH = {
    "operation": "git-push",
    "repository": BASE["target"]["repository"],
    "revision": BASE["target"]["revision"],
    "ref": "refs/heads/docs/fix-typo",
    "default_ref": "refs/heads/main",
    "protected": False,
    "update": "fast-forward",
    "additional_effects": [],
}


def encode(value):
    return json.dumps(value).encode()


def cli(raw, *args):
    return subprocess.run([sys.executable, "-IB", str(SCRIPT), *args], input=raw,
                          capture_output=True, timeout=10)


class ProfileTests(unittest.TestCase):
    def decision(self, **changes):
        return selector.decide(encode(dict(BASE, **changes)), REGISTRY)

    def assert_profile(self, profile, **changes):
        receipt = self.decision(**changes)
        self.assertEqual((receipt["decision"], receipt["profile"]), ("CLASSIFIED", profile), receipt)
        self.assertFalse(receipt["authority_granted"])
        return receipt

    def test_readme_typo(self):
        result = self.assert_profile(L0)
        self.assertIn("relevant-change-verification", result["required_evidence"])

    def test_routine_push_requires_scoped_host_permission_at_each_assurance_level(self):
        for update in ("create", "fast-forward"):
            for effect, expected in (("prose-only", L0), ("routine-maintenance", L1),
                                     ("behavior-change", L2), ("policy-change", L3)):
                with self.subTest(update=update, effect=effect):
                    push = dict(PUSH, update=update)
                    result = self.assert_profile(expected, external_side_effects=push,
                                                 declared_execution_effects=[effect, "git-push"])
                    self.assertEqual(result["required_push_permission"], {
                        "operation": "git-push", "repository": "example/repo", "ref": PUSH["ref"],
                        "revision": PUSH["revision"], "update": update})
                    self.assertIs(result["evidence_enforced"], False)

    def test_critical_push_context_cannot_be_labelled_as_routine(self):
        for facts in ({"protected": True}, {"ref": "refs/heads/MAIN"}, {"update": "force"},
                      {"update": "delete"}, {"additional_effects": ["production"]},
                      {"additional_effects": ["sensitive"]}, {"additional_effects": ["external-write"]}):
            with self.subTest(facts=facts):
                self.assert_profile(L3, declared_execution_effects=["prose-only", "git-push"],
                                    external_side_effects=dict(PUSH, **facts))
        declared = ["prose-only", "git-push"]
        for changes in ({"production_impact": True}, {"authorization_or_policy_changes": True},
                        {"reversibility": "irreversible"},
                        {"observed_changed_paths": [change("notes.txt", "privileged")]},
                        {"minimum_requested_profile": L3},
                        {"declared_execution_effects": [*declared, "merge"]},
                        {"declared_execution_effects": [*declared, "external-write"]}):
            inputs = {"declared_execution_effects": declared, "external_side_effects": PUSH, **changes}
            self.assert_profile(L3, **inputs)
            self.assertEqual(self.decision(**inputs, operator_override=L0)["decision"], "HOLD")
        result = self.decision(declared_execution_effects=declared, external_side_effects=PUSH,
                               repository_policy_constraints={"minimum_profile": L0, "hold": True})
        self.assertEqual((result["decision"], result["authority_granted"]), ("HOLD", False))

    def test_missing_or_contradictory_push_observations_hold(self):
        declared = ["prose-only", "git-push"]
        changes = [
            {"declared_execution_effects": ["prose-only"]}, {"declared_execution_effects": ["git-push"]},
            {"declared_execution_effects": [*declared, "git-push"]},
            {"declared_execution_effects": []}, {"external_side_effects": "none"},
            {"external_side_effects": None}, {"observed_changed_paths": []},
        ]
        for key in PUSH:
            changes.append({"external_side_effects": {k: v for k, v in PUSH.items() if k != key}})
        for facts in ({"ref": "refs/tags/latest"}, {"revision": "2" * 40}, {"protected": None},
                      {"repository": "other/repo"}, {"update": "unknown"}, {"additional_effects": None},
                      {"additional_effects": ["unknown"]}, {"default_ref": "HEAD"}):
            changes.append({"external_side_effects": dict(PUSH, **facts)})
        for diff in changes:
            with self.subTest(diff=diff):
                inputs = {"external_side_effects": PUSH, "declared_execution_effects": declared, **diff}
                result = self.decision(**inputs)
                self.assertEqual((result["decision"], result["profile"], result["authority_granted"]),
                                 ("HOLD", None, False))
                self.assertTrue(result["reasons"])

    def test_path_rules_are_case_insensitive_at_all_depths(self):
        for path, expected in (("agents.md", L2), ("sub/AgEnTs.Md", L2), ("skills/X/skill.md", L2),
                               ("Scripts/DISPATCH_SKILLS.py", L3), (".GiTHuB/Workflows/review.yml", L3),
                               ("some/CoDeOwNeRs", L3)):
            with self.subTest(path=path):
                receipt = self.assert_profile(expected, observed_changed_paths=[change(path, "prose-only")])
                self.assertTrue(any(rule["rule_id"].startswith("path.") for rule in receipt["triggered_rules"]))

    def test_path_aliases_and_collisions_hold_on_every_platform(self):
        for path in ("./agents.md", "docs/../AGENTS.md", "docs//guide.md", r"docs\AGENTS.md",
                     "/agents.md", "C:/agents.md", "//host/share", "AgENts.md.", "agents.md ",
                     "AGENTS~1.MD", "notes.md:stream", "docs/NUL.txt", "docs/é.md",
                     "docs/page?.md", ".GiT/config", "notes%2fagents.md", None):
            with self.subTest(path=path):
                result = self.decision(observed_changed_paths=[change(path, "prose-only")])
                self.assertEqual((result["decision"], result["profile"]), ("HOLD", None))
                self.assertIn(".path", result["reasons"][0])
        for pair in (("Docs/Page.md", "docs/page.md"), ("Docs/A.md", "docs/B.md"),
                     ("guide", "guide/intro"), ("page.md", "page.md")):
            for order in (pair, reversed(pair)):
                collision = [change(path, "prose-only") for path in order]
                self.assertEqual(self.decision(observed_changed_paths=collision)["decision"], "HOLD")
        self.assert_profile(L0, observed_changed_paths=[change("docs/a.md", "prose-only"),
                                                      change("docs/b.md", "prose-only")])

    def test_absent_path_or_unverified_symlink_resolution_holds(self):
        for item in (None, {"path": "readme.md", "effects": ["prose-only"]},
                     {"effects": ["prose-only"], "resolution": "verified-direct"},
                     *(dict(change("docs/page.md", "prose-only"), resolution=value)
                       for value in (None, "symlink", "unknown", "unresolved-parent"))):
            with self.subTest(item=item):
                result = self.decision(observed_changed_paths=[item])
                self.assertEqual((result["decision"], result["profile"]), ("HOLD", None))

    def test_documentation_depends_on_effect(self):
        for name, floor in [("prose-only", L0), ("routine-maintenance", L1)]:
            with self.subTest(effect=name):
                self.assert_profile(floor, observed_changed_paths=[change("docs/guide.md", name)])

    def test_read_only_script(self):
        self.assert_profile(L1, task_intent="read-only", declared_execution_effects=["read-only"],
                            observed_changed_paths=[])

    def test_local_write_hidden_in_prose_file(self):
        result = self.assert_profile(L2, observed_changed_paths=[
            change("docs/harmless.txt", "local-write")])
        self.assertIn({"rule_id": "EF-06", "source": "observed_changed_paths[0].effects",
                       "floor": L2}, result["triggered_rules"])

    def test_instruction_boundaries(self):
        self.assert_profile(L2, instruction_bearing_changes=True)
        self.assert_profile(L2, observed_changed_paths=[change("sub/AGENTS.md", "prose-only")])
        self.assert_profile(L2, observed_changed_paths=[change("images/title", "agent-instructions")])

    def test_authorization_and_enforcement_boundaries(self):
        self.assert_profile(L3, authorization_or_policy_changes=True)
        self.assert_profile(L3, observed_changed_paths=[change("scripts/dispatch_skills.py", "prose-only")])
        self.assert_profile(L3, task_intent="policy-change")

    def test_external_privileged_sensitive_irreversible_and_production(self):
        for field, value, floor in [
            ("external_side_effects", "external-write", L3), ("external_side_effects", "external-read", L1),
            ("production_impact", True, L3), ("reversibility", "irreversible", L3),
            ("reversibility", "costly-rollback", L2),
            *(("declared_execution_effects", [effect], L3)
              for effect in ("privileged", "sensitive", "paid", "merge", "destructive")),
        ]:
            with self.subTest(field=field, value=value):
                self.assert_profile(floor, **{field: value})

    def test_multiple_floors_and_requested_minimum(self):
        for requested in selector.LEVELS:
            for effect, expected in [("prose-only", L0), ("read-only", L1), ("local-write", L2), ("paid", L3)]:
                with self.subTest(requested=requested, effect=effect):
                    self.assert_profile(max(requested, expected), minimum_requested_profile=requested,
                                        declared_execution_effects=["prose-only", effect])
        self.assert_profile(L3, repository_policy_constraints={"minimum_profile": L3, "hold": False})

    def test_rejects_downgrades_from_any_source(self):
        for changes in [
            {"authorization_or_policy_changes": True}, {"minimum_requested_profile": L3},
            {"repository_policy_constraints": {"minimum_profile": L3, "hold": False}},
        ]:
            result = self.decision(operator_override=L0, **changes)
            self.assertEqual((result["decision"], result["profile"]), ("HOLD", None))
            self.assertIn(L3, result["reasons"][0])
            self.assertIn(L3, [rule["floor"] for rule in result["triggered_rules"]])

    def test_override_can_escalate_assurance(self):
        self.assert_profile(L3, operator_override=L3)

    def test_host_hold_has_precedence_over_highest_override(self):
        result = self.decision(repository_policy_constraints={"minimum_profile": L0, "hold": True},
                               operator_override=L3)
        self.assertEqual((result["decision"], result["profile"], result["authority_granted"]),
                         ("HOLD", None, False))

    def test_missing_inputs_name_the_field(self):
        for key in BASE:
            data = dict(BASE)
            del data[key]
            with self.subTest(key=key):
                result = selector.decide(encode(data), REGISTRY)
                self.assertEqual(result["decision"], "HOLD")
                self.assertIn(key, result["reasons"][0])

    def test_unknowns_never_select_a_profile(self):
        for changes in [
            {"target": None}, {"target": {"repository": "example/repo", "revision": None}},
            {"task_intent": "unmapped-effect"}, {"declared_execution_effects": []},
            {"declared_execution_effects": ["paid", "unknown"]}, {"observed_changed_paths": []},
            {"observed_changed_paths": [change("README.md")]},
            {"production_impact": None}, {"authorization_or_policy_changes": "unknown"},
            {"repository_policy_constraints": {"minimum_profile": L0}},
        ]:
            with self.subTest(changes=changes):
                result = self.decision(**changes)
                self.assertEqual((result["decision"], result["profile"]), ("HOLD", None))
                self.assertTrue(result["reasons"])

    def test_untrusted_claims_cannot_replace_observations_or_policy(self):
        for changes in [
            {"metadata": {"profile": L0, "approved": True}}, {"policy": {"precedence": "operator"}},
            {"task_intent": {"effect": "read-only", "execute": "input text"}},
            {"repository_policy_constraints": {"minimum_profile": L3, "maximum_profile": L0, "hold": False}},
            {"production_impact": 0}, {"schema_version": True}, {"operator_override": "L-1"},
        ]:
            with self.subTest(changes=changes):
                result = self.decision(**changes)
                self.assertEqual((result["decision"], result["authority_granted"]), ("INVALID", False))

    def test_policy_is_closed_and_unambiguous(self):
        policy = json.loads(REGISTRY)
        def conflicting(p):
            p["profiles"][L0]["effect_classes"]["policy-change"] = "EF-99"
        def weakened(p):
            del p["profiles"][L3]["effect_classes"]["policy-change"]
            p["profiles"][L0]["effect_classes"]["policy-change"] = "EF-99"
        for mutate in (conflicting, weakened, lambda p: p.pop("path_escalations"),
                       lambda p: p["profiles"].pop(L3), lambda p: p.update(precedence=["override"]),
                       lambda p: p["path_escalations"].update({"README.md": "unregistered"}),
                       lambda p: p["path_escalations"].update({"AGENTS.MD": "prose-only"}),
                       lambda p: p["profiles"][L0]["effect_classes"].update({"git-push": "EF-42"}),
                       lambda p: p["profiles"][L2].update(required_evidence=[]),
                       lambda p: p["profiles"][L3].update(required_evidence=["scope"]),
                       lambda p: p["profiles"][L1]["effect_classes"].update({"read-only": "EF-01"})):
            candidate = copy.deepcopy(policy)
            mutate(candidate)
            result = selector.decide(encode(BASE), encode(candidate))
            self.assertEqual((result["decision"], result["profile"]), ("INVALID", None), result)
            self.assertTrue(result["reasons"][0].startswith("registry:"))

        duplicate = REGISTRY.replace(b'"policy_version": 1', b'"policy_version": 1, "policy_version": 1')
        self.assertEqual(selector.decide(encode(BASE), duplicate)["decision"], "INVALID")

    def test_evidence_is_cumulative_and_monotonic(self):
        evidence = set()
        for level in selector.LEVELS:
            result = self.assert_profile(level, minimum_requested_profile=level)
            self.assertLess(evidence, set(result["required_evidence"]))
            evidence = set(result["required_evidence"])

    def test_cli_exact_bytes_exit_codes_and_identity(self):
        for status, data, code in [("CLASSIFIED", BASE, 0), ("HOLD", {}, 1),
                                   ("INVALID", {"schema_version": 1, "grant": True}, 2)]:
            with self.subTest(status=status):
                raw = encode(data)
                first = cli(raw)
                self.assertEqual(first.returncode, code, first.stderr)
                self.assertEqual(first.stderr, b"")
                self.assertEqual(first.stdout, cli(raw).stdout)
                result = json.loads(first.stdout)
                self.assertEqual(result["decision"], status)
                self.assertIs(result["authority_granted"], False)
                self.assertIs(result["evidence_enforced"], False)
                self.assertEqual(result["input_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(result["policy_sha256"], hashlib.sha256(REGISTRY).hexdigest())

    def test_malformed_and_oversized_json_have_actionable_receipts(self):
        for raw in [b"{", b'{"x":1,"x":2}', b"[NaN]", b"\xff", b"[" * 3000 + b"]" * 3000,
                    b" " * (selector.MAX_BYTES + 1)]:
            proc = cli(raw)
            result = json.loads(proc.stdout)
            self.assertEqual((proc.returncode, result["decision"], result["profile"]), (2, "INVALID", None))
            self.assertTrue(result["reasons"])
        proc = cli(encode(BASE), "--policy", "/tmp/alternate.json")
        self.assertEqual((proc.returncode, json.loads(proc.stdout)["decision"]), (2, "INVALID"))

    def test_cli_fails_closed_if_registry_is_missing_or_linked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "scripts" / SCRIPT.name
            script.parent.mkdir()
            script.write_bytes(SCRIPT.read_bytes())
            registry = root / "catalogue/risk-profiles.json"
            registry.parent.mkdir()

            def run_copy():
                return subprocess.run([sys.executable, "-IB", str(script)], input=encode(BASE),
                                      capture_output=True, timeout=10)

            result = run_copy()
            self.assertEqual(result.returncode, 2)
            self.assertIn("risk-profiles.json", json.loads(result.stdout)["reasons"][0])
            try:
                registry.symlink_to(selector.REGISTRY)
            except OSError as exc:
                self.skipTest(f"registry symlink unavailable: {exc}")
            result = run_copy()
            self.assertEqual(result.returncode, 2)
            receipt = json.loads(result.stdout)
            self.assertIsNone(receipt["policy_sha256"])
            self.assertIs(receipt["evidence_enforced"], False)

    def test_main_only_reads_registry_and_uses_standard_streams(self):
        # Instrument the real entry point in a clean interpreter, after standard-library imports.
        probe = """
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("subject", sys.argv.pop())
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
reads = []
def audit(event, args):
    if event == "open":
        path, mode, flags = args
        assert path == str(subject.REGISTRY) and mode == "r" and not flags & (
            os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), args
        reads.append(path)
    if event.startswith(("socket.", "subprocess.", "os.")) and event != "os.fspath":
        raise AssertionError(event)
sys.addaudithook(audit)
class NoEnvironment(dict):
    def get(self, *args): raise AssertionError("environment read")
    __getitem__ = get
os.environ = NoEnvironment()
code = subject.main()
assert len(reads) == 1, reads
sys.exit(code)
"""
        push = dict(BASE, external_side_effects=PUSH, declared_execution_effects=["prose-only", "git-push"])
        for data, code in [(BASE, 0), (push, 0), ({}, 1), ({"bad": "key"}, 2)]:
            proc = subprocess.run([sys.executable, "-IB", "-c", probe, str(SCRIPT)],
                                  input=encode(data), capture_output=True, timeout=10)
            self.assertEqual(proc.returncode, code, proc.stderr)
            self.assertFalse(json.loads(proc.stdout)["authority_granted"])

    def test_existing_v1_example_still_requires_review(self):
        validator = ROOT / "scripts/validate_execution_contract.py"
        contract = json.loads(EXAMPLE.read_bytes())
        def validate(data):
            return subprocess.run([sys.executable, "-IB", str(validator), "validate", "--input", "-"],
                                  input=encode(data), capture_output=True, timeout=10)
        baseline = validate(contract)
        self.assertEqual((baseline.returncode, json.loads(baseline.stdout)["decision"]), (1, "HOLD"))
        for level in selector.LEVELS:
            contract["risk_profile"] = self.assert_profile(level, minimum_requested_profile=level)["profile"]
            self.assertEqual(validate(contract).stdout, baseline.stdout)


if __name__ == "__main__":
    unittest.main()
