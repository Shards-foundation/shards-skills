---
name: shards-sec-detection-response
description: "Shards Foundation workflow. Use when designing security telemetry, fraud alerts or SOC detection for an app, API or cloud service."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Security Logging, Detection & Alerting

## Trigger
Use when designing security telemetry, fraud alerts or SOC detection for an app, API or cloud service.

## Required inputs
event sources, threat scenarios, data sensitivity, expected volume and responders. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Map required security events to threat scenarios, identities and critical actions.
2. Design structured logging with timestamps, actor/source, decision and correlation IDs.
3. Redact personal data, tokens, secrets and private transaction details from telemetry.
4. Define alert thresholds, false-positive controls, escalation and on-call ownership.
5. Simulate permitted misuse and verify detection and responder evidence end to end.
6. Test retention, tamper resistance and recovery of essential logs.

## Output contract
Detection coverage matrix, example redacted events, alert test results and on-call runbook. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Include the `cloud` profile only when cloud infrastructure is actually in assessment scope. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Logs are observations, not authorization; no covert monitoring of individuals. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
