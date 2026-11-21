#!/usr/bin/env python3
"""Offline schema validation for a versioned, lossless Shards checkpoint.

Validates structure and sanitisation; intentionally does NOT verify authority,
remote evidence, signatures, live permissions or the truth of claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

GIT_REVISION = re.compile(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\Z")
SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
SECRET = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|xox[baprs]-[\w-]{10,}|Bearer\s+\S+|"
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.I,
)
SENSITIVE_FIELD = re.compile(
    r"(?:^|_)(?:password|passwd|private_key|secret|[a-z]*token|api_key|auth|authorization|"
    r"cookie|credentials?|signature|email|phone|ssn)(?:$|_)", re.I,
)
URL = re.compile(r"[a-z][a-z0-9+.-]*://[^\s<>\"']+", re.I)
CHECKPOINT_PREFIX = b'{"checkpoint":'
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
    if type(v) is not str or not GIT_REVISION.fullmatch(v):
        fail(where, "must be a full 40- or 64-character Git commit SHA or null when unavailable")

def digest(v, where):
    if v is not None and (type(v) is not str or not SHA256.fullmatch(v)):
        fail(where, "must be 64-character SHA-256 or null")

def sensitive_field(name):
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return SENSITIVE_FIELD.search(re.sub(r"[^a-zA-Z0-9]+", "_", name))

def sensitive_value(value):
    if SECRET.search(value):
        return True
    for match in URL.finditer(value):
        try:
            url = urlsplit(match.group())
            if "@" in url.netloc or any(
                sensitive_field(key) or SECRET.search(item)
                for key, item in parse_qsl(url.query, keep_blank_values=True)
            ):
                return True
        except ValueError:
            return True
    return False

def clean_content(x, where="$", depth=0):
    if depth > 128:
        fail(where, "maximum nesting depth exceeded")
    if type(x) is dict:
        for k,v in x.items():
            if type(k) is not str or sensitive_field(k) or sensitive_value(k):
                fail(where, "sensitive or invalid field name")
            clean_content(v, f"{where}.{k}", depth+1)
    elif type(x) is list:
        for i,v in enumerate(x):
            clean_content(v, f"{where}[{i}]", depth+1)
    elif type(x) is str and sensitive_value(x):
        fail(where, "potential credential pattern detected")
    elif type(x) in (float, Decimal) and not math.isfinite(x):
        fail(where, "nonfinite number")

def decode_without_duplicate_keys(raw: str):
    def no_dups(pairs):
        result={}
        for k,v in pairs:
            if k in result:
                raise Invalid("duplicate JSON field")
            result[k]=v
        return result
    try:
        return json.loads(raw, object_pairs_hook=no_dups, parse_float=Decimal,
                          parse_constant=lambda c: fail("JSON", "nonfinite number"))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as e:
        raise Invalid(f"invalid JSON: {e}") from e

def restrict_fields(record, allowed, where):
    if record.keys() - allowed:
        fail(where, "unreviewed metadata field")

def validate(c, *, metadata=frozenset()):
    c=obj(c, "checkpoint")
    clean_content(c)
    restrict_fields(c, {"schema_version", "task_id", "goal", "task_owner", "executor", "observed_at",
                        "authority", "targets", "progress", "evidence", "blockers", "next"} | metadata, "checkpoint")
    if c.get("schema_version") != "shards-handoff/1.0":
        fail("schema_version", "expected shards-handoff/1.0")
    for k in ("task_id", "goal", "task_owner", "executor", "observed_at"):
        required_str(c.get(k),k)
    time_iso(c["observed_at"], "observed_at")
    auth=obj(c.get("authority"), "authority")
    restrict_fields(auth, {"basis", "allowed", "prohibited", "expires_at"}, "authority")
    required_str(auth.get("basis"), "authority.basis")
    arrays(auth.get("allowed"), "authority.allowed")
    arrays(auth.get("prohibited"), "authority.prohibited")
    if "expires_at" in auth and auth["expires_at"] is not None:
        time_iso(auth["expires_at"], "authority.expires_at")
    targets=c.get("targets")
    if type(targets) is not list or not 1 <= len(targets) <= 30:
        fail("targets", "expected 1..30 target objects")
    unknown_revision=False
    target_revisions = set()
    for i,t in enumerate(targets):
        t=obj(t,f"targets[{i}]")
        restrict_fields(t, {"repository", "branch", "commit_sha", "revision_status"}, f"targets[{i}]")
        required_str(t.get("repository"),f"targets[{i}].repository")
        if "branch" not in t:
            fail(f"targets[{i}].branch", "required field; use null for a detached revision")
        if t.get("branch") is not None:
            required_str(t["branch"],f"targets[{i}].branch")
        if "commit_sha" not in t:
            fail(f"targets[{i}].commit_sha", "required field; use null with UNKNOWN status when unavailable")
        sha(t.get("commit_sha"),f"targets[{i}].commit_sha",nullable=True)
        if t.get("commit_sha") is None:
            unknown_revision=True
        else:
            target_revisions.add(t["commit_sha"].lower())
        if t.get("revision_status") not in {"KNOWN", "UNKNOWN"}:
            fail(f"targets[{i}].revision_status","must be KNOWN or UNKNOWN")
        if (t.get("commit_sha") is None) != (t["revision_status"]=="UNKNOWN"):
            fail(f"targets[{i}]", "revision_status and commit_sha disagree")
    progress=obj(c.get("progress"),"progress")
    restrict_fields(progress, {"executed", "adjudicated", "exported", "pending"}, "progress")
    for k in ("executed", "adjudicated", "exported", "pending"):
        arrays(progress.get(k), f"progress.{k}")
    records=c.get("evidence")
    if type(records) is not list or len(records)>1000:
        fail("evidence","expected array up to 1000")
    ids=set(); reported=0; verified_claims=0
    for i,e in enumerate(records):
        w=f"evidence[{i}]"; e=obj(e,w)
        restrict_fields(e, {"id", "claim", "source_kind", "claim_level", "subject", "locator",
                            "digest_sha256", "observed_at"}, w)
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
        restrict_fields(subj, {"actor", "operation", "revision_sha"}, f"{w}.subject")
        required_str(subj.get("actor"),f"{w}.subject.actor")
        required_str(subj.get("operation"),f"{w}.subject.operation")
        if "revision_sha" not in subj:
            fail(f"{w}.subject.revision_sha", "required field; use null when revision is unknown")
        sha(subj.get("revision_sha"),f"{w}.subject.revision_sha",nullable=True)
        loc=obj(e.get("locator"),f"{w}.locator")
        restrict_fields(loc, {"kind", "value"}, f"{w}.locator")
        if loc.get("kind") not in ALLOWED_LOCATORS:
            fail(w,"unknown locator kind")
        if loc.get("kind") not in {"synthetic", "unavailable"}:
            required_str(loc.get("value"),f"{w}.locator.value")
        elif loc.get("value") is not None:
            required_str(loc["value"],f"{w}.locator.value")
        digest(e.get("digest_sha256"),f"{w}.digest_sha256")
        time_iso(e.get("observed_at"),f"{w}.observed_at")
        if level=="INDEPENDENTLY_VERIFIED":
            revision = subj["revision_sha"]
            if (e["source_kind"] == "synthetic" or loc["kind"] in {"synthetic", "unavailable"}
                    or revision is None or revision.lower() not in target_revisions):
                fail(w, "independently verified claim requires a real source and a pinned target revision")
            if loc["kind"]=="local_artifact" and e.get("digest_sha256") is None:
                fail(w,"independently verified local artifact requires digest")
    arrays(c.get("blockers"),"blockers")
    nxt=obj(c.get("next"),"next")
    restrict_fields(nxt, {"owner", "action", "decision", "evidence_required"}, "next")
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

def read_checkpoint(path: Path) -> bytes:
    def open_regular(name, flags):
        return os.open(name, flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))

    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
        fail("input", "expected a bounded regular file")
    with open(path, "rb", opener=open_regular) as stream:
        opened = os.fstat(stream.fileno())
        if not os.path.samestat(before, opened):
            fail("input", "file changed before reading")
        raw = stream.read(MAX_FILE + 1)
        after = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            fail("input", "file changed during reading")
    if len(raw) > MAX_FILE:
        fail("input", "file exceeds size limit")
    return raw


def open_output_directory(path: Path) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not {os.open, os.mkdir, os.link, os.unlink, os.rmdir}.issubset(os.supports_dir_fd):
        fail("output", "protected checkpoint writes require POSIX directory descriptors")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, flags, dir_fd=directory)
            except FileNotFoundError:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
                os.fsync(directory)
                child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory
    except BaseException:
        os.close(directory)
        raise


def write_checkpoint(path: Path, data: bytes) -> list[str]:
    path = path.absolute()
    if path.resolve() != path:
        fail("output", "destination must be canonical and contain no symlinks")
    directory = open_output_directory(path.parent)
    staging = ".handoff-" + uuid.uuid4().hex
    staging_fd = None
    created_directory = created_file = published = False
    warnings = []
    try:
        os.mkdir(staging, mode=0o700, dir_fd=directory)
        created_directory = True
        staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
        identity = os.fstat(staging_fd)
        if identity.st_uid != os.geteuid() or stat.S_IMODE(identity.st_mode) & 0o077:
            fail("output", "staging directory must be private")
        file_fd = os.open("checkpoint.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=staging_fd)
        created_file = True
        with os.fdopen(file_fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if not os.path.samestat(os.fstat(directory), path.parent.lstat()):
            fail("output", "destination directory changed before publication")
        os.link("checkpoint.json", path.name, src_dir_fd=staging_fd, dst_dir_fd=directory)
        published = True
        try:
            same_directory = os.path.samestat(os.fstat(directory), path.parent.lstat())
        except OSError:
            same_directory = False
        if not same_directory:
            warnings.append("Output created in the original directory. Its path changed during publication.")
        try:
            os.fsync(directory)
        except OSError:
            warnings.append("Output created. Directory sync failed, so durability is unconfirmed.")
    finally:
        try:
            if created_file:
                os.unlink("checkpoint.json", dir_fd=staging_fd)
            if created_directory:
                os.rmdir(staging, dir_fd=directory)
        except OSError:
            if published:
                warnings.append("Output created. Private staging cleanup failed.")
        finally:
            if staging_fd is not None:
                os.close(staging_fd)
            os.close(directory)
    return warnings


def checkpoint_output(raw: bytes, summary: dict) -> bytes:
    checkpoint = raw.strip(b" \t\r\n")
    metadata = {"validation": summary, "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest()}
    return CHECKPOINT_PREFIX + checkpoint + b"," + json.dumps(metadata, sort_keys=True).encode("utf-8")[1:] + b"\n"


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--confirm-sanitised", action="store_true", required=True,
                    help="confirm the task owner reviewed all values for sensitive content")
    ap.add_argument("--allow-metadata-field", action="append", default=[], metavar="KEY",
                    help="preserve one explicitly reviewed, safe top-level extension")
    args=ap.parse_args(argv)
    try:
        raw = read_checkpoint(args.input)
        c = decode_without_duplicate_keys(raw.decode("utf-8"))
        summary=validate(c, metadata=frozenset(args.allow_metadata_field))
        warnings = write_checkpoint(args.output, checkpoint_output(raw, summary))
    except (ValueError, RuntimeError, KeyError, TypeError, ArithmeticError) as e:
        print("BLOCKED: " + str(e), file=sys.stderr)
        return 2
    except OSError:
        print("BLOCKED: could not read the input or publish an exclusive checkpoint", file=sys.stderr)
        return 2
    try:
        print(json.dumps({"result": "SCHEMA_VALID", "output": str(args.output), "warnings": warnings, **summary},
                         sort_keys=True), flush=True)
    except OSError:
        # A broken status stream cannot undo a successfully linked checkpoint.
        try:
            with open(os.devnull, "w") as discard:
                os.dup2(discard.fileno(), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    return 0

if __name__=="__main__":
    raise SystemExit(main())
