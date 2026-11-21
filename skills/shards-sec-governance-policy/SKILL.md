---
name: shards-sec-governance-policy
description: "Shards Foundation workflow. Use when formalising business security policies, acceptable use, exceptions or risk ownership."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Security Governance & Policy Lifecycle

## Trigger
Use when formalising business security policies, acceptable use, exceptions or risk ownership.

## Required inputs
organization type, leadership owner, asset risks, applicable obligations and existing controls. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Identify accountable policy owner, approving body, audience and revision date.
2. Document risk appetite, asset classification, acceptable use, access, supplier, incident and continuity policies.
3. Map policy statements to enforceable technical controls and observed evidence.
4. Define role separation: policy authors cannot silently approve their own exceptions or audit them.
5. Implement versioning, training acknowledgement, exception expiry and review triggers.
6. Use board/management sign-off and retain change history before claiming a policy is in force.

## Output contract
A versioned policy pack, risk/exception register, owners, sign-off status and evidence gaps. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,governance --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Drafts are not approved policies; written declarations alone do not establish control operation. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
