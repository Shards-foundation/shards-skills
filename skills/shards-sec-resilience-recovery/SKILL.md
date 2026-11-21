---
name: shards-sec-resilience-recovery
description: "Shards Foundation workflow. Use for payment, crypto, SaaS, AI or enterprise critical services needing recovery guarantees."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Business Continuity & Disaster Recovery

## Trigger
Use for payment, crypto, SaaS, AI or enterprise critical services needing recovery guarantees.

## Required inputs
service criticality, dependencies, data recovery targets, backup architecture and incident scenarios. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Determine business-impact analysis, tolerable downtime, recovery objectives and safety boundaries.
2. Model loss of region, keys, database, provider, operator or compromised backup.
3. Require encrypted immutable/offline options where justified and separation of backup credentials.
4. Document manual fallback, failover authority, communications and decision gates.
5. Perform a controlled restore/tabletop test against representative data and measure outcomes.
6. Keep evidence of time-to-recover, integrity and remaining single points of failure.

## Output contract
A recovery dependency map, measured restore results, owner-approved runbook and residual-risk register. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
A scheduled backup is not proof of restoration; no destructive failover drill without authorisation. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
