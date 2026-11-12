---
name: shards-task-contract
description: "Use when starting or resuming work to pin the requested outcome, authorised scope and stable acceptance criteria before tools are used."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Task Contract

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Capture task ID, requested outcome, in-scope and out-of-scope actions, existing authorisation and evidence required for completion.
2. Establish immutable acceptance criteria IDs before implementation. Record changes as explicit amendments, never silently overwrite the original.
3. Assign one next action and a stop condition. If the desired output is already complete, report evidence and stop.
4. Every additional task, PR or release must map to an existing criterion or a separately approved amendment.
5. Use the operating ledger CLI to create a task record and record criterion results.

## Output contract
Return a task contract with stable acceptance criteria, authority boundaries, next action and halt conditions. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Reject uncontrolled scope growth, vague success definitions and retrospective edits to original criteria. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
