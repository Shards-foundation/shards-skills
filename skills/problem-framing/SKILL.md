---
name: problem-framing
description: "Use when a request is ambiguous, multi-stage, high-impact, or likely to fail because the objective and acceptance criteria are underspecified."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Problem Framing

## Workflow
1. Restate the desired outcome as an observable end state, not a list of activities.
2. Separate supplied facts, unknowns, assumptions, constraints, and decisions.
3. Identify the smallest set of missing details that can change the solution. Ask only for essential blockers; otherwise label bounded assumptions.
4. Define acceptance criteria, non-goals, risk boundaries, dependencies, and rollback expectations.
5. Break work into verifiable milestones with an owner, expected artefact, test, and status.
6. Before execution, check that the plan is feasible with available tools and permissions.

## Output contract
Return: objective, constraints, assumptions, open blockers, acceptance criteria, milestone plan, risk register, and verification plan. Mark unverified statements explicitly.

## Verification
A second reader should be able to decide whether the task is complete without interpreting vague words such as "good", "robust", or "fully working".

## Failure handling
If requirements conflict, surface the conflict and propose a minimal resolution. Do not hide a blocker behind invented progress.
