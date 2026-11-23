#!/usr/bin/env python3
"""Select an advisory assurance profile from a trusted policy and a JSON observation."""
import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True

from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re

REGISTRY = Path(__file__).resolve().parents[1] / "catalogue" / "risk-profiles.json"
LEVELS = ("L0_MINIMAL", "L1_STANDARD", "L2_ENGINEERING", "L3_CRITICAL")
PRECEDENCE = ["host-policy", "hold-on-uncertainty", "highest-floor", "raise-only-override"]
MAX_BYTES = 200_000
EXIT = {"CLASSIFIED": 0, "HOLD": 1, "INVALID": 2}
# v1 policy authors can raise these semantic minima. A missing or weaker rule is invalid.
MINIMUM_CLASSES = (
    ("prose-only",),
    ("routine-maintenance", "read-only", "external-read"),
    ("behavior-change", "local-write", "agent-instructions", "costly-rollback"),
    ("policy-change", "privileged", "sensitive", "external-write", "production",
     "irreversible", "destructive", "paid", "merge"),
)

MINIMUM_EVIDENCE = (
    {"scope", "authority-reference", "relevant-change-verification", "failure-report"},
    {"revision", "relevant-checks", "receipts"},
    {"regression-evidence", "security-consideration", "review-where-required"},
    {"strict-approval", "independent-assurance", "operational-gates"},
)


class Unknown(ValueError):
    """Material evidence is missing, unknown or blocked."""


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Remove duplicate JSON keys.")
        result[key] = value
    return result


def invalid_constant(_):
    raise ValueError("Use finite JSON values.")


def parse(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError(f"Reduce the JSON document to {MAX_BYTES} bytes.")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys,
                      parse_constant=invalid_constant)


def fields(value, required, where, *, optional=(), policy=False):
    if not isinstance(value, dict) or value.keys() - set(required) - set(optional):
        raise ValueError(f"{where}: use an object with only documented fields.")
    missing = sorted(set(required) - value.keys())
    if missing:
        error = ValueError if policy else Unknown
        raise error(f"{where}: supply {', '.join(missing)}.")


