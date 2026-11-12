---
name: shards-sec-incident-response
description: "Shards Foundation workflow. Use when credentials, customer data, funds, systems or agents may have been compromised."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Incident Response & Evidence Preservation

## Trigger
Use when credentials, customer data, funds, systems or agents may have been compromised.

## Required inputs
alert, incident coordinator, affected assets, contact tree and evidence retention rules. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Open incident record, preserve timestamps, contacts and chain-of-custody expectations.
2. Classify severity by customer safety, financial loss, data exposure and service availability.
3. Separate verified facts from hypotheses; preserve relevant logs before containment changes.
4. Select containment that minimises harm and explicitly authorise disruptive actions.
5. Coordinate recovery, credential rotation, stakeholder communications and regulatory notification review.
6. Verify restored operations, monitor for recurrence and write a sanitised post-incident review.

## Output contract
Incident timeline, containment approvals, evidence index, recovery criteria and notification-assessment owner. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Do not destroy evidence, disclose personal data or assume breach notification deadlines across jurisdictions. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
