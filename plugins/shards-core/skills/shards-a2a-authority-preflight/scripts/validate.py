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
SENSITIVE = re.compile(r"(?:password|access[_-]?token|api[_-]?key|private[_-]?key|secret|credential[_-]?value)", re.I)
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


def _contains_secret(value: object) -> bool:
    if isinstance(value, str):
        return bool(SECRET.search(value))
    if isinstance(value, dict):
        return any(SENSITIVE.search(str(k)) or _contains_secret(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_secret(v) for v in value)
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
    _string(task.get("branch"), "task.branch")
    sha = _string(task.get("head_sha"), "task.head_sha", SHA)
    roles = _object(obj.get("roles"), "roles")
    role_ids = {role: _string(roles.get(role), f"roles.{role}", ID) for role in ROLES}
    if role_ids["reviewer"] in (role_ids["executor"], role_ids["integrator"]):
        raise ValueError("Independent reviewer must differ from executor and integrator")
    actor_ids = set(role_ids.values())
    raw_evidence = _array(obj.get("evidence"), "evidence", 96)
    evidence: dict[str, dict] = {}
    for raw in raw_evidence:
        e = _object(raw, "evidence item")
        eid = _string(e.get("id"), "evidence.id", ID)
        if eid in evidence:
            raise ValueError("Duplicate evidence ID")
        if e.get("kind") not in EVIDENCE_KINDS:
            raise ValueError("Unknown evidence kind")
        _string(e.get("reference"), "evidence.reference")
        _string(e.get("observed_by"), "evidence.observed_by", ID)
        _string(e.get("revision"), "evidence.revision", SHA)
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
        if a.get("repository") != repo or a.get("branch") != task["branch"]:
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
        permission, access, policy, issue = (a.get("permission"), a.get("access"),
                                             a.get("policy"), a.get("access_issue"))
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
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate evidence reference")
        if any(not isinstance(r, str) or r not in evidence for r in refs):
            raise ValueError("Action references missing evidence")
        kinds_current = {evidence[r]["kind"] for r in refs if evidence[r]["revision"] == sha}
        reasons = []
        if permission != "GRANTED": reasons.append("SCOPE_" + permission)
        if permission == "GRANTED" and "delegation" not in kinds_current: reasons.append("DELEGATION_NOT_VERIFIED")
        if access != "OBSERVED": reasons.append(issue)
        if access == "OBSERVED" and "capability" not in kinds_current: reasons.append("CAPABILITY_EVIDENCE_MISSING_OR_STALE")
        if policy in ("UNKNOWN", "DENIED"): reasons.append("POLICY_" + policy)
        if policy == "VERIFIED" and "policy" not in kinds_current: reasons.append("POLICY_EVIDENCE_MISSING_OR_STALE")
        next_owner = (role_ids["merge_decider"] if op in ("pr.merge", "deployment.run", "credentials.rotate")
                      else role_ids["reviewer"] if op == "pr.approve"
                      else role_ids["coordinator"])
        if reasons:
            blocked.append({"actor": actor, "operation": op, "reasons": sorted(set(reasons)),
                            "escalate_to": next_owner})
        matrix.append({"actor": actor, "operation": op, "effect": OPERATIONS[op],
                       "claim_status": "COMPLETE" if not reasons else "HOLD"})
    return {"skill": "shards-a2a-authority-preflight", "schema_version": 1,
            "task_id": task_id, "repository": repo, "head_sha": sha,
            "decision": "CLAIMS_COMPLETE" if not blocked else "HOLD",
            "authority_granted_by_validator": False, "external_permissions_verified_by_validator": False,
            "execution_performed": False, "independent_review_performed": False,
            "evidence_type": "SELF_REPORTED_METADATA_ONLY",
            "operations": matrix, "blockers": blocked,
            "next_step": "Recheck host grants, effective access, policy and revision at execution time; seek scoped authority for any effects."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("validate",), default="validate")
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.input.is_symlink() or not args.input.is_file() or args.input.stat().st_size > 262144:
            raise ValueError("Input absent, symlinked or oversized")
        with args.input.open(encoding="utf-8") as file:
            obj = json.load(file)
        result = validate(obj)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["decision"] == "CLAIMS_COMPLETE" else 1
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Do not echo raw source text in errors.
        print(json.dumps({"decision": "INVALID", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
