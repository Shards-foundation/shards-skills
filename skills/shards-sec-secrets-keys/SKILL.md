---
name: shards-sec-secrets-keys
description: "Shards Foundation workflow. Use when handling API keys, wallet keys, signing credentials, database secrets or CI tokens."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Secrets & Cryptographic Key Lifecycle

## Trigger
Use when handling API keys, wallet keys, signing credentials, database secrets or CI tokens.

## Required inputs
secret classes, key owners, custody boundary, rotation process and infrastructure. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Inventory secret types and privilege scopes without copying secret values into results.
2. Prefer managed secret stores or HSM where appropriate; prevent access through logs, builds, prompts and public repositories.
3. Separate development, staging and production credentials and identify bootstrap trust.
4. Verify minting, storage, rotation, expiry, revocation, compromise response and backup recovery.
5. Test least-privilege denial and a simulated rotation using disposable credentials.
6. Record residual exposure and owner-approved reissue plan.

## Output contract
A secret lifecycle map, rotation runbook and evidence of isolation tests with redacted identifiers. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,crypto --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Never print tokens or private keys; never rotate real production keys without narrow approval. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
