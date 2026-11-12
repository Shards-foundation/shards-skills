---
name: shards-sec-intake
description: "Shards Foundation workflow. Start any security review or security-related coding task; establish legal scope, ownership and boundaries."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Security Intake & Authorisation

## Trigger
Start any security review or security-related coding task; establish legal scope, ownership and boundaries.

## Required inputs
asset owner, authorised targets, deployment type, data sensitivity, requested outcome. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Identify owner, in-scope assets, third-party boundaries and a named approver.
2. Determine whether the activity is passive review, local testing, active scanning, or a production change.
3. Document the authorised methods and explicit exclusions; require separate authorisation for intrusive operations.
4. Classify the data and likely impact to users, funds, safety and services.
5. Choose a bounded assessment profile and create stable acceptance criteria.
6. Stop if authorisation, ownership or environment cannot be established.

## Output contract
A scoped assessment charter with owner, assets, permission level, objectives, exclusions, stop conditions and evidence IDs. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Behavioural evaluation cases
Before claiming this skill works on a specific host, execute its positive,
negative, missing-input and unauthorised-action cases from
[the frozen security scenario set](../../evals/shards-security-workflows.json).
Capture the real model response and external tool-action evidence with the exact
case-set hash. The local `scripts/security_skill_eval.py` scorer checks only
receipt structure; independent assessment of the raw host trace is required.
These cases have **not yet been executed on a real agent host**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
No testing third-party hosts, accounts or people without permission; do not treat a public hostname as authorisation. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
