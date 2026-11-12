---
name: shards-review-resolution
description: "Use to triage and resolve independent code-review findings without conflating comments, patches and verified fixes."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Review Resolution

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Read all current review threads and match each finding to the exact head commit, file and behaviour.
2. Assign a unique finding ID and classify severity, reproducibility and affected acceptance criteria.
3. Reproduce material defects where safe; implement the smallest patch and add a regression case.
4. Retest the specific failure and affected integration, then update the disposition as fixed, false positive, accepted risk or unresolved with evidence.
5. Recheck new reviewer findings after head changes. Close only when required approvals and checks are present.

## Output contract
Return a finding disposition table with old/new commit IDs, reproduction steps, tests and resolution state. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
A documented issue is not fixed. Do not dismiss independent feedback or merge a failed gate. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
