---
name: shards-sec-defi-protocol
description: "Shards Foundation workflow. Use before deploying or upgrading contracts, bridges, oracles, DAOs or DeFi financial mechanisms."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: blockchain
status: draft
version: 0.1.0
author: Shards Foundation
---

# Smart Contract & DeFi Protocol Assurance

## Trigger
Use before deploying or upgrading contracts, bridges, oracles, DAOs or DeFi financial mechanisms.

## Required inputs
exact chain and commit, contract addresses, upgrade model, economic assumptions and oracle sources. If essential input is unavailable, mark BLOCKED. Never request passwords, private keys or personal datasets in chat.

## Workflow
1. Document contract trust boundaries, token flows, privileged roles and external integrations.
2. Review access control, reentrancy, arithmetic, sequencing, time assumptions and failure compensation.
3. Model oracle manipulation, MEV, liquidations, insolvency, bridge failure and governance capture.
4. Use invariants, property-based tests, fuzzing and controlled fork tests with trusted tooling.
5. Review upgrades, timelocks, pauses, emergency keys and users' withdrawal paths.
6. Separate independent audit findings from fix proofs and deploy only with explicit change authority.

## Output contract
A protocol risk register, test/invariant evidence, privileges map and release blockers. Each finding includes **ID, severity, asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Absent evidence means BLOCKED. Separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,crypto --system "named system"` for consistent control selection. Collect actual evidence with scope and revision; assess using `docs/security-assurance.md`. This tool reports operator-attested results, not automated security certification.

## Failure handling
On conflicting evidence, uncertain legal applicability, unapproved effects or stale controls, return BLOCKED with the precise missing input. Never down-classify a critical failure to an informational comment.

## Authority and safe use
Audits cannot guarantee absence of exploits; do not deploy or transact on live networks automatically. The host enforces tool permissions, scope and approvals; a skill grants no authority.

## References
See `docs/security-frameworks.md` and `docs/security-assurance.md` for versioned standards and report formats. Not certified or endorsed by any standards body.
