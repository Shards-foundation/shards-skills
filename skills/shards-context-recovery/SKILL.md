---
name: shards-context-recovery
description: "Use after interruptions, session changes or agent handovers to restore a task from durable records and revalidate changing facts."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Context Recovery

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Load the existing task ID and latest append-only ledger events instead of reconstructing history from model memory.
2. Reconcile recorded branch, commit, PR and checks with current repository state; flag any stale evidence.
3. Preserve the original acceptance criteria, approvals, previous failures and reviewer findings.
4. Recover exactly one next action; do not restart completed work or repeat approved decisions.
5. Record a checkpoint with observed changes, blocker and current commit before handing over.

## Output contract
Return what was requested, what is done, what remains, what is verified, and the next authorised action. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Block action when ownership, authorisation, identity or source state cannot be reverified. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
