---
name: shards-sec-authorized-testing
description: "Shards Foundation workflow. Use for legal penetration-test planning, bug-bounty scope reviews and defensive attacker-emulation exercises."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Authorised Adversarial Security Testing

## Trigger
Use for legal penetration-test planning, bug-bounty scope reviews and defensive attacker-emulation exercises.

## Required inputs
written authorisation, exact targets, test windows, exclusions, contact and emergency stop. If essential input is unavailable, mark BLOCKED. Never request passwords, private keys or personal datasets in chat.

## Workflow
1. Validate asset ownership and written permission; distinguish bug bounty policies from general access.
2. Establish rules of engagement, safe test environment, data handling and emergency contacts.
3. Start passive and non-destructive; control impact and rate for all probes.
4. Document findings without persistence, credential theft, lateral movement or service disruption.
5. Coordinate disclosure and retest only within currently authorised scope.
6. Produce concrete fixes and defensive evidence rather than exploit-chain automation.

## Output contract
A rules-of-engagement document, scoped defensive findings and verified remediation backlog. Each finding includes **ID, severity, asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Absent evidence means BLOCKED. Separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base --system "named system"` for consistent control selection. Collect actual evidence with scope and revision; assess using `docs/security-assurance.md`. This tool reports operator-attested results, not automated security certification.

## Failure handling
On conflicting evidence, uncertain legal applicability, unapproved effects or stale controls, return BLOCKED with the precise missing input. Never down-classify a critical failure to an informational comment.

## Authority and safe use
Stop on scope ambiguity; never attack unconsenting systems. The host enforces tool permissions, scope and approvals; a skill grants no authority.

## References
See `docs/security-frameworks.md` and `docs/security-assurance.md` for versioned standards and report formats. Not certified or endorsed by any standards body.
