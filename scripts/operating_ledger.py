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
    if set(data) != {"outcome", "scope", "authority", "criteria"}:
        raise ValueError("Contract fields must be outcome, scope, authority, criteria")
    for field in ("outcome", "scope", "authority"):
        require_text(data, field)
    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria or len(criteria) > 50:
        raise ValueError("At least one and no more than 50 criteria required")
    ids = set()
    for item in criteria:
        if not isinstance(item, dict) or set(item) != {"id", "acceptance"}:
            raise ValueError("Invalid criterion shape")
        require_text(item, "acceptance")
        cid = item["id"]
        if not isinstance(cid, str) or not ID.fullmatch(cid) or cid in ids:
            raise ValueError("Invalid or repeated criterion id")
        ids.add(cid)

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
    fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    return lockfile

def init(root, task, payload):
    file = task_file(root, task)
    validate_contract(payload)
    event = construct(0, "0" * 64, "contract", payload)
    emit(file, event, exclusive=True)
    return {"task": task, "event_sha256": event["sha256"], "criterion_count": len(payload["criteria"])}

def append(root, task, kind, payload):
    if kind not in KINDS or not isinstance(payload, dict):
        raise ValueError("Invalid event")
    file = task_file(root, task)
    mutex = lock(file)
    try:
        events = read_events(file)
        if kind == "evidence":
            if set(payload) != {"criterion_id", "status", "reference", "revision", "observation"}:
                raise ValueError("Evidence fields invalid")
            known = {c["id"] for c in events[0]["payload"]["criteria"]}
            for event in events[1:]:
                if event["kind"] == "amendment":
                    known.update(c["id"] for c in event["payload"]["criteria"])
            if payload.get("criterion_id") not in known or payload.get("status") not in OUTCOMES:
                raise ValueError("Unknown criterion or status")
            for key in ("reference", "revision", "observation"):
                require_text(payload, key)
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

def summary(root, task):
    events = read_events(task_file(root, task))
    criteria = {c["id"]: {"acceptance": c["acceptance"], "status": "unverified"} for c in events[0]["payload"]["criteria"]}
    attempts = {}
    for event in events[1:]:
        p = event["payload"]
        if event["kind"] == "amendment":
            criteria.update({c["id"]: {"acceptance": c["acceptance"], "status": "unverified"} for c in p["criteria"]})
        elif event["kind"] == "evidence":
            criteria[p["criterion_id"]].update({"status": p["status"], "reference": p["reference"], "revision": p["revision"]})
        elif event["kind"] == "attempt":
            key = (p["criterion_id"], p["action"], p["result"])
            attempts[key] = attempts.get(key, 0) + 1
    loops = [{"criterion_id": k[0], "action": k[1], "result": k[2], "count": n} for k,n in attempts.items() if n >= 3]
    return {"task": task, "outcome": events[0]["payload"]["outcome"], "criteria": criteria,
            "event_count": len(events), "head_sha256": events[-1]["sha256"],
            "repetition_warnings": loops,
            "complete": all(c["status"] in ("tested", "reviewed", "deployed", "production-verified") and c.get("reference") for c in criteria.values())}

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
