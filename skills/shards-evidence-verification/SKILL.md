---
name: shards-evidence-verification
description: "Use before reporting completion to tie each acceptance criterion to observable artifacts and distinguish deployment from local tests."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Evidence Verification

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Inspect the original task contract and exact criterion identifiers.
2. Classify each result as proposed, implemented, tested, reviewed, deployed or production-verified; keep states distinct.
3. Pin commit, check-run, artifact digest, URL or runtime evidence and timestamp for every pass claim.
4. Treat missing, stale or contradictory evidence as unverified; record FAIL or BLOCKED with a clear cause.
5. Present a criterion-by-criterion verdict, remaining blockers and whether the requested task is actually complete.

## Output contract
Return a criterion evidence matrix with source, revision, observation, status, and outstanding work. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Do not equate CI green with production deployment or use another agent's narrative as independent verification. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
