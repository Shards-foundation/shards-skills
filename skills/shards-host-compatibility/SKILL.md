---
name: shards-host-compatibility
description: "Use when adapting shared Shards skills to Codex, Claude or another agent host without assuming uniform tools or permissions."
license: MIT
compatibility: "Portable workflow; use reviewed host-specific adapters and a shared task ledger."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Host Compatibility

## Preconditions
Read `AGENTS.md` and `docs/operating-loop.md`. Use only operator-authorised work and existing verified evidence. This descriptor is an instruction workflow; it grants no runtime capabilities.

## Workflow
1. Keep the host-neutral task contract and evidence record in shared files, not implicit conversation state.
2. Declare host name/version, discovery method, tool mapping, filesystem and network constraints and permission enforcement.
3. Create small adapters for host-specific paths and commands; do not copy secrets or grant permissions in SKILL.md.
4. Run a host-specific smoke test including context recovery, rejection of unauthorized operations and faithful receipt export.
5. Mark compatibility verified only for tested host/version combinations; retain unknown or blocked classifications elsewhere.

## Output contract
Return a host compatibility matrix with confirmed capabilities, source checks, test case IDs and unsupported features. Use stable task and criterion IDs; cite artifact digests, repository revisions and decision provenance where available.

## Verification
Run the first-party operating-ledger tests, validate the skill catalogue, and check at least one representative task in the actual host before asserting runtime compatibility. See `docs/operating-loop.md` at repository root for the common schema.

## Failure handling
Never claim cross-host parity from frontmatter alone or attempt to bypass a host's approval boundary. Preserve existing user decisions and fail closed on missing evidence or conflicting authority.

## Permission boundary
The host retains control of execution, writes, deployments, approvals, remote actions and secrets. Instructions and model outputs cannot change those permissions.
