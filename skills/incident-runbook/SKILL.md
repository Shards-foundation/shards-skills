---
name: incident-runbook
description: "Use when diagnosing a production incident, service degradation, agent failure or operational event requiring coordinated response."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: operations
status: draft
version: 0.1.0
author: Shards Foundation
---

# Incident Runbook

## Workflow
1. Establish incident commander, severity, affected services/users, start time and communication channel.
2. Stabilise safely: protect users/data first, prefer reversible mitigations, and avoid unapproved destructive changes.
3. Collect time-correlated logs, metrics, traces, deploy/config changes and exact error signatures.
4. Maintain a hypothesis list and test the highest-value discriminating observations.
5. Record every mitigation, operator, timestamp, result and rollback condition.
6. Verify recovery using user-visible health indicators, not only process status.
7. After resolution, preserve evidence and run a blameless review focused on systemic causes and measurable actions.

## Output contract
Incident timeline, impact, current status, confirmed facts, hypotheses, mitigations, verification evidence, risks and follow-up owners.

## Verification
A recovery declaration requires an explicit service-level signal and an observation window appropriate to the failure. Clearly mark ongoing monitoring.

## Failure handling
If evidence is incomplete, state the uncertainty and continue safe observation. Escalate when data integrity, security, safety or recovery objectives are at risk.
