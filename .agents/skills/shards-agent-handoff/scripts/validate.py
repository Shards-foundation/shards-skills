#!/usr/bin/env python3
"""Offline schema validation for a versioned, lossless Shards checkpoint.

Validates structure and sanitisation; intentionally does NOT verify authority,
remote evidence, signatures, live permissions or the truth of claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SHA40 = re.compile(r"[a-fA-F0-9]{40}\Z")
SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)", re.I)
SENSITIVE_FIELD = re.compile(r"(?:^|_)(?:password|private_key|secret|access_token|api_key)(?:$|_)", re.I)
ALLOWED_DECISIONS = {"CONTINUE", "HOLD", "ESCALATE", "CLOSED"}
ALLOWED_CLAIMS = {"REPORTED", "OBSERVED", "INDEPENDENTLY_VERIFIED"}
ALLOWED_LOCATORS = {"github_commit", "github_check_run", "github_review", "local_artifact", "synthetic", "unavailable"}
ALLOWED_SOURCE_KINDS = {"executor_report", "local_artifact", "git_commit", "ci_run", "pull_request_review", "synthetic"}
MAX_FILE = 256_000

class Invalid(ValueError):
    pass

def fail(where: str, message: str) -> None:
    raise Invalid(f"{where}: {message}")

def obj(x, where):
    if type(x) is not dict:
        fail(where, "expected object")
    return x

def required_str(v, where):
    if type(v) is not str or not v.strip():
        fail(where, "required non-empty string")
    if len(v) > 10_000:
        fail(where, "string exceeds limit")
    return v

def arrays(v, where):
    if type(v) is not list or len(v) > 1000:
        fail(where, "expected array of at most 1000 elements")
    for i, x in enumerate(v):
        required_str(x, f"{where}[{i}]")
    return v

def time_iso(v, where):
    v = required_str(v, where)
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        fail(where, "invalid ISO-8601 timestamp")
    if dt.tzinfo is None or dt.utcoffset() is None:
        fail(where, "timestamp must include UTC offset")

def sha(v, where, nullable=False):
    if nullable and v is None:
        return
    if type(v) is not str or not SHA40.fullmatch(v):
        fail(where, "must be a full 40-character Git commit SHA or null when unavailable")

def digest(v, where):
    if v is not None and (type(v) is not str or not SHA256.fullmatch(v)):
        fail(where, "must be 64-character SHA-256 or null")

def clean_content(x, where="$", depth=0):
    if depth > 128:
        fail(where, "maximum nesting depth exceeded")
    if type(x) is dict:
        for k,v in x.items():
            if type(k) is not str or SENSITIVE_FIELD.search(k):
                fail(where, "sensitive or invalid field name")
            clean_content(v, f"{where}.{k}", depth+1)
    elif type(x) is list:
        for i,v in enumerate(x):
            clean_content(v, f"{where}[{i}]", depth+1)
    elif type(x) is str and SECRET.search(x):
        fail(where, "potential credential pattern detected")

def decode_without_duplicate_keys(raw: str):
    def no_dups(pairs):
        result={}
        for k,v in pairs:
            if k in result:
                raise Invalid(f"duplicate JSON field: {k}")
            result[k]=v
        return result
    try:
        return json.loads(raw, object_pairs_hook=no_dups, parse_constant=lambda c: fail("JSON", "nonfinite number"))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as e:
        raise Invalid(f"invalid JSON: {e}") from e

def validate(c):
    c=obj(c, "checkpoint")
    clean_content(c)
    if c.get("schema_version") != "shards-handoff/1.0":
        fail("schema_version", "expected shards-handoff/1.0")
    for k in ("task_id", "goal", "task_owner", "executor", "observed_at"):
        required_str(c.get(k),k)
    time_iso(c["observed_at"], "observed_at")
    auth=obj(c.get("authority"), "authority")
    required_str(auth.get("basis"), "authority.basis")
    arrays(auth.get("allowed"), "authority.allowed")
    arrays(auth.get("prohibited"), "authority.prohibited")
    if "expires_at" in auth and auth["expires_at"] is not None:
        time_iso(auth["expires_at"], "authority.expires_at")
    targets=c.get("targets")
    if type(targets) is not list or not 1 <= len(targets) <= 30:
        fail("targets", "expected 1..30 target objects")
    unknown_revision=False
    for i,t in enumerate(targets):
        t=obj(t,f"targets[{i}]")
        required_str(t.get("repository"),f"targets[{i}].repository")
        if t.get("branch") is not None:
            required_str(t["branch"],f"targets[{i}].branch")
        if "commit_sha" not in t:
            fail(f"targets[{i}].commit_sha", "required field; use null with UNKNOWN status when unavailable")
        sha(t.get("commit_sha"),f"targets[{i}].commit_sha",nullable=True)
        if t.get("commit_sha") is None:
            unknown_revision=True
        if t.get("revision_status") not in {"KNOWN", "UNKNOWN"}:
            fail(f"targets[{i}].revision_status","must be KNOWN or UNKNOWN")
        if (t.get("commit_sha") is None) != (t["revision_status"]=="UNKNOWN"):
            fail(f"targets[{i}]", "revision_status and commit_sha disagree")
    progress=obj(c.get("progress"),"progress")
    for k in ("executed", "adjudicated", "exported", "pending"):
        arrays(progress.get(k), f"progress.{k}")
    records=c.get("evidence")
    if type(records) is not list or len(records)>1000:
        fail("evidence","expected array up to 1000")
    ids=set(); reported=0; verified_claims=0
    for i,e in enumerate(records):
        w=f"evidence[{i}]"; e=obj(e,w)
        eid=required_str(e.get("id"),f"{w}.id")
        if eid in ids:
            fail(w,"duplicate evidence id")
        ids.add(eid)
        required_str(e.get("claim"),f"{w}.claim")
        if e.get("source_kind") not in ALLOWED_SOURCE_KINDS:
            fail(w,"unknown source_kind")
        if e.get("claim_level") not in ALLOWED_CLAIMS:
            fail(w,"unknown claim_level")
        level=e["claim_level"]
        reported+=level=="REPORTED"
        verified_claims+=level=="INDEPENDENTLY_VERIFIED"
        subj=obj(e.get("subject"),f"{w}.subject")
        required_str(subj.get("actor"),f"{w}.subject.actor")
        required_str(subj.get("operation"),f"{w}.subject.operation")
        if "revision_sha" not in subj:
            fail(f"{w}.subject.revision_sha", "required field; use null when revision is unknown")
        sha(subj.get("revision_sha"),f"{w}.subject.revision_sha",nullable=True)
        loc=obj(e.get("locator"),f"{w}.locator")
        if loc.get("kind") not in ALLOWED_LOCATORS:
            fail(w,"unknown locator kind")
        if loc.get("kind") not in {"synthetic", "unavailable"}:
            required_str(loc.get("value"),f"{w}.locator.value")
        elif loc.get("value") is not None:
            required_str(loc["value"],f"{w}.locator.value")
        digest(e.get("digest_sha256"),f"{w}.digest_sha256")
        time_iso(e.get("observed_at"),f"{w}.observed_at")
        if level=="INDEPENDENTLY_VERIFIED":
            if loc["kind"] in {"synthetic","unavailable"} or subj.get("revision_sha") is None:
                fail(w,"independently verified claim requires non-synthetic locator and pinned subject revision")
            if loc["kind"]=="local_artifact" and e.get("digest_sha256") is None:
                fail(w,"independently verified local artifact requires digest")
    arrays(c.get("blockers"),"blockers")
    nxt=obj(c.get("next"),"next")
    required_str(nxt.get("owner"),"next.owner")
    required_str(nxt.get("action"),"next.action")
    arrays(nxt.get("evidence_required"),"next.evidence_required")
    if nxt.get("decision") not in ALLOWED_DECISIONS:
        fail("next.decision", "invalid decision")
    if unknown_revision and nxt["decision"] in {"CONTINUE","CLOSED"}:
        fail("next.decision", "unknown target revision requires HOLD or ESCALATE")
    if nxt["decision"]=="CLOSED" and (c["blockers"] or progress["pending"] or not records):
        fail("next.decision", "closure conflicts with blockers, pending work or absent evidence")
    return {"schema_version":c["schema_version"],"task_id":c["task_id"],"claimed_evidence_count":len(records),"reported_only_count":reported,"independently_verified_claim_count":verified_claims,"unknown_target_revisions":unknown_revision,"decision_claim":nxt["decision"],"schema_valid":True,"external_evidence_verified":False,"authority_verified":False,"execution_authorised":False,"warning":"Schema validation only. Evidence labels and authority are claims; independently re-fetch sources before acting."}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        p=args.input
        if not p.is_file() or p.stat().st_size>MAX_FILE:
            fail("input","missing or too large")
        raw=p.read_bytes(); c=decode_without_duplicate_keys(raw.decode("utf-8"))
        summary=validate(c)
        result={"validation":summary,"checkpoint":c,"checkpoint_sha256":hashlib.sha256(raw).hexdigest()}
        dest=args.output
        if dest.is_symlink() or dest.exists():
            fail("output","already exists; never overwrite or follow symlink")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True,ensure_ascii=False)
            f.write("\n")
        print(json.dumps({"result":"SCHEMA_VALID","output":str(dest),**summary},sort_keys=True))
        return 0
    except (Invalid,OSError,ValueError,UnicodeError,RecursionError,KeyError,TypeError) as e:
        print("BLOCKED: "+str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
