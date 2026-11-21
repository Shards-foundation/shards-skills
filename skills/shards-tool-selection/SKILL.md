---
name: shards-tool-selection
description: "Use before expensive repository or external-tool operations to select the least costly permitted route and reuse validated observations."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Tool Selection

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. List tools already connected and the exact capabilities needed for the acceptance criterion.
2. Prefer the narrowest read operation, then cached evidence only if source revision and freshness permit it.
3. Estimate tool output size and avoid full repository dumps when a file, line range or targeted search will suffice.
4. Keep source refs, target revisions and expiry in the task ledger so other agents can reuse relevant observations.
5. Escalate to a different tool only when a named failure or missing capability justifies it.

## Output contract
Return selected tool, necessary permissions, supporting evidence, freshness boundary and fallback route. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Never invent tool access, reuse expired evidence as current or ask for a credential already governed by host policy. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
