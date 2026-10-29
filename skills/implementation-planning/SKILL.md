---
name: implementation-planning
description: "Use when a change spans multiple files, components or stages and needs a sequenced plan with explicit verification before execution."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Implementation Planning

## Workflow
1. Inspect the repository and existing conventions before proposing file changes.
2. State the end state, constraints, assumptions, dependencies and out-of-scope work.
3. Decompose work into small, ordered tasks with concrete file paths, expected changes and acceptance tests.
4. Identify dependency edges, parallelisable work, risky migrations and irreversible actions.
5. Attach a verification command or observable check to every task; include negative and failure-path tests.
6. Add checkpoints for review, security, integration and rollback; keep progress state explicit.
7. Execute only against the approved plan, updating status when evidence changes the plan.

## Output contract
Provide ordered tasks, dependencies, affected paths, acceptance criteria, test commands, risks, rollback and a status ledger.

## Verification
Each task must be independently checkable and small enough to review. The final gate must test the integrated system, not merely individual tasks.

## Failure handling
If inspection reveals conflicting architecture or a missing prerequisite, pause at that dependency and update the plan rather than fabricating implementation progress.
