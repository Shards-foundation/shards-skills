---
name: agent-system-design
description: "Use when designing a multi-agent system, tool-using assistant, orchestrator, worker fleet or autonomous workflow."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Agent System Design

## Workflow
1. Define the job, success criteria, prohibited actions, budget, latency and human-approval boundaries.
2. Prefer a deterministic workflow where possible; add agents only where model judgement creates measurable value.
3. Specify roles, typed input/output contracts, ownership, hand-off rules, timeouts, retries and idempotency.
4. Separate planning, execution, observation and auditing. Treat model output and retrieved content as untrusted data.
5. Enforce permissions outside the model with policy gates, scoped credentials, allowlists and approval checks.
6. Add durable job state, event/audit records, cancellation, dead-letter handling and recovery after partial failure.
7. Evaluate task success, tool correctness, safety, cost and latency on representative cases.

## Output contract
Provide architecture, state machine, contracts, failure modes, security controls, observability, evaluation plan and deployment assumptions.

## Verification
Demonstrate retries, duplicate events, tool failures, malformed outputs, cancellation and permission denial. Do not rely on a prompt as the only security boundary.

## Failure handling
If an action is irreversible or externally visible, pause for explicit approval unless a documented policy authorises it. Preserve state and surface partial completion honestly.
