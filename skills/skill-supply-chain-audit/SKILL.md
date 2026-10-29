---
name: skill-supply-chain-audit
description: "Use before adopting, copying, installing or executing a third-party agent skill, plugin, prompt package or tool bundle."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Skill Supply Chain Audit

## Workflow
1. Record source URL, owner, exact commit/tag, retrieval date, file inventory and declared licence.
2. Read repository and per-file notices; determine whether redistribution and modification are permitted.
3. Inspect instructions for prompt injection, authority escalation, secret access, data exfiltration, destructive commands and hidden network calls.
4. Inspect every script, binary, dependency, install hook and remote endpoint. Hash artefacts when reproducibility matters.
5. Run static scanners and metadata validators, then review every hit in context.
6. Behaviour-test only in a disposable sandbox without secrets, with restricted egress and explicit command approval.
7. Record reviewer, findings, evidence, disposition and re-review trigger.

## Output contract
Return provenance, licence decision, capability inventory, risk findings, scanner limitations, sandbox results and status (`draft`, `review`, `verified`, `rejected`).

## Verification
A skill is `verified` only for the exact reviewed revision and declared scope. Any upstream revision change invalidates the previous review until re-evaluated.

## Failure handling
If licence, provenance or behaviour cannot be established, do not copy or execute the material. Link to the source and mark the decision unresolved.