def identifiers(values, where):
    if (not isinstance(values, list) or not values
            or any(not isinstance(v, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", v)
                   for v in values) or len(set(values)) != len(values)):
        raise ValueError(f"{where}: supply distinct nonempty policy identifiers.")
    return values


def validate_policy(policy):
    fields(policy, ["policy_version", "precedence", "profiles", "path_escalations"],
           "policy", policy=True)
    if (type(policy["policy_version"]) is not int or policy["policy_version"] != 1
            or policy["precedence"] != PRECEDENCE):
        raise ValueError("Restore a supported policy version and precedence.")
    profiles = policy["profiles"]
    fields(profiles, LEVELS, "policy.profiles", policy=True)
    rules = {}
    seen_ids = set()
    evidence = set()
    for rank, level in enumerate(LEVELS):
        spec = profiles[level]
        fields(spec, ["purpose", "effect_classes", "required_evidence"], level, policy=True)
        if not isinstance(spec["purpose"], str) or not spec["purpose"].strip():
            raise ValueError(f"{level}: supply the profile purpose.")
        evidence.update(identifiers(spec["required_evidence"], level + ".required_evidence"))
        missing = MINIMUM_EVIDENCE[rank] - evidence
        if missing:
            raise ValueError(f"{level}: restore required evidence {', '.join(sorted(missing))}.")
        effects = spec["effect_classes"]
        if not isinstance(effects, dict):
            raise ValueError(f"{level}: map each effect class to a unique rule ID.")
        for effect in identifiers(list(effects), level + ".effect_classes"):
            rule_id = effects[effect]
            if (not isinstance(rule_id, str) or not re.fullmatch(r"EF-[0-9]+", rule_id)
                    or rule_id in seen_ids or effect in rules):
                raise ValueError(f"policy: resolve conflicting or malformed rule for {effect}.")
            seen_ids.add(rule_id)
            rules[effect] = (rank, rule_id)
    for minimum, classes in enumerate(MINIMUM_CLASSES):
        for effect in classes:
            if effect not in rules or rules[effect][0] < minimum:
                raise ValueError(f"policy: restore {effect} at {LEVELS[minimum]} or higher.")
    paths = policy["path_escalations"]
    if not isinstance(paths, dict) or not paths:
        raise ValueError("policy: supply path escalation rules.")
    for pattern, effect in paths.items():
        if (not isinstance(effect, str) or effect not in rules or not pattern
                or pattern.startswith("/") or any(p in ("", ".", "..") for p in pattern.split("/"))):
            raise ValueError("policy: use relative path patterns and registered effects.")
    return rules


def known(value, where):
    if value is None or value == "unknown" or value == "":
        raise Unknown(f"{where}: supply an observed value.")
    return value


def profile_rank(value, where):
    if value not in LEVELS:
        raise ValueError(f"{where}: use a registered profile ID.")
    return LEVELS.index(value)


def classify(data, policy, rules, receipt):
    required = ("schema_version", "target", "task_intent", "observed_changed_paths",
                "declared_execution_effects", "instruction_bearing_changes",
                "authorization_or_policy_changes", "external_side_effects", "reversibility",
                "production_impact", "minimum_requested_profile", "repository_policy_constraints")
    fields(data, required, "input", optional=("operator_override",))
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version: use integer 1.")
    target = known(data["target"], "target")
    fields(target, ("repository", "revision"), "target")
    for key, pattern in (("repository", r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"),
                         ("revision", r"(?:[0-9a-f]{40}|[0-9a-f]{64})")):
        value = known(target[key], "target." + key)
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError(f"target.{key}: supply a canonical repository or full Git object ID.")
    if any(part in (".", "..") for part in target["repository"].split("/")) or not target["revision"].strip("0"):
        raise Unknown("target: identify the actual repository and revision.")

    hits = receipt["triggered_rules"]

    def floor(rule_id, source, rank):
        hits.append({"rule_id": rule_id, "source": source, "floor": LEVELS[rank]})

    def effect(value, source):
        known(value, source)
        if not isinstance(value, str):
            raise ValueError(f"{source}: use a registered effect string.")
        if value not in rules:
            raise Unknown(f"{source}: inspect the effect and map it to a registered class.")
        rank, rule_id = rules[value]
        floor(rule_id, source, rank)

    def effect_list(values, source):
        known(values, source)
        if not isinstance(values, list):
            raise ValueError(f"{source}: supply an array of observed effect classes.")
        if not values:
            raise Unknown(f"{source}: identify at least one actual effect.")
        for value in values:
            effect(value, source)

    effect(data["task_intent"], "task_intent")
    effect_list(data["declared_execution_effects"], "declared_execution_effects")
    paths = known(data["observed_changed_paths"], "observed_changed_paths")
    if not isinstance(paths, list):
        raise ValueError("observed_changed_paths: supply an array of path observations.")
    if not paths and data["task_intent"] == "prose-only":
        raise Unknown("observed_changed_paths: identify the prose change before classification.")
    for index, item in enumerate(paths):
        source = f"observed_changed_paths[{index}]"
        fields(item, ("path", "effects"), source)
        path = known(item["path"], source + ".path")
        if (not isinstance(path, str) or not path.isprintable() or "\\" in path
                or re.match(r"^[A-Za-z]:", path)
                or any(p in ("", ".", "..") for p in path.split("/"))):
            raise ValueError(f"{source}.path: use a normalized repository-relative path.")
        effect_list(item["effects"], source + ".effects")
        for pattern, risk in policy["path_escalations"].items():
            candidate = path if "/" in pattern else path.rsplit("/", 1)[-1]
            if fnmatchcase(candidate, pattern):
                floor("path." + pattern, source + ".path", rules[risk][0])

    for field, risk in (("instruction_bearing_changes", "agent-instructions"),
                        ("authorization_or_policy_changes", "policy-change"),
                        ("production_impact", "production")):
        flag = known(data[field], field)
        if type(flag) is not bool:
            raise ValueError(f"{field}: use true, false or null for unknown.")
        if flag:
            effect(risk, field)

    for field, neutral, choices in (
        ("reversibility", "reversible", ("costly-rollback", "irreversible")),
        ("external_side_effects", "none", ("external-read", "external-write")),
    ):
        value = known(data[field], field)
        if value != neutral:
            if value not in choices:
                raise ValueError(f"{field}: use {', '.join((neutral, *choices))} or null.")
            effect(value, field)

    constraints = known(data["repository_policy_constraints"], "repository_policy_constraints")
    fields(constraints, ("minimum_profile", "hold"), "repository_policy_constraints")
    hold = known(constraints["hold"], "repository_policy_constraints.hold")
    if type(hold) is not bool:
        raise ValueError("repository_policy_constraints.hold: use true, false or null.")
    for source, requested in (("repository_policy_constraints.minimum_profile", constraints["minimum_profile"]),
                              ("minimum_requested_profile", data["minimum_requested_profile"])):
        floor("minimum." + source, source, profile_rank(known(requested, source), source))
    highest = max(LEVELS.index(hit["floor"]) for hit in hits)
    if hold:
        raise Unknown("repository_policy_constraints.hold: resolve the policy hold with its owner.")
    if "operator_override" in data:
        override = profile_rank(known(data["operator_override"], "operator_override"), "operator_override")
        if override < highest:
            raise Unknown(f"operator_override: remove the downgrade or request {LEVELS[highest]} or higher.")
        floor("operator.raise-only", "operator_override", override)
        highest = override

    receipt["profile"] = LEVELS[highest]
    receipt["required_evidence"] = sorted({item for level in LEVELS[:highest + 1]
                                           for item in policy["profiles"][level]["required_evidence"]})


def decide(raw, registry):
    receipt = {"receipt_version": 1, "authority_granted": False, "profile": None,
               "required_evidence": [], "triggered_rules": [], "reasons": [],
               "policy_sha256": hashlib.sha256(registry).hexdigest() if len(registry) <= MAX_BYTES else None,
               "input_sha256": hashlib.sha256(raw).hexdigest() if len(raw) <= MAX_BYTES else None}
    source = "registry"
    try:
        policy = parse(registry)
        rules = validate_policy(policy)
        source = "input"
        classify(parse(raw), policy, rules, receipt)
        receipt["decision"] = "CLASSIFIED"
    except Unknown as exc:
        receipt.update(decision="HOLD", reasons=[str(exc)])
    except (ValueError, RecursionError) as exc:
        receipt.update(decision="INVALID", reasons=[f"{source}: {exc}"])
    return receipt


def main():
    try:
        if sys.argv[1:]:
            raise ValueError("Pass one JSON document on stdin without command-line arguments.")
        if REGISTRY.parent.is_symlink() or REGISTRY.is_symlink() or not REGISTRY.is_file():
            raise ValueError("Restore the regular catalogue/risk-profiles.json in the trusted checkout.")
        with REGISTRY.open("rb") as stream:
            registry = stream.read(MAX_BYTES + 1)
        result = decide(sys.stdin.buffer.read(MAX_BYTES + 1), registry)
    except (OSError, ValueError) as exc:
        result = {"receipt_version": 1, "decision": "INVALID", "profile": None,
                  "authority_granted": False, "triggered_rules": [], "required_evidence": [],
                  "policy_sha256": None, "input_sha256": None, "reasons": [str(exc)]}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return EXIT[result["decision"]]


if __name__ == "__main__":
    raise SystemExit(main())
