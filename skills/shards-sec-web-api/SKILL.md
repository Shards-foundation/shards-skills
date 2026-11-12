---
name: shards-sec-web-api
description: "Shards Foundation workflow. Use for APIs, SaaS, websites, GraphQL, webhooks and multi-tenant services."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Web, API & Application Assurance

## Trigger
Use for APIs, SaaS, websites, GraphQL, webhooks and multi-tenant services.

## Required inputs
routes, trust model, API schemas, auth rules, dependency list and test environment. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Map entry points, authentication requirements, resource ownership and trust boundaries.
2. Check injection, output encoding, request validation, upload handling, SSRF and secure deserialisation.
3. Exercise tenant isolation, IDOR, replay, idempotency, CSRF/session protections and rate limits in a controlled test environment.
4. Validate webhook signatures against raw request bytes, freshness window and replay storage.
5. Assess security headers, dependency risk, error leakage, monitoring and recovery behavior.
6. Map applicable OWASP ASVS 5.0 requirements and identify tested versus not-tested controls.

## Output contract
Endpoint-level findings, negative-test evidence, control map and release blockers. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,web --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Do not scan unowned websites or report an ASVS level achieved from heuristic source checks. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
