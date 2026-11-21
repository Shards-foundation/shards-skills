---
name: shards-sec-business-threat-model
description: "Shards Foundation workflow. Use for an enterprise, startup or regulated product before architecture or significant feature changes."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Business Threat Modelling

## Trigger
Use for an enterprise, startup or regulated product before architecture or significant feature changes.

## Required inputs
business goals, assets, actors, data flows, existing controls, impact thresholds. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Inventory money paths, privileged identities, customer data, operational dependencies and critical services.
2. Map ingress, egress, trust zones and connections including suppliers and agents.
3. Create misuse cases for insider, compromised vendor, criminal, malicious customer and accidental operator actions.
4. Rank scenarios by likelihood and impact, separating assumptions from observed exposure.
5. Define prevention, detection, response and recovery controls with accountable owners.
6. Revisit after architecture, financial flow or jurisdiction changes.

## Output contract
An asset/data-flow map, ranked threat register, residual-risk owner and actionable mitigations. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Do not claim zero risk from missing incident history or run intrusive attack tests without permission. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
