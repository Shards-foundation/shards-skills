#!/usr/bin/env python3
"""Validate a Shards execution-contract envelope without executing any task."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

SHA = re.compile(r"^[0-9a-fA-F]{40}$")
REPOSITORY = re.compile(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+")
CHECK_KINDS = {"test", "self-reported-test", "check"}
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


def _scan_secrets(value, depth=0):
    if depth > 64:
        raise ValueError("Contract exceeds maximum nesting depth")
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_FIELD.search(str(key)):
                raise ValueError("Sensitive field name is forbidden")
            _scan_secrets(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_secrets(item, depth + 1)
    elif isinstance(value, str) and SECRET.search(value):
        raise ValueError("Credential-like content is forbidden")


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError("Duplicate JSON field")
        fields[key] = value
    return fields


def _invalid_constant(_):
    raise ValueError("Invalid JSON number")


def _actor_label(value):
    # GitHub login case and the display-only @ prefix cannot create independence.
    label = value.strip().removeprefix("@").casefold()
    if not label:
        raise ValueError("Empty actor identifier")
    return label


def _artifact_reference(ref, repository):
    """Identity for duplicate detection and compatibility with a formal review claim."""
    if ref != ref.strip() or any(ord(ch) < 32 for ch in ref):
        raise ValueError("Malformed artifact reference")
    url = urlsplit(ref)
    host = (url.hostname or "").rstrip(".")
    if host not in ("github.com", "www.github.com", "api.github.com"):
        return ref, "opaque"  # Local and other host references remain self-reported.
    if url.scheme != "https" or url.username is not None or url.port not in (443, None):
        return ref, "inapplicable"
    prefix = "/repos/" if host == "api.github.com" else "/"
    scoped_path = re.match(prefix + r"([^/]+/[^/]+)(?:/|$)", url.path)
    if not scoped_path or scoped_path[1].casefold() != repository.casefold():
        return ref, "inapplicable"
    if url.fragment.startswith(("issuecomment-", "discussion_r")) or "/comments/" in url.path:
        return ref, "inapplicable"
    if host == "api.github.com":
        target = re.fullmatch(r"/repos/([^/]+/[^/]+)/pulls/([1-9][0-9]*)/reviews/([1-9][0-9]*)/?", url.path)
        if not target or url.fragment:
            return ref, "other-github"
        repo, pull, review = target.groups()
    else:
        target = re.fullmatch(r"/([^/]+/[^/]+)/pull/([1-9][0-9]*)/?", url.path)
        anchor = re.fullmatch(r"pullrequestreview-([1-9][0-9]*)", url.fragment)
        if not target or not anchor:
            return ref, "other-github"
        repo, pull = target.groups()
        review = anchor.group(1)
    return (repo.casefold(), pull, review), "github-review"


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
    repository = _text(scope, "repository")
    if not REPOSITORY.fullmatch(repository) or any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("Repository must be an owner/repo identifier")
    branch = _text(scope, "branch")
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

    def unique_items(items, key, category):
        ids = set()
        for item in items:
            if not _is_object(item):
                raise ValueError(category + " must be an object")
            value = _text(item, key)
            if value in ids:
                raise ValueError("Duplicate " + category + " identifier")
            ids.add(value)
        return ids

    step_ids = unique_items(steps, "id", "step")
    check_ids = unique_items(checks, "id", "check")

    def covered_ids(item, field, known_ids):
        ids = _array(item, field)
        if not ids or any(not isinstance(i, str) or i not in known_ids for i in ids):
            raise ValueError("Unknown or missing identifiers in " + field)
        covered = frozenset(ids)
        if len(covered) != len(ids):
            raise ValueError("Duplicate identifier in " + field)
        return covered

    evidence_ids = set()
    formal_reviews = {}
    artifact_keys = {}
    work_receipts = set()
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

        for key in ("repository", "branch", "subject_actor"):
            if key in item:
                _text(item, key)
        if "repository" in item and not REPOSITORY.fullmatch(item["repository"]):
            raise ValueError("Invalid evidence repository")
        if "result" in item and _text(item, "result") not in CHECK_RESULTS:
            raise ValueError("Invalid evidence result")
        for field, known in (("step_ids", step_ids), ("check_ids", check_ids)):
            if field in item:
                covered_ids(item, field, known)

        artifact_keys[item_id], ref_kind = _artifact_reference(item["ref"], repository)
        if item["kind"] in CHECK_KINDS and ref_kind in ("opaque", "other-github"):
            work_receipts.add(item_id)
        if item["kind"] == "formal-review":
            if _text(item, "verdict") not in REVIEW_VERDICTS:
                raise ValueError("Unknown formal review artifact verdict")
            covered = covered_ids(item, "step_ids", step_ids)
            if ref_kind in ("opaque", "github-review"):
                formal_reviews[item_id] = (covered, item["observed_by"], item["verdict"])

    def check_refs(item):
        refs = _array(item, "evidence_ids")
        if any(not isinstance(ref, str) or ref not in evidence_ids for ref in refs):
            raise ValueError("Unknown evidence reference")
        return refs

    reasons = []
    evidence_by_id = {entry["id"]: entry for entry in evidence}
    artifact_counts = Counter(artifact_keys.values())

    def live_refs(refs):
        return bool(refs) and all(
            head_sha is not None and evidence_by_id[ref]["revision"].lower() == head_sha.lower()
            and evidence_by_id[ref].get("repository", repository).casefold() == repository.casefold()
            and evidence_by_id[ref].get("branch", branch) == branch
            for ref in refs
        )

    def supports_work(refs, field, work_id, total, subject=None, observer=None):
        for ref in refs:
            item = evidence_by_id[ref]
            if ref not in work_receipts or item.get("result", "PASS") != "PASS":
                continue
            if artifact_counts[artifact_keys[ref]] != 1:
                continue
            if field in item:
                if work_id not in item[field]:
                    continue
            elif total != 1:
                continue
            if subject is not None and item.get("subject_actor", item["observed_by"]) != subject:
                continue
            if observer is not None and item["observed_by"] != observer:
                continue
            return True
        return False

    if head_sha is None:
        reasons.append("Unknown exact head SHA")
    if any(a["material"] and not a["resolved"] for a in ambiguities):
        reasons.append("Unresolved material ambiguity")
    if any(constraints[key] for key in CONSTRAINT_KEYS):
        reasons.append("Host authorization for consequential effects cannot be verified by this validator")

    owners = {}
    failed = False
    for step in steps:
        owners[step["id"]] = _actor_label(_text(step, "owner"))
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
            reasons.append("Step failed: " + step["id"])
        elif status != "VERIFIED":
            reasons.append("Step not reported VERIFIED: " + step["id"])
        if status == "VERIFIED" and (not live_refs(refs) or not supports_work(
                refs, "step_ids", step["id"], len(steps), subject=step["owner"])):
            reasons.append("Missing applicable current verification evidence for step: " + step["id"])

    for check in checks:
        result = _text(check, "result")
        if result not in CHECK_RESULTS:
            raise ValueError("Unknown check result")
        refs = check_refs(check)
        if result == "PASS" and not refs:
            raise ValueError("Passing check lacks evidence")
        if result == "FAIL":
            failed = True
            reasons.append("Check failed: " + check["id"])
        elif result != "PASS":
            reasons.append("Check not passing: " + check["id"])
        observer = _text(check, "observed_by") if "observed_by" in check else None
        if result == "PASS" and (not live_refs(refs) or not supports_work(
                refs, "check_ids", check["id"], len(checks), observer=observer)):
            reasons.append("Missing applicable current result evidence for check: " + check["id"])

    approved_steps = set()
    for review in reviews:
        if not _is_object(review):
            raise ValueError("Review must be an object")
        covered = covered_ids(review, "step_ids", step_ids) if "step_ids" in review else frozenset()
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
        if not current:
            continue
        if open_findings:
            reasons.append("Open findings at current revision")
        if verdict != "APPROVED":
            reasons.append("Review blocked at current revision")
            continue

        actor = _actor_label(reviewer)
        if not covered or actor == _actor_label(executor):
            continue
        if any(owners[step_id] == actor for step_id in covered):
            continue
        if open_findings or not live_refs(refs):
            continue
        expected_review = (covered, reviewer, verdict)
        if any(formal_reviews.get(ref) == expected_review
               and artifact_counts[artifact_keys[ref]] == 1 for ref in refs):
            approved_steps.update(covered)

    for step_id in step_ids - approved_steps:
        reasons.append("No applicable independent review claim at current head SHA: " + step_id)

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
    item.add_argument("--input", required=True, type=Path, help="UTF-8 JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        if args.input == Path("-"):
            raw = sys.stdin.buffer.read(200_001)
        else:
            if args.input.is_symlink():
                raise ValueError("Symlinked contract input is forbidden")
            path = args.input.resolve()
            if not path.is_file() or path.stat().st_size > 200_000:
                raise ValueError("Input must be an existing regular JSON file under 200KB")
            with path.open("rb") as source:
                raw = source.read(200_001)
        if len(raw) > 200_000:
            raise ValueError("Contract exceeds byte limit")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields,
                          parse_constant=_invalid_constant)
        report = validate(data)
    except (OSError, UnicodeError, ValueError, RecursionError):
        report = {
            "workflow": "shards-execution-contract",
            "structural_status": "INVALID",
            "decision": "INVALID",
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
