---
name: shards-sec-identity-access
description: "Shards Foundation workflow. Use when adding login, permissions, SSO, service accounts or admin operations."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Identity, Session & Access Security

## Trigger
Use when adding login, permissions, SSO, service accounts or admin operations.

## Required inputs
roles, identity provider, resource ownership rules, session lifecycle and audit needs. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Define actor-role-resource-action matrix and deny-by-default policy outside the browser.
2. Enforce phishing-resistant MFA for privileged identities where supported, least privilege and separation of duties.
3. Review session fixation, cookie attributes, token audience, expiry, revocation and device/session logout.
4. Test cross-tenant object access and service-to-service identity spoofing.
5. Verify administrative actions leave attributable, protected audit evidence.
6. Set recurring access review, emergency access and deprovisioning procedures.

## Output contract
A permission matrix, negative authorisation tests, identified gaps and deployment gate. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,web --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Do not regard frontend route hiding or client flags as access control. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
