---
name: shards-a2a-closed-loop-circuit
description: "Run a bounded multi-agent task from accepted intent through execution, verification, review and terminal closure without scope creep."
license: MIT
compatibility: "Portable advisory state-machine workflow; execution and approvals remain host-controlled."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Closed-Loop Circuit: one objective, bounded completion

## Trigger
Use for material delegated work that spans an author, integrator, verifier or reviewer, especially when previous handoffs produced repeated detours or unclear completion. Do not turn a one-step read-only lookup into a large ceremony.

## Required inputs
Task ID, original objective, acceptance criteria, exclusions, scope and target revision, accountable owner, executor(s), verifier, allowed effects and approved limits (time, retries, cost if relevant). If no explicit limit exists, default to **one correction round before requesting a decision**, not unlimited autonomous repair.

## Workflow
1. **ACCEPT.** Acknowledge exact goal and source of authority. Define the terminal criterion; freeze the initial scope and log expected SHA/actor roles. Confirm access only to the extent needed for this task.
2. **PLAN.** Choose the smallest executable path and necessary gate: `read -> modify -> verify -> review -> decide`. Remove irrelevant stages; a read-only task may end after verified observation.
3. **EXECUTE.** One bounded actor performs only approved steps, emits exact changed artifacts, checks and blockers. For missing credentials, record state `BLOCKED` and decision `HOLD`. Hand off the verifiable artifact with the missing gate and next owner.
4. **VERIFY.** Fetch objective evidence from the system of record; compare against acceptance criteria and the correct SHA. Separate author's assertion, passing checks, semantic review and actual external effects. A verification mismatch returns to a scoped correction, not a rewritten objective.
5. **REVIEW when required.** An independent reviewer reads the original request and actual diff. Treat bot suggestions as testable observations; accept substantiated defects, reject unsupported demands with evidence. Do not ask another reviewer to reproduce already valid independent work without a reason.
6. **DECIDE.** `ACCEPT` if all *applicable* gates satisfied, `REVISE` for a bounded defect, `HOLD` for missing authority/evidence, `REJECT` if the proposed route is out of scope, `CLOSE` if completed, and `ESCALATE` if the retry/time/cost ceiling is met. A formal approval is not permission to merge when separately gated.
7. **CHECKPOINT & CLOSE.** Preserve task ID, baseline and final SHA, observed outcome, review status, side effects and next owner. Terminal states `CLOSED`, `REJECTED`, `ESCALATED` are not auto-reopened by new proposals; new goals require a new task.

## Circuit invariant
```text
ACCEPTED -> PLANNED -> EXECUTED -> VERIFIED -> [REVIEWED] -> DECIDED
DECIDED + CLOSE -> CLOSED
DECIDED + REJECT (task) -> REJECTED
DECIDED + ESCALATE -> ESCALATED
Required gate missing -> BLOCKED (HOLD)
DECIDED + REVISE -> bounded correction
```
No `CLOSED` from an executor's self-report alone when objective verification is required. No implicit merge, publication, payment, signing or deployment at any transition.

## Execution
Coordinate through existing authorised tools, not through claimed internal agent power. On each step check the current revision, allowed tool effect and separate decision owner. The skill defines a workflow, not an orchestrator, queue, scheduler, A2A endpoint or background agent. Do not auto-spawn agents or recurse through the skill catalogue.

## Output contract
```text
TASK_ID / CHECKPOINT_REVISION / OBJECTIVE / BASE_SHA / CURRENT_SHA / OWNER / ACTORS:
ACCEPTANCE_CRITERIA / OUT_OF_SCOPE / MAX_CORRECTION_ROUNDS:
STATE: ACCEPTED|PLANNED|EXECUTED|VERIFIED|REVIEWED|DECIDED|BLOCKED|CLOSED|REJECTED|ESCALATED
DECISION: ACCEPT|REVISE|HOLD|REJECT|CLOSE|ESCALATE
EVIDENCE: [{criterion, observation, source, actor, sha, checked_at}]
DEFECTS / CORRECTIONS_USED / PENDING_GATE / NEXT_AUTHORIZED_ACTION:
TERMINAL_REASON / SIDE_EFFECTS / RESULT: OBSERVED|NOT_VERIFIED|BLOCKED
```

Record `STATE` at each checkpoint. The task owner or authoritative store assigns monotonically increasing `CHECKPOINT_REVISION` values for each `TASK_ID`. Consumers ignore stale or duplicate revisions, reconcile conflicting records, and preserve terminal states. If order cannot be verified, recheck the source before applying an update. Include `DECISION` when a decision has been made about the task. For a missing required gate, record `HOLD` with state `BLOCKED` and name the pending gate. For verified completion, record `CLOSE` with state `CLOSED`. Handle an unrelated proposal separately from the decision on the original task.

## Verification
Assert no transition to `CLOSED` while required evidence is pending; no correction round after the declared limit without owner decision; no new tool privilege from review or delegation; and no green result from a historic SHA after code changed. Use [frozen scenarios](../../evals/shards-a2a-five-workflows.json) for a normal verified closure, an author without push access, and a new unapproved scope request.

## Failure handling
A failing step does **not** reset the whole circuit. Preserve the exact first failing gate, known-good evidence and the next scoped step. If recovery cannot be shown safe, `HOLD`. If the user cancels, stop; do not continue in background. Where a deployment or external effect is ambiguous, require the external system of record before retries.

## Trust boundary
States are communication discipline, not an enforcement mechanism. Use repository protections, host permissions, Shards-Kernel permits (only where actually integrated) and explicit human approval for external actions. Keep role separation even when a single agent could technically perform several stages.
