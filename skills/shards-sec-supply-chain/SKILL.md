---
name: shards-sec-supply-chain
description: "Shards Foundation workflow. Use when importing packages, AI skills, container images, SDKs or build actions."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Dependency, SBOM & Build Integrity

## Trigger
Use when importing packages, AI skills, container images, SDKs or build actions.

## Required inputs
source repository, licenses, dependency lock, upstream commit and release pipeline. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Record original publisher, source, immutable revision, license and update channel.
2. Review install scripts, post-install hooks, container privileges, dependencies and network behavior.
3. Generate and inspect a dependency inventory/SBOM using trusted tooling in isolation.
4. Compare known advisories with reachable code, exploit preconditions and package usage.
5. Require pinned versions, artifact provenance and controlled CI privileges; test the update in sandbox.
6. Maintain exception expiry and supply-chain incident rollback.

## Output contract
A provenance record, identified dependency risks, validated update decision and review evidence. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,cloud --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Unknown origin or arbitrary script execution is blocked, not silently marked safe. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
