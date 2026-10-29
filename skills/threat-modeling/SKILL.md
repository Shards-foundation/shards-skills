---
name: threat-modeling
description: "Use when designing a new service, agent, integration, data flow, smart contract or significant architectural change."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: security
status: draft
version: 0.1.0
author: Shards Foundation
---

# Threat Modeling

## Workflow
1. Define system boundary, assets, actors, trust zones, entry points and data flows.
2. Identify adversary capabilities and abuse cases, including compromised dependencies and malicious tool output.
3. Enumerate threats with a consistent method such as STRIDE, adapted to the domain.
4. Rate likelihood and impact with stated assumptions; identify high-risk attack paths.
5. Map each material threat to preventive, detective and recovery controls.
6. Define residual risk, verification tests, owners and review triggers.

## Output contract
Provide a concise architecture summary, threat table, control mapping, assumptions, residual risks and test plan.

## Verification
Every high-risk threat must have a mitigation or explicit accepted-risk owner. Avoid vague controls such as "use best practices".

## Failure handling
If architecture evidence is missing, label the model provisional and request a diagram, data-flow description or key interfaces rather than inventing components.
