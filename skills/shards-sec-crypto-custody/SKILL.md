---
name: shards-sec-crypto-custody
description: "Shards Foundation workflow. Use for wallet apps, multisig treasuries, token custody, key rotation and high-value on-chain signing."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: blockchain
status: draft
version: 0.1.0
author: Shards Foundation
---

# Wallet, Signing & Digital Asset Custody

## Trigger
Use for wallet apps, multisig treasuries, token custody, key rotation and high-value on-chain signing.

## Required inputs
chain/network, wallet architecture, keys and signers, custody model, asset sensitivity and incident plan. If missing and essential, mark BLOCKED rather than inventing facts. Never request a private key, password or customer dataset in chat.

## Workflow
1. Map key generation, storage, recovery, derivation paths, signers, permissions and human oversight.
2. Evaluate hardware-backed and distributed signing where appropriate, plus independent signer separation.
3. Bind every signing request to verified chain ID, destination, value, calldata, approvals and nonce.
4. Test malicious approval, blind signing, address substitution and wrong-chain simulation with dummy assets.
5. Document revoke/rotation, compromised signer, lost device and emergency freeze scenarios.
6. Maintain on-chain audit records while minimising address-linked personal data.

## Output contract
A custody trust diagram, signing policy, negative tests and disaster recovery plan. Each finding includes **ID, severity, affected asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Keep absent evidence BLOCKED. Report the exact revision, environment and timestamp; separate planned, implemented, tested and independently verified.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,crypto --system "named system"` for a consistent control selection. Collect actual technical and organisational evidence; assess with the reviewed input schema in `docs/security-assurance.md`. Record at least one positive and one negative test where feasible. The tool reports operator-attested evidence, **not automated security certification**.

## Failure handling
On conflicting evidence, unknown regulatory applicability, unapproved effects or out-of-date controls, return BLOCKED with the precise missing input and owner. Do not downgrade a failed critical control to a documentation note.

## Authority and safe use
Never expose seed phrases, private keys or authorise real asset movements on a skill's recommendation. This skill carries no tool permissions. All actions require host-enforced scope and approval. External specifications are references, not inherited authority.

## References
Refer to `docs/security-frameworks.md` for versioned primary-source links and applicability limitations, and `docs/security-assurance.md` for common report schemas. The Shards-authored workflow is not NIST, OWASP or regulator certification.
