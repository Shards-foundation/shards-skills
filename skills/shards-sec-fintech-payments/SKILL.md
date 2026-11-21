---
name: shards-sec-fintech-payments
description: "Shards Foundation workflow. Use for wallets, banking APIs, card flows, payment platforms, money movement and settlement systems."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: finance
status: draft
version: 0.1.0
author: Shards Foundation
---

# Fintech, Payment & Funds Movement Controls

## Trigger
Use for wallets, banking APIs, card flows, payment platforms, money movement and settlement systems.

## Required inputs
regulated activity, transaction flow, custodians, partners, currencies, settlement and authorised signers. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Map who holds funds, authorises instructions, initiates settlement and controls refunds or reversals.
2. Require server-side authorisation, amount/beneficiary integrity and replay-safe idempotency keys.
3. Check fraud thresholds, sanctions/AML jurisdiction analysis and suspicious-activity escalation with specialists.
4. Reconcile independent ledger, provider and bank settlement records; handle partial failure and double spend.
5. Design dual authorisation for privileged transfers and tested rollback/compensation mechanisms.
6. Escalate PSD2/SCA, DORA, PCI or other regimes only if applicability mapping supports them.

## Output contract
A funds-flow threat model, controls test table, reconciliation evidence and regulatory blockers. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,fintech --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Never initiate live payments, move money or assert regulatory licensing without explicit authority. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
