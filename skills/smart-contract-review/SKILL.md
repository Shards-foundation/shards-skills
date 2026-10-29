---
name: smart-contract-review
description: "Use when reviewing Solidity or other smart-contract code for security, economic correctness, upgradeability and operational risks."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: blockchain
status: draft
version: 0.1.0
author: Shards Foundation
---

# Smart Contract Review

## Workflow
1. Establish chain, compiler, dependencies, threat model, trust assumptions, privileged roles and asset flows.
2. Map external entry points, state transitions, invariants, callbacks and cross-contract interactions.
3. Review access control, reentrancy, arithmetic, precision/rounding, oracle assumptions, signature validation, replay protection and denial of service.
4. Inspect upgrade/admin paths, initialization, pause/emergency procedures and ownership transfer.
5. Analyse economic attacks, MEV, flash-loan composability and incentive failures where applicable.
6. Use static analysis and tests/fuzzing where tools exist; verify findings manually and propose invariant-based regression tests.
7. State deployment/compiler/configuration scope and unreviewed dependencies.

## Output contract
Return severity-ranked findings with code location, exploit preconditions, impact, evidence, remediation and tests. Include scope and explicit exclusions.

## Verification
Do not claim an audit or exploit reproduction without actual evidence. Static-tool output must be triaged; no findings is not proof of safety.

## Failure handling
If chain-specific semantics or dependencies are unknown, mark the review incomplete and identify the exact missing artefact. Never deploy or transact as part of a review without explicit authorisation.
