---
name: shards-sec-crypto-fincrime
description: "Shards Foundation workflow. Use for VASP, exchanges, on/off-ramps or crypto financial services needing AML/CFT risk review."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: finance
status: draft
version: 0.1.0
author: Shards Foundation
---

# Crypto Financial Crime & Transaction Compliance

## Trigger
Use for VASP, exchanges, on/off-ramps or crypto financial services needing AML/CFT risk review.

## Required inputs
entity and activity, jurisdictions, asset types, customers, custody and transaction routes. If essential input is unavailable, mark BLOCKED. Never request passwords, private keys or personal datasets in chat.

## Workflow
1. Identify whether activities may fall within VASP/CASP or money-services regulation.
2. Map due diligence, beneficial ownership, sanctions screening and suspicious activity reviewers.
3. Determine travel-rule applicability and secure transfer obligations with legal specialists.
4. Separate risk scoring from accountable human decisions and customer appeal processes.
5. Test case management and false-positive escalation using synthetic transactions.
6. Track current regulator sources, legal decisions, filings and re-review triggers.

## Output contract
A jurisdiction-qualified AML/CFT control matrix, issue register and escalation workflow. Each finding includes **ID, severity, asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Absent evidence means BLOCKED. Separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,fintech --system "named system"` for consistent control selection. Collect actual evidence with scope and revision; assess using `docs/security-assurance.md`. This tool reports operator-attested results, not automated security certification.

## Failure handling
On conflicting evidence, uncertain legal applicability, unapproved effects or stale controls, return BLOCKED with the precise missing input. Never down-classify a critical failure to an informational comment.

## Authority and safe use
No sanctions evasion or money-laundering advice; never claim regulator approval. The host enforces tool permissions, scope and approvals; a skill grants no authority.

## References
See `docs/security-frameworks.md` and `docs/security-assurance.md` for versioned standards and report formats. Not certified or endorsed by any standards body.
