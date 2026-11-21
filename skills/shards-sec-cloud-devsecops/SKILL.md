---
name: shards-sec-cloud-devsecops
description: "Shards Foundation workflow. Use when deploying or modifying cloud infrastructure, containers, CI/CD pipelines or infrastructure-as-code."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Cloud, CI/CD & Infrastructure Controls

## Trigger
Use when deploying or modifying cloud infrastructure, containers, CI/CD pipelines or infrastructure-as-code.

## Required inputs
cloud accounts, project boundaries, IaC, CI roles, environment protections and change window. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Inventory accounts, network edges, data stores, identities and production paths.
2. Review default-deny IAM, network segmentation, private storage, encryption and secret references.
3. Check OIDC workload identity, ephemeral credentials, protected branches and least-privilege workflow tokens.
4. Validate artifact pinning, dependency updates, infrastructure plan review and drift detection.
5. Inspect logs, monitoring, restore capability and emergency access with evidence.
6. Verify changes in a disposable environment before approved rollout.

## Output contract
A cloud control inventory with IaC diffs, least-privilege findings and tested rollback. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,cloud --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Never run apply, delete or rotate in production solely from this skill. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
