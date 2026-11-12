---
name: shards-sec-vibecoding-gate
description: "Shards Foundation workflow. Use when an inexperienced developer or coding agent builds or ships a web app, AI feature or payment flow."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Vibe-Coding Security Gate

## Trigger
Use when an inexperienced developer or coding agent builds or ships a web app, AI feature or payment flow.

## Required inputs
repository revision, intended user actions, data handled, deployment target, authentication model. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Draw the trust boundary: anonymous visitor, signed-in user, admin, background service and third-party API.
2. Check secrets are server-side, private endpoints are inaccessible without authentication and all object access is authorised server-side.
3. Verify validation, output encoding, safe file uploads, SSRF defenses and abuse limits against realistic misuse cases.
4. Demand tests for horizontal privilege escalation, direct-object access and payment/webhook replay.
5. Check dependencies, deployment environment, logging redaction, backups and privacy notices.
6. Produce a fail-closed shipping verdict; test using dummy records and non-production credentials.

## Output contract
A beginner-readable PASS/FAIL/BLOCKED release checklist with exact reproduction steps, changes required and tested commit. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Read-only local preflight
For an owned Git checkout, run `python scripts/vibecode_guard.py --repo .` and inspect **sanitised file/line findings only**. An exit code of 0 means no configured heuristics matched, **not** that the app is secure; code 1 means findings need review, code 2 means input is blocked. The tool reads tracked local files only; it does not execute project code, call external services, inspect live cloud systems or reveal matched source lines. Manually verify each finding and conduct the negative application tests in the workflow.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,web --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

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
Do not infer security from UI polish, an AI explanation or a passing build; no automatic deploy. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
