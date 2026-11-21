---
name: shards-progress-control
description: "Use during multi-step work to detect loops, scope creep and no-evidence retries while keeping the next action focused."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Progress Control

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. For each attempt record criterion ID, action fingerprint, observed result, evidence reference and whether new information was produced.
2. Detect repetition of the same failed action with no new evidence; change hypothesis, route or report a concrete blocker.
3. Enforce a bounded retry budget per action and respect time, token and permission constraints.
4. Stop expanding work when all original acceptance criteria have verified evidence.
5. If blocked, report the exact unmet prerequisite rather than filling time with unrelated work.

## Output contract
Return current criterion, distinct attempts, progress signal, blocker and one next action. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Do not change the task contract, create extra PRs or claim progress based on repeated tool calls. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
