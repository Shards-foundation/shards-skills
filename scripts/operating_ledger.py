#!/usr/bin/env python3
"""Append-only, hash-chained local operating ledger. No network or skill execution."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$")
KINDS = {"attempt", "checkpoint", "evidence", "review", "lesson", "amendment", "decision"}
OUTCOMES = {"proposed", "implemented", "tested", "reviewed", "deployed", "production-verified", "fail", "blocked"}
REQUIRED_EVIDENCE = {"implemented", "tested", "reviewed", "deployed", "production-verified"}
TARGET_FIELDS = {"target_revision", "subject_actor", "resource", "required_evidence"}
ATTRIBUTION = {"subject_actor", "observed_by", "resource"}
REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
MAX_BYTES = 1_000_000

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def sha(raw):
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def task_file(root, task):
    if not ID.fullmatch(task):
        raise ValueError("Invalid task identifier")
    base = Path(root)
    if base.is_symlink():
        raise ValueError("Symlinked ledger directory rejected")
    base.mkdir(parents=True, exist_ok=True)
    file = base / (task + ".jsonl")
    if file.is_symlink():
        raise ValueError("Symlinked ledger file rejected")
    return file

def require_text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError("Invalid required field: " + key)

def validate_contract(data):
    if not isinstance(data, dict) or set(data) != {"outcome", "scope", "authority", "criteria"}:
        raise ValueError("Contract fields must be outcome, scope, authority, criteria")
    for field in ("outcome", "scope", "authority"):
        require_text(data, field)
    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria or len(criteria) > 50:
        raise ValueError("At least one and no more than 50 criteria required")
    ids = set()
    for item in criteria:
        if not isinstance(item, dict) or set(item) not in ({"id", "acceptance"}, {"id", "acceptance"} | TARGET_FIELDS):
            raise ValueError("Invalid criterion shape")
        require_text(item, "acceptance")
        cid = item["id"]
        if not isinstance(cid, str) or not ID.fullmatch(cid) or cid in ids:
            raise ValueError("Invalid or repeated criterion id")
        ids.add(cid)
        if "required_evidence" in item:
            for key in ("target_revision", "subject_actor", "resource"):
                require_text(item, key)
            if not REVISION.fullmatch(item["target_revision"]):
                raise ValueError("Target revision must be a full Git object ID")
            required = item["required_evidence"]
            if (not isinstance(required, list) or not required or
                    any(not isinstance(k, str) or k not in REQUIRED_EVIDENCE for k in required)
                    or len(required) != len(set(required))):
                raise ValueError("Invalid required evidence types")

def read_events(file):
    if not file.is_file():
        raise ValueError("Task does not exist")
    lines = file.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Ledger empty")
    previous = "0" * 64
    result = []
    for number, line in enumerate(lines):
        event = json.loads(line)
        if not isinstance(event, dict) or set(event) != {"seq", "at", "kind", "payload", "prev_sha256", "sha256"}:
            raise ValueError("Invalid event shape")
        digest = event["sha256"]
        unsigned = {k:v for k,v in event.items() if k != "sha256"}
        if type(event["seq"]) is not int or event["seq"] != number or event["prev_sha256"] != previous or not isinstance(digest, str) or sha(canonical(unsigned)) != digest:
            raise ValueError("Ledger chain invalid at event " + str(number))
        if number == 0 and event["kind"] != "contract":
            raise ValueError("First event must be contract")
        previous = digest
        result.append(event)
    return result

def construct(seq, previous, kind, payload):
    row = {"seq": seq, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kind": kind, "payload": payload, "prev_sha256": previous}
    row["sha256"] = sha(canonical(row))
    return row

def emit(file, row, *, exclusive=False):
    raw = (canonical(row) + "\n").encode("utf-8")
    flags = os.O_WRONLY | (os.O_CREAT | os.O_EXCL if exclusive else os.O_APPEND)
    fd = os.open(file, flags, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)

def lock(file):
    lockfile = file.with_suffix(".lock")
    try:
        fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Task lock exists. Confirm no live writer, verify ledger integrity, then manually remove only the stale .lock file as documented.") from exc
    os.close(fd)
    return lockfile

def init(root, task, payload):
    file = task_file(root, task)
    validate_contract(payload)
    event = construct(0, "0" * 64, "contract", payload)
    emit(file, event, exclusive=True)
    return {"task": task, "event_sha256": event["sha256"], "criterion_count": len(payload["criteria"])}

def validate_evidence(payload):
    base = {"criterion_id", "status", "reference", "revision", "observation"}
    if not isinstance(payload, dict):
        raise ValueError("Invalid evidence")
    keys = set(payload)
    if keys != base:
        if not base | ATTRIBUTION <= keys or keys - base - ATTRIBUTION - {"decision", "resolves", "evidence_type"}:
            raise ValueError("Evidence fields invalid")
        for key in ATTRIBUTION:
            require_text(payload, key)
        if "evidence_type" in keys:
            if (payload["status"] not in ("blocked", "fail") or
                    not isinstance(payload["evidence_type"], str) or payload["evidence_type"] not in REQUIRED_EVIDENCE):
                raise ValueError("Invalid blocked evidence type")
        if "decision" in keys:
            if payload["status"] != "reviewed" or payload["decision"] not in (
                    "APPROVED", "CHANGES_REQUESTED", "DISMISSED", "COMMENTED"):
                raise ValueError("Invalid review decision")
        if "resolves" in keys:
            resolves = payload["resolves"]
            if (not isinstance(resolves, list) or not resolves or len(resolves) > 50 or
                    any(not isinstance(d, str) or not re.fullmatch(r"[0-9a-f]{64}", d) for d in resolves)):
                raise ValueError("Invalid resolved event digests")
    for key in base:
        require_text(payload, key)
    if payload["status"] not in OUTCOMES:
        raise ValueError("Unknown evidence status")


def append(root, task, kind, payload):
    if kind not in KINDS or not isinstance(payload, dict):
        raise ValueError("Invalid event")
    file = task_file(root, task)
    mutex = lock(file)
    try:
        events = read_events(file)
        if kind == "evidence":
            validate_evidence(payload)
            known = {c["id"] for c in events[0]["payload"]["criteria"]}
            for event in events[1:]:
                if event["kind"] == "amendment":
                    known.update(c["id"] for c in event["payload"]["criteria"])
            if payload["criterion_id"] not in known:
                raise ValueError("Unknown criterion or status")
        elif kind == "amendment":
            if set(payload) != {"reason", "authority", "criteria"}:
                raise ValueError("Amendment requires reason, authority and new criteria")
            validate_contract({"outcome": "unchanged", "scope": "unchanged", "authority": payload["authority"], "criteria": payload["criteria"]})
            require_text(payload, "reason")
            known = {c["id"] for c in events[0]["payload"]["criteria"]}
            for event in events[1:]:
                if event["kind"] == "amendment":
                    known.update(c["id"] for c in event["payload"]["criteria"])
            if any(c["id"] in known for c in payload["criteria"]):
                raise ValueError("Cannot rewrite existing acceptance criteria")
        else:
            if set(payload) != {"criterion_id", "action", "result", "reference"}:
                raise ValueError("Event fields invalid")
            for key in ("action", "result", "reference"):
                require_text(payload, key)
            if payload.get("criterion_id") is not None:
                known = {c["id"] for c in events[0]["payload"]["criteria"]}
                for event in events[1:]:
                    if event["kind"] == "amendment":
                        known.update(c["id"] for c in event["payload"]["criteria"])
                if payload["criterion_id"] not in known:
                    raise ValueError("Unknown criterion")
        row = construct(len(events), events[-1]["sha256"], kind, payload)
        emit(file, row)
        return {"task": task, "seq": row["seq"], "event_sha256": row["sha256"]}
    finally:
        mutex.unlink(missing_ok=True)

def criterion_result(task, criterion, evidence, verify_observation):
    required = criterion.get("required_evidence", [])
    confirmed = set()
    recorded = set()
    blockers = {}
    for event in evidence:
        record = event["payload"]
        kind = record["status"]
        if kind in ("fail", "blocked") or record.get("decision") in ("CHANGES_REQUESTED", "DISMISSED"):
            if kind == "reviewed":
                affected = {"reviewed"}
            elif "evidence_type" in record:
                affected = {record["evidence_type"]}
            else:
                # Legacy or unspecified failures may affect any condition.
                affected = set(required)
            confirmed.difference_update(affected)
            blockers[event["sha256"]] = {"reference": record["reference"], "outstanding": sorted(affected)}
            continue
        if (kind not in required or not ATTRIBUTION <= record.keys() or
                record["revision"] != criterion["target_revision"] or
                record["resource"] != criterion["resource"] or
                record["subject_actor"] != criterion["subject_actor"]):
            continue
        if kind == "reviewed" and (record.get("decision") != "APPROVED" or
                                   record["observed_by"] == criterion["subject_actor"]):
            continue
        recorded.add(kind)
        # Only the integrating host can authenticate an observation and its provenance.
        if verify_observation is not None and verify_observation(task, criterion, record) is True:
            confirmed.add(kind)
            for digest in record.get("resolves", []):
                blocker = blockers.get(digest)
                if blocker and kind in blocker["outstanding"] and record["reference"] != blocker["reference"]:
                    blocker["outstanding"].remove(kind)
                    if not blocker["outstanding"]:
                        del blockers[digest]
    complete = bool(required) and confirmed == set(required) and not blockers
    return {**criterion, "status": "verified" if complete else "blocked" if blockers else "unverified",
            "recorded_evidence_types": sorted(recorded), "verified_evidence_types": sorted(confirmed),
            "missing_verified_evidence": sorted(set(required) - confirmed),
            "blockers": blockers, "evidence": [e["payload"] for e in evidence], "complete": complete}


def summary(root, task, *, verify_observation=None):
    """Verify the chain locally. The optional host verifier independently checks the exact claim."""
    events = read_events(task_file(root, task))
    contract = events[0]["payload"]
    validate_contract(contract)
    criteria = {c["id"]: c for c in contract["criteria"]}
    evidence = {key: [] for key in criteria}
    attempts = {}
    for event in events[1:]:
        p = event["payload"]
        if event["kind"] == "amendment":
            validate_contract({"outcome": contract["outcome"], "scope": contract["scope"],
                               "authority": p["authority"], "criteria": p["criteria"]})
            for criterion in p["criteria"]:
                cid = criterion["id"]
                if cid in criteria:
                    raise ValueError("Cannot rewrite existing acceptance criteria")
                criteria[cid] = criterion
                evidence[cid] = []
        elif event["kind"] == "evidence":
            validate_evidence(p)
            evidence[p["criterion_id"]].append(event)
        elif event["kind"] == "attempt":
            key = (p["criterion_id"], p["action"], p["result"])
            attempts[key] = attempts.get(key, 0) + 1
    results = {cid: criterion_result(task, criterion, evidence[cid], verify_observation)
               for cid, criterion in criteria.items()}
    loops = [{"criterion_id": k[0], "action": k[1], "result": k[2], "count": n} for k,n in attempts.items() if n >= 3]
    return {"task": task, "outcome": contract["outcome"], "criteria": results,
            "event_count": len(events), "head_sha256": events[-1]["sha256"],
            "repetition_warnings": loops, "host_verifier_present": verify_observation is not None,
            "complete": all(c["complete"] for c in results.values())}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".shards/state/tasks")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("init", "record", "show", "verify"):
        p = sub.add_parser(cmd)
        p.add_argument("--task", required=True)
        if cmd in ("init", "record"):
            p.add_argument("--payload", required=True, help="Path to a UTF-8 JSON payload file")
        if cmd == "record":
            p.add_argument("--kind", choices=sorted(KINDS), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("init", "record"):
            datafile = Path(args.payload)
            if datafile.is_symlink() or datafile.stat().st_size > MAX_BYTES:
                raise ValueError("Untrusted or oversized payload")
            payload = json.loads(datafile.read_text(encoding="utf-8"))
            answer = init(args.root, args.task, payload) if args.command == "init" else append(args.root, args.task, args.kind, payload)
        else:
            answer = summary(args.root, args.task)
            if args.command == "verify" and not answer["complete"]:
                print(json.dumps(answer, indent=2))
                return 1
        print(json.dumps(answer, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError, UnicodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
