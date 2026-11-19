#!/usr/bin/env python3
"""Validate a Shards execution-contract envelope without executing any task."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-fA-F]{40}$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
SENSITIVE_FIELD = re.compile(r"(?:password|private[_-]?key|api[_-]?key|access[_-]?token|secret)", re.I)
STEP_STATUSES = {"PROPOSED", "EXECUTED", "VERIFIED", "FAILED", "BLOCKED"}
EFFECTS = {"read-only", "local-write", "local-execute", "external-write", "production", "paid", "merge", "destructive", "sensitive"}
EFFECT_PERMISSIONS = {"external-write": "allow_external_write", "production": "allow_production", "paid": "allow_paid", "merge": "allow_merge"}
CHECK_RESULTS = {"PASS", "FAIL", "NOT_RUN", "BLOCKED"}
REVIEW_VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "BLOCKED"}
CONSTRAINT_KEYS = ("allow_paid", "allow_production", "allow_merge", "allow_external_write")


def _is_object(value):
    return isinstance(value, dict)


def _text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing non-empty string: " + key)
    return value


def _array(obj, key):
    value = obj.get(key)
    if not isinstance(value, list):
        raise ValueError("Missing list: " + key)
    return value


def _scan_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_FIELD.search(str(key)):
                raise ValueError("Sensitive field name is forbidden")
            _scan_secrets(item)
    elif isinstance(value, list):
        for item in value:
            _scan_secrets(item)
    elif isinstance(value, str) and SECRET.search(value):
        raise ValueError("Credential-like content is forbidden")


def validate(data):
    """Return a structural verdict; never interpret this as host permission."""
    if not _is_object(data):
        raise ValueError("Contract must be a JSON object")
    _scan_secrets(data)
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported schema_version")
    task_id = _text(data, "task_id")
    if not SLUG.fullmatch(task_id):
        raise ValueError("Invalid task_id")
    intent = data.get("intent")
    scope = data.get("scope")
    constraints = data.get("constraints")
    if not all(_is_object(x) for x in (intent, scope, constraints)):
        raise ValueError("intent, scope and constraints must be objects")
    _text(intent, "reference")
    _text(intent, "goal")
    assumptions = _array(intent, "assumptions")
    if any(not isinstance(x, str) for x in assumptions):
        raise ValueError("assumptions must be strings")
    ambiguities = _array(intent, "ambiguities")
    for ambiguity in ambiguities:
        if not _is_object(ambiguity):
            raise ValueError("ambiguity must be an object")
        _text(ambiguity, "description")
        if type(ambiguity.get("material")) is not bool or type(ambiguity.get("resolved")) is not bool:
            raise ValueError("ambiguity flags must be booleans")
    _text(scope, "repository")
    _text(scope, "branch")
    head_sha = scope.get("head_sha")
    if head_sha is not None and (not isinstance(head_sha, str) or not SHA.fullmatch(head_sha)):
        raise ValueError("head_sha must be a full 40-character commit SHA or null")
    for key in CONSTRAINT_KEYS:
        if type(constraints.get(key)) is not bool:
            raise ValueError("Constraint must be boolean: " + key)
    executor = _text(data, "executor")
    steps = _array(data, "steps")
    checks = _array(data, "checks")
    reviews = _array(data, "reviews")
    evidence = _array(data, "evidence")
    if not steps or not checks:
        raise ValueError("At least one step and one check are required")

    evidence_ids = set()
    for item in evidence:
        if not _is_object(item):
            raise ValueError("Evidence entry must be an object")
        item_id = _text(item, "id")
        if item_id in evidence_ids:
            raise ValueError("Duplicate evidence id")
        evidence_ids.add(item_id)
        for key in ("kind", "ref", "revision", "observed_by"):
            _text(item, key)
        if not SHA.fullmatch(item["revision"]):
            raise ValueError("Evidence revision must be a full SHA")

    def check_refs(item):
        refs = _array(item, "evidence_ids")
        if any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs):
            raise ValueError("Unknown evidence reference")
        return refs

    def unique_items(items, key, category):
        ids = set()
        for item in items:
            if not _is_object(item):
                raise ValueError(category + " must be an object")
            value = _text(item, key)
            if value in ids:
                raise ValueError("Duplicate " + category + " identifier")
            ids.add(value)

    unique_items(steps, "id", "step")
    unique_items(checks, "id", "check")
    reasons = []
    evidence_by_id = {entry["id"]: entry for entry in evidence}

    def live_refs(refs):
        return bool(refs) and all(
            head_sha is not None and evidence_by_id[ref]["revision"].lower() == head_sha.lower()
            for ref in refs
        )

    if head_sha is None:
        reasons.append("Unknown exact head SHA")
    if any(a["material"] and not a["resolved"] for a in ambiguities):
        reasons.append("Unresolved material ambiguity")
    if any(constraints[key] for key in CONSTRAINT_KEYS):
        reasons.append("Host authorization for consequential effects cannot be verified by this validator")

    failed = False
    step_owners = set()
    for step in steps:
        step_owners.add(_text(step, "owner"))
        effect = _text(step, "effect")
        if effect not in EFFECTS:
            raise ValueError("Unknown effect class")
        status = _text(step, "status")
        if status not in STEP_STATUSES:
            raise ValueError("Unknown step status")
        refs = check_refs(step)
        if status in ("EXECUTED", "VERIFIED") and not refs:
            raise ValueError("Observed or verified step lacks evidence")
        if status in ("EXECUTED", "VERIFIED"):
            permission = EFFECT_PERMISSIONS.get(effect)
            if permission and not constraints[permission]:
                failed = True
                reasons.append("Executed effect contradicts declared constraints: " + step["id"])
            if effect in ("destructive", "sensitive"):
                reasons.append("Sensitive or destructive effect needs host verification: " + step["id"])
        if status == "FAILED":
            failed = True
        elif status != "VERIFIED":
            reasons.append("Step not independently verified: " + step["id"])
        if status == "VERIFIED" and not live_refs(refs):
            reasons.append("Stale or missing step evidence: " + step["id"])

    for check in checks:
        result = _text(check, "result")
        if result not in CHECK_RESULTS:
            raise ValueError("Unknown check result")
        refs = check_refs(check)
        if result == "PASS" and not refs:
            raise ValueError("Passing check lacks evidence")
        if result == "FAIL":
            failed = True
        elif result != "PASS":
            reasons.append("Check not passing: " + check["id"])
        if result == "PASS" and not live_refs(refs):
            reasons.append("Stale or missing check evidence: " + check["id"])

    approved = False
    for review in reviews:
        if not _is_object(review):
            raise ValueError("Review entry must be an object")
        reviewer = _text(review, "reviewer")
        revision = _text(review, "revision")
        verdict = _text(review, "verdict")
        if verdict not in REVIEW_VERDICTS:
            raise ValueError("Unknown review verdict")
        if not SHA.fullmatch(revision):
            raise ValueError("Review revision must be a full SHA")
        open_findings = review.get("open_findings")
        if type(open_findings) is not int or open_findings < 0:
            raise ValueError("open_findings must be a nonnegative integer")
        refs = check_refs(review)
        if verdict == "APPROVED" and not refs:
            raise ValueError("Approved review lacks evidence")
        current = head_sha is not None and revision.lower() == head_sha.lower()
        if (verdict == "APPROVED" and reviewer != executor
                and reviewer not in step_owners and current
                and open_findings == 0 and live_refs(refs)):
            approved = True
        elif current and open_findings:
            reasons.append("Open findings at current revision")
        elif current and verdict in ("CHANGES_REQUESTED", "BLOCKED"):
            reasons.append("Review blocked at current revision")
    if not approved:
        reasons.append("No evidence-backed different-actor approval of current head SHA")

    decision = "FAIL" if failed else ("HOLD" if reasons else "EVIDENCE_READY")
    return {
        "workflow": "shards-execution-contract",
        "schema_version": 1,
        "task_id": task_id,
        "revision": head_sha,
        "structural_status": "VALID",
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "execution_performed": False,
        "approval_verified": False,
        "independent_review_verified": False,
        "scope": "local structural checks of self-reported references only",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    item = subs.add_parser("validate")
    item.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.input.is_symlink():
            raise ValueError("Symlinked contract input is forbidden")
        path = args.input.resolve()
        if not path.is_file() or path.stat().st_size > 200_000:
            raise ValueError("Input must be an existing regular JSON file under 200KB")
        data = json.loads(path.read_text(encoding="utf-8"))
        report = validate(data)
    except (OSError, UnicodeError, ValueError, TypeError):
        report = {
            "workflow": "shards-execution-contract",
            "structural_status": "INVALID",
            "decision": "HOLD",
            "reasons": ["Invalid or unsafe contract; inspect input locally"],
            "execution_performed": False,
            "approval_verified": False,
            "independent_review_verified": False,
        }
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "EVIDENCE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
