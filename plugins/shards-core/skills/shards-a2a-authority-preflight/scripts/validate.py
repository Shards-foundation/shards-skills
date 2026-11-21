#!/usr/bin/env python3
"""Validate a self-reported Shards A2A authority inventory. Never probes or grants access."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)
SENSITIVE = re.compile(r"(?:password|token|api[_-]?key|private[_-]?key|secret|credential[_-]?value)", re.I)
MAX_INPUT_BYTES = 262144
MAX_DEPTH = 32
ROLES = ("delegator", "coordinator", "executor", "integrator", "reviewer", "merge_decider")
OPERATIONS = {
    "repo.read": "READ", "git.fetch": "READ", "pr.read": "READ", "ci.read": "READ",
    "source.edit": "LOCAL_WRITE", "git.commit": "LOCAL_WRITE", "git.pull": "LOCAL_WRITE",
    "tests.run": "LOCAL_EXECUTE", "git.push": "EXTERNAL_WRITE",
    "pr.create": "EXTERNAL_WRITE", "pr.comment": "EXTERNAL_WRITE",
    "pr.approve": "EXTERNAL_WRITE", "pr.merge": "SENSITIVE",
    "deployment.run": "SENSITIVE", "credentials.rotate": "SENSITIVE",
}
PERMISSION = {"GRANTED", "UNKNOWN", "DENIED"}
ACCESS = {"OBSERVED", "UNKNOWN", "DENIED"}
POLICY = {"VERIFIED", "UNKNOWN", "DENIED", "NOT_APPLICABLE"}
ACCESS_ISSUES = {"NONE", "MISSING_CONNECTOR", "MISSING_CREDENTIAL", "TOOL_UNAVAILABLE", "PERMISSION_DENIED", "UNVERIFIED"}
EVIDENCE_KINDS = {"delegation", "capability", "policy"}


def _string(value: object, label: str, pattern: re.Pattern | None = None) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"Missing or invalid {label}")
    if pattern is not None and not pattern.fullmatch(value):
        raise ValueError(f"Invalid {label}")
    return value


def _object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {label}")
    return value


def _array(value: object, label: str, limit: int) -> list:
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"Invalid {label}")
    return value


def _contains_secret(value: object, depth: int = 0) -> bool:
    if depth > MAX_DEPTH:
        raise ValueError("Inventory exceeds nesting limit")
    if isinstance(value, str):
        return bool(SECRET.search(value))
    if isinstance(value, dict):
        return any(SENSITIVE.search(str(k)) or _contains_secret(v, depth + 1) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_secret(v, depth + 1) for v in value)
    return False


def validate(data: object) -> dict:
    obj = _object(data, "document")
    if _contains_secret(obj):
        raise ValueError("Potential sensitive data present; do not print or transfer it")
    if type(obj.get("schema_version")) is not int or obj["schema_version"] != 1:
        raise ValueError("Unsupported schema_version")
    task = _object(obj.get("task"), "task")
    task_id = _string(task.get("id"), "task.id", ID)
    _string(task.get("goal"), "task.goal")
    repo = _string(task.get("repository"), "task.repository", REPO)
    branch = _string(task.get("branch"), "task.branch")
    sha = _string(task.get("head_sha"), "task.head_sha", SHA)
    roles = _object(obj.get("roles"), "roles")
    role_ids = {role: _string(roles.get(role), f"roles.{role}", ID) for role in ROLES}
    if role_ids["reviewer"] in (role_ids["executor"], role_ids["integrator"]):
        raise ValueError("Independent reviewer must differ from executor and integrator")
    actor_ids = set(role_ids.values())
    if len({actor.casefold() for actor in actor_ids}) != len(actor_ids):
        raise ValueError("Ambiguous case variants of an actor ID")
    raw_evidence = _array(obj.get("evidence"), "evidence", 96)
    evidence: dict[str, dict] = {}
    observations_by_reference = {}
    for raw in raw_evidence:
        e = _object(raw, "evidence item")
        eid = _string(e.get("id"), "evidence.id", ID)
        if eid in evidence:
            raise ValueError("Duplicate evidence ID")
        if _string(e.get("kind"), "evidence.kind") not in EVIDENCE_KINDS:
            raise ValueError("Unknown evidence kind")
        _string(e.get("reference"), "evidence.reference")
        _string(e.get("observed_by"), "evidence.observed_by", ID)
        _string(e.get("revision"), "evidence.revision", SHA)
        # v1 inventories before scoped evidence remain readable. Absent fields
        # cannot match an action, and present fields must have the correct type.
        for field, pattern in (("subject_actor", ID), ("operation", None),
                               ("repository", REPO), ("branch", None)):
            if field in e:
                _string(e[field], "evidence." + field, pattern)
        if "operation" in e and e["operation"] not in OPERATIONS:
            raise ValueError("Unknown evidence operation")
        observation = tuple(e.get(key) for key in ("kind", "revision", "observed_by", "subject_actor",
                                                   "operation", "repository", "branch"))
        observations_by_reference.setdefault(e["reference"].strip(), set()).add(observation)
        evidence[eid] = e
    raw_actions = _array(obj.get("actions"), "actions", 48)
    if not raw_actions:
        raise ValueError("At least one requested action is required")
    blocked, matrix = [], []
    seen = set()
    for raw in raw_actions:
        a = _object(raw, "action")
        actor = _string(a.get("actor"), "action.actor", ID)
        if actor not in actor_ids:
            raise ValueError("Action actor not assigned to any task role")
        op = _string(a.get("operation"), "action.operation")
        if op not in OPERATIONS:
            raise ValueError("Unknown operation")
        if a.get("repository") != repo or a.get("branch") != branch:
            raise ValueError("Action target does not match task scope")
        key = (actor, op)
        if key in seen:
            raise ValueError("Duplicate actor/operation action")
        seen.add(key)
        if op == "pr.approve" and actor != role_ids["reviewer"]:
            raise ValueError("Only assigned independent reviewer may approve")
        if op == "pr.merge" and actor != role_ids["merge_decider"]:
            raise ValueError("Only assigned merge decider may merge")
        if op == "source.edit" and actor != role_ids["executor"]:
            raise ValueError("Only assigned executor may edit")
        permission, access, policy, issue = (
            _string(a.get(field), "action." + field)
            for field in ("permission", "access", "policy", "access_issue")
        )
        if permission not in PERMISSION or access not in ACCESS or policy not in POLICY or issue not in ACCESS_ISSUES:
            raise ValueError("Invalid action status")
        if access == "OBSERVED" and issue != "NONE":
            raise ValueError("Observed access cannot have an unresolved access issue")
        if access != "OBSERVED" and issue == "NONE":
            raise ValueError("Unknown or denied access must state an access issue")
        if access == "DENIED" and issue != "PERMISSION_DENIED":
            raise ValueError("Denied access requires a permission-denied observation")
        if access == "UNKNOWN" and issue == "PERMISSION_DENIED":
            raise ValueError("Permission denial must be recorded as DENIED, not UNKNOWN")
        if OPERATIONS[op] in ("EXTERNAL_WRITE", "SENSITIVE") and policy == "NOT_APPLICABLE":
            raise ValueError("External writes need an explicitly checked policy gate")
        refs = _array(a.get("evidence_ids"), "action.evidence_ids", 12)
        if any(not isinstance(r, str) or r not in evidence for r in refs):
            raise ValueError("Action references missing evidence")
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate evidence reference")
        matched = []
        reasons = []
        for ref in refs:
            item = evidence[ref]
            if (item["revision"] == sha and item["observed_by"] in actor_ids
                    and item.get("subject_actor") == actor and item.get("operation") == op
                    and item.get("repository") == repo and item.get("branch") == branch):
                if len(observations_by_reference[item["reference"].strip()]) != 1:
                    reasons.append("AMBIGUOUS_EVIDENCE_REFERENCE")
                else:
                    matched.append(item)
        kinds_current = {item["kind"] for item in matched}
        if permission != "GRANTED": reasons.append("SCOPE_" + permission)
        if permission == "GRANTED" and "delegation" not in kinds_current: reasons.append("DELEGATION_NOT_VERIFIED")
        if access != "OBSERVED": reasons.append(issue)
        if access == "OBSERVED" and "capability" not in kinds_current: reasons.append("CAPABILITY_EVIDENCE_MISSING_OR_STALE")
        if policy in ("UNKNOWN", "DENIED"): reasons.append("POLICY_" + policy)
        if policy == "VERIFIED" and "policy" not in kinds_current: reasons.append("POLICY_EVIDENCE_MISSING_OR_STALE")
        if reasons:
            next_owner = next((role_ids[role] for role in ("coordinator", "delegator")
                               if role_ids[role] != actor), None)
            blocked.append({"actor": actor, "operation": op, "reasons": sorted(set(reasons)),
                            "escalate_to": next_owner})
        matrix.append({"actor": actor, "operation": op, "effect": OPERATIONS[op],
                       "matched_evidence": [{"id": item["id"], "kind": item["kind"],
                                             "observed_by": item["observed_by"]} for item in matched],
                       "claim_status": "COMPLETE" if not reasons else "HOLD"})
    reviewer = role_ids["reviewer"]
    if (reviewer, "pr.approve") in seen and any(
            (reviewer, op) in seen for op in ("git.commit", "git.push", "pr.create")):
        raise ValueError("Independent reviewer cannot formally review work they author or publish")
    return {"skill": "shards-a2a-authority-preflight", "schema_version": 1,
            "task_id": task_id, "repository": repo, "branch": branch, "head_sha": sha,
            "decision": "CLAIMS_COMPLETE" if not blocked else "HOLD",
            "authority_granted_by_validator": False, "external_permissions_verified_by_validator": False,
            "execution_performed": False, "independent_review_performed": False,
            "evidence_type": "SELF_REPORTED_METADATA_ONLY",
            "operations": matrix, "blockers": blocked,
            "next_step": "Recheck host grants, effective access, policy and revision at execution time; seek scoped authority for any effects."}


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object field")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError("Invalid JSON numeric constant")


def _read_inventory(path: Path) -> object:
    if path == Path("-"):
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        if path.is_symlink() or not path.is_file():
            raise ValueError("Input absent or symlinked")
        with path.open("rb") as file:
            raw = file.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds size limit")
    # Bound container nesting before invoking the recursive JSON decoder.
    depth = 0
    in_string = escaped = False
    content = raw.decode("utf-8")
    for char in content:
        if escaped:
            escaped = False
        elif in_string and char == "\\":
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char in "[{":
                depth += 1
                if depth > MAX_DEPTH:
                    raise ValueError("Inventory exceeds nesting limit")
            elif char in "]}":
                depth -= 1
                if depth < 0:
                    raise ValueError("Invalid JSON nesting")
    return json.loads(content, object_pairs_hook=_unique_fields, parse_constant=_invalid_constant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("validate",), default="validate")
    parser.add_argument("--input", type=Path, required=True, help="UTF-8 JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = validate(_read_inventory(args.input))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["decision"] == "CLAIMS_COMPLETE" else 1
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        print(json.dumps({"decision": "INVALID", "error": "Could not read or decode inventory"}), file=sys.stderr)
        return 2
    except ValueError as exc:
        # Validation errors contain field names and constraints only.
        print(json.dumps({"decision": "INVALID", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
