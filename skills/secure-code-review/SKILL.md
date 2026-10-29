---
name: secure-code-review
description: "Use when reviewing code for vulnerabilities, unsafe input handling, authorisation errors, secrets exposure or insecure defaults."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Secure Code Review

## Workflow
1. Identify trust boundaries, sensitive assets, attacker-controlled inputs and security-relevant sinks.
2. Trace authentication and authorisation independently; verify object-level access and default-deny behaviour.
3. Inspect input validation, output encoding, injection risks, path handling, deserialisation, SSRF, crypto usage and error leakage as relevant.
4. Review secret handling, logging, dependency provenance, network egress and privilege boundaries.
5. Validate findings against concrete code paths and available tests; avoid speculative CVE claims.
6. Recommend least-privilege, defence-in-depth fixes and regression tests.

## Output contract
Provide severity, affected path/line, preconditions, impact, evidence, remediation and test recommendation. State scope and exclusions.

## Verification
Do not test against systems without authorisation. A scanner finding is not confirmed until context is reviewed; absence of findings is not proof of security.

## Failure handling
If exploitability or scope is uncertain, mark confidence and request the minimum evidence needed. Never request real production secrets to validate a finding.
