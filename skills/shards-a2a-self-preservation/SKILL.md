---
name: shards-a2a-self-preservation
description: "Preserve valid task evidence and continuity on agent resumption by re-fetching unchanged results instead of needlessly re-running work."
license: MIT
compatibility: "Portable advisory workflow; evidence freshness must be verified against the authoritative source."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Self-Preservation: preserve work, not the agent

## Trigger
Use when an agent resumes after interruption, context loss, usage exhaustion, an executor handoff or a scoped code/review revision. The thing being preserved is **verified progress, operator resources and user intent**, never an AI's continued operation or privileges.

## Required inputs
Original task and owner, last verified SHA, exact changed artifacts, previous receipts/checks with run IDs and timestamps, current repository/host state, relevant dependencies and pending gates. No previous logs? State `EVIDENCE_MISSING` rather than guessing.

## Workflow
1. **RECOVER.** Re-read the human task and the last sanitised handoff; establish current actor/authority, branch, commit, clean/dirty state and outcome from the live system. Do not treat prior chat memory as proof.
2. **DIFF.** Compare previous verified artifact and target revision to current artifact, including dependency/context drift (tool version, configuration, credentials policy, environment, contract and test inputs). Identify the smallest changed dependency set.
3. **CLASSIFY EACH CHECK:** `REUSE_BY_REF` when exact-head immutable evidence and relevant dependencies are unchanged; `REFETCH_STATUS` when the job was pending or a remote approval/check may have progressed; `RERUN_TARGETED` when changes invalidate affected results; `RERUN_FULL` only when a global gate requires it; `HOLD` when evidence or authority is unavailable.
4. **REFETCH first.** Query existing CI run/review/merge/deployment records by ID and SHA. A new review comment may invalidate a prior gate even with no code change. Re-fetch is itself an observation and must be time-stamped; do not claim the original test re-executed.
5. **REEXECUTE narrowly.** For an actual content or environment change, run the affected tests/checks only if locally authorised; independently observe any CI reruns triggered by the platform. Never fabricate a cached PASS or repeat side-effecting operations to diagnose their status.
6. **PRESERVE findings.** Keep current claims categorised as `VERIFIED_UNCHANGED`, `UPDATED_BY_REFETCH`, `INVALIDATED`, `NOT_RUN`, `BLOCKED`. Record the reason for any reused evidence, including actor/operation/sha and the exact trust boundary.
7. **HANDOFF & STOP.** Record every required gate still pending or unverified. If a refetched required check remains pending, return `HOLD` and recheck the existing run when appropriate. Use `CLOSED` only after all required gates have current completion evidence. Give the next agent the relevant state delta, known-good artifacts and minimum next action. Do not extend authority, spawn a new agent, purchase compute or keep yourself running merely to preserve continuity.

## Execution
Use existing read-only tools (e.g. `git rev-parse`, PR metadata, check-run identifiers, verified digests). Execute tests only when demanded by dependency impact or host/repository policy. This skill has no scheduler, memory persistence, cache of credentials, model self-preservation or waiving live security gates.

## Output contract
```text
TASK_ID / ACTOR / TASK_OWNER / TARGET / BASE_SHA / CURRENT_SHA:
PREVIOUS_EVIDENCE: [{id, source, actor, operation, sha, observed_at}]
CHANGED_DEPENDENCIES / NEW_FINDINGS:
CHECK_DECISIONS: [{check_id, action: REUSE_BY_REF|REFETCH_STATUS|RERUN_TARGETED|RERUN_FULL|HOLD, reason, evidence_ref, timestamp}]
VALIDATED_STATE / STALE_CLAIMS / UNRUN_CHECKS / PENDING_REQUIRED_GATES / SIDE_EFFECTS:
DECISION: CONTINUE|HOLD|ESCALATE|CLOSED
NEXT_OWNER / NEXT_AUTHORIZED_ACTION:
```

## Verification
Test that (a) a pending check at identical SHA is re-fetched, not re-run, (b) a single-line doc correction causes affected checks to be validated on new SHA while stable context may be reused, (c) changed code or compromised evidence invalidates old test claims, and (d) an external payment/dispatch with uncertain outcome is reconciled rather than retried. Record evidence timestamps. The [frozen scenarios](../../evals/shards-a2a-five-workflows.json) are prompts, not real cross-host acceptance results.

## Failure handling
If the source record cannot be queried, `HOLD` rather than claim an old success is current. If a material finding appears during re-fetch, preserve it as open even when the previous reviewer had approved. If a failure blocks continuation, emit a small immutable handoff; never silently restart the task or perform extra external writes.

## Trust boundary
Reusing valid observations is not waiving tests or security review. Freshness is scoped to the exact actor, resource, operation, revision and dependencies. Evidence caching cannot create or renew authorisation, and no agent has a special right to survive termination or expand its runtime.
