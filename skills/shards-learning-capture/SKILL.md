---
name: shards-learning-capture
description: "Use after a repeated failure or measured improvement to preserve a compact, provenance-linked lesson for later agents."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Learning Capture

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Identify the trigger and observed event from recorded tool or test evidence.
2. Capture the actual cause separately from an unverified hypothesis.
3. State a narrowly scoped correction, counterexample, provenance, review owner and expiry/revalidation date.
4. Store a sanitized lesson in the local append-only task ledger; never include tokens or private user content.
5. Promote the correction into a shared skill only after controlled evaluation; retire lessons that stop predicting better outcomes.

## Output contract
Return one compact lesson with trigger, evidence, cause, correction, limitations, expiry and ownership. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Reject anecdotes as causal proof, permanent policy changes without review and secrets in saved context. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
