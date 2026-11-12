---
name: shards-sec-jurisdiction-scope
description: "Shards Foundation workflow. Use for cross-border digital products, finance, AI services or crypto when laws and regulators may differ."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Regulatory Jurisdiction & Applicability Mapping

## Trigger
Use for cross-border digital products, finance, AI services or crypto when laws and regulators may differ.

## Required inputs
entity incorporation, customers and residency, service activities, establishment, assets, data transfers and dates. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Record legal entities, operating countries, customer locations and regulatory perimeter-relevant activities separately.
2. Identify potentially relevant law and regulator by territory, entity and service; source only primary authorities where possible.
3. Evaluate dates, exemptions, thresholds and whether a registration, licence or notification is required.
4. Assign each rule as potentially applicable, not applicable with reason, or legal review required.
5. Link versioned regulator sources and legal reviewer sign-off; track effective-date changes.
6. Refuse transaction or launch approval where material applicability remains unresolved.

## Output contract
A dated jurisdiction matrix with activities, sources, assumptions, owners, review status and licensing blockers. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,governance --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
This is research and issue-spotting, not legal advice; never invent legal status or assert blanket global compliance. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
