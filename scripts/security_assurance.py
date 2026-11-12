#!/usr/bin/env python3
"""Offline Shards security-assurance planning and evidence triage; NOT a scanner or certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalogue" / "shards-security-controls.json"
MAX_INPUT_BYTES = 1_000_000
SAFE_ID = re.compile(r"^[A-Z]{2,4}-[0-9]{2}$")
SAFE_TEXT = re.compile(r"^[^\x00-\x08\x0b\x0c\x0e-\x1f]{1,500}$")
DANGEROUS = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})", re.I)
VERDICTS = {"pass", "fail", "not_applicable"}

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def read_json(path: Path) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Input must be a regular non-symlink file")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds size limit")
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object")
    return payload, sha(raw)

def require_text(value: object, what: str) -> str:
    if not isinstance(value, str) or not SAFE_TEXT.fullmatch(value.strip()) or DANGEROUS.search(value):
        raise ValueError("Missing, unsafe or excessive text for " + what)
    return value.strip()

def registry() -> tuple[dict, str]:
    data, registry_sha = read_json(REGISTRY)
    if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), list) or not isinstance(data.get("controls"), list):
        raise ValueError("Unsupported control registry")
    profiles = data["profiles"]
    if not profiles or "base" not in profiles or any(not isinstance(p, str) or not p.isidentifier() for p in profiles) or len(profiles) != len(set(profiles)):
        raise ValueError("Invalid profile registry")
    seen = set()
    for c in data["controls"]:
        if not isinstance(c, dict) or set(c) != {"id", "profile", "title", "severity", "evidence", "framework"}:
            raise ValueError("Malformed control record")
        cid = c["id"]
        if not isinstance(cid, str) or not SAFE_ID.fullmatch(cid) or cid in seen or c["profile"] not in profiles or c["severity"] not in ("critical", "high", "medium", "low"):
            raise ValueError("Duplicate, unknown or unsafe control")
        for name in ("title", "evidence", "framework"):
            require_text(c[name], name)
        seen.add(cid)
    return data, registry_sha

def profile_selection(raw: object, names: list[str]) -> list[str]:
    if isinstance(raw, str):
        values = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, list):
        values = raw
    else:
        raise ValueError("Profiles must be a comma-separated string or list")
    if not values or any(not isinstance(v, str) or v not in names for v in values):
        raise ValueError("Unknown or missing control profile")
    if len(values) != len(set(values)):
        raise ValueError("Repeated profile")
    return ["base"] + sorted(v for v in values if v != "base")

def selection(controls: list[dict], chosen: list[str]) -> list[dict]:
    return sorted((c for c in controls if c["profile"] in chosen), key=lambda c: c["id"])

def plan(data: dict, registry_sha: str, system: str, profiles: str) -> dict:
    owner_system = require_text(system, "system")
    selected = profile_selection(profiles, data["profiles"])
    controls = selection(data["controls"], selected)
    return {"schema_version": 1, "system": owner_system, "profiles": selected,
            "registry_sha256": registry_sha, "control_count": len(controls), "controls": controls,
            "note": "Proposed control checklist only; no tests performed, no compliance established."}

def assess(data: dict, registry_sha: str, payload: dict, input_sha: str) -> dict:
    if set(payload) != {"schema_version", "scope", "observations"} or payload["schema_version"] != 1:
        raise ValueError("Assessment must contain exactly schema_version, scope, observations")
    scope = payload["scope"]
    if not isinstance(scope, dict) or set(scope) != {"system", "owner", "jurisdictions", "revision", "environment", "authorised_scope", "profiles"}:
        raise ValueError("Invalid assessment scope")
    for field in ("system", "owner", "revision", "environment", "authorised_scope"):
        require_text(scope[field], field)
    if not isinstance(scope["jurisdictions"], list) or not scope["jurisdictions"] or len(scope["jurisdictions"]) > 20:
        raise ValueError("Jurisdictions must be non-empty and bounded")
    for country in scope["jurisdictions"]:
        require_text(country, "jurisdiction")
    chosen = profile_selection(scope["profiles"], data["profiles"])
    chosen_controls = selection(data["controls"], chosen)
    selected_by_id = {c["id"]: c for c in chosen_controls}
    observations = payload["observations"]
    if not isinstance(observations, list) or len(observations) > len(chosen_controls):
        raise ValueError("Invalid observation count")
    lookup = {}
    for item in observations:
        if not isinstance(item, dict) or set(item) != {"control_id", "status", "reference", "revision", "observation", "approver"}:
            raise ValueError("Invalid observation schema")
        cid = item["control_id"]
        if not isinstance(cid, str) or cid not in selected_by_id or cid in lookup or item["status"] not in VERDICTS:
            raise ValueError("Unknown, duplicate or invalid control status")
        for f in ("reference", "revision", "observation"):
            require_text(item[f], f)
        if item["revision"] != scope["revision"]:
            raise ValueError("Evidence revision does not match assessed revision")
        if item["status"] == "not_applicable":
            require_text(item["approver"], "not-applicable approver")
        elif item["approver"] is not None:
            require_text(item["approver"], "approver")
        lookup[cid] = item
    counts = {"reported_pass": 0, "fail": 0, "blocked": 0, "not_applicable": 0}
    results = []
    for c in chosen_controls:
        item = lookup.get(c["id"])
        if item is None:
            status, cause = "BLOCKED", "Missing evidence"
            counts["blocked"] += 1
        elif item["status"] == "fail":
            status, cause = "FAIL", "Operator-reported failed control"
            counts["fail"] += 1
        elif item["status"] == "not_applicable":
            if c["severity"] == "critical":
                status, cause = "BLOCKED", "Critical control cannot be excluded automatically"
                counts["blocked"] += 1
            else:
                status, cause = "NOT_APPLICABLE_REVIEW", "Exclusion requires independent validation"
                counts["not_applicable"] += 1
        else:
            status, cause = "REPORTED_PASS", "Self-attested; verify attached evidence independently"
            counts["reported_pass"] += 1
        results.append({"id": c["id"], "severity": c["severity"], "title": c["title"],
                        "status": status, "reason": cause,
                        "evidence_reference": item["reference"] if item else None,
                        "observed_revision": item["revision"] if item else None})
    # An external reviewer must independently validate sources and jurisdiction.
    verdict = "REVIEW_READY_NOT_CERTIFIED" if not counts["blocked"] and not counts["fail"] else "HOLD"
    return {"schema_version": 1, "system": scope["system"], "profiles": chosen, "jurisdictions": scope["jurisdictions"],
            "registry_sha256": registry_sha, "input_sha256": input_sha, "revision": scope["revision"],
            "assessment": "operator-attested-only", "verdict": verdict,
            "counts": counts, "controls": results,
            "warning": "Does not establish security, legal compliance, production readiness or independent audit assurance."}

def emit(value: dict, output: str | None) -> None:
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        destination = Path(output)
        if destination.is_symlink():
            raise ValueError("Symlinked output rejected")
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(data)
    print(data, end="")

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    pp = sub.add_parser("plan")
    pp.add_argument("--profiles", required=True)
    pp.add_argument("--system", required=True)
    pp.add_argument("--output")
    ap = sub.add_parser("assess")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        data, registry_sha = registry()
        if args.action == "list":
            emit({"profiles": data["profiles"], "control_count": len(data["controls"]), "registry_sha256": registry_sha}, None)
            return 0
        if args.action == "plan":
            emit(plan(data, registry_sha, args.system, args.profiles), args.output)
            return 0
        payload, input_sha = read_json(Path(args.input))
        report = assess(data, registry_sha, payload, input_sha)
        emit(report, args.output)
        return 0 if report["verdict"] == "REVIEW_READY_NOT_CERTIFIED" else 1
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
