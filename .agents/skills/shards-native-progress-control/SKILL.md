---
name: shards-native-progress-control
description: "Use on multi-step agent tasks to detect no-evidence loops, unnecessary repeated SHA checks and retry churn; record the smallest next action with a bounded evidence-gain budget."
license: MIT
compatibility: "Portable instruction-only workflow; no ledger or host-specific runtime required."
status: candidate
---
# Shards Progress Control — evidence gain over activity

## Trigger
Repeated reads, repeated failed commands, compaction continuation, re-review, long tasks with uncertain completion, or several agents attempting the same work.

## Procedure
1. **Freeze the task contract** with criterion ID, owner, target revision(s), allowed effects and success condition. Identify what actually remains unresolved.
2. **Inventory prior attempts** with `criterion_id`, `action`, `action_fingerprint`, input/dependency SHA-256 where available, timestamp, status, `evidence_ref`, and `new_information` boolean. If a previous trace is missing, say `ATTEMPTS_UNKNOWN`.
3. **Compare evidence gain:** if same action + same fingerprint + same result + no new evidence, do not repeat merely to appear busy. State a changed hypothesis or `HOLD` with blocker. A new locator may be worth one re-fetch, but is not itself proof of success.
4. **Retry bound:** default at most one identical failed attempt without information gain; a second attempt requires a changed prerequisite/hypothesis or explicit user authority. A sensitive or side-effecting operation gets **zero blind retries**. Report retry history rather than silently resetting the counter after compaction.
5. **SHA freshness:** immutable commit object can be reused by verified digest. Mutable branch HEAD, PR review state, CI job status and privileges must be refreshed at the decision point; don't poll repeatedly without a purpose.
6. **Stop/route:** when all original criteria have verified evidence, stop. On blocked prerequisites, identify owner and one next action, not a new unrelated objective.

## Output
`TASK/CRITERION/OWNER, PREVIOUS_ATTEMPTS, UNIQUE_ACTION_FINGERPRINTS, EVIDENCE_GAIN, VERIFIED_STATE, OPEN_BLOCKER, NEXT_OWNER, ONE_NEXT_ACTION, RETRY_DECISION: REUSE|REFETCH|TARGETED_RETRY|HOLD|CLOSE`.

## No-ledger fallback
If Shards `AGENTS.md` or `docs/operating-loop.md` does not exist, use a local attempt list in the handoff output; do not claim append-only durability or a native ledger. Missing data stays unknown.

## Safety
This is not an autonomous task scheduler or authority grant. No external effect may be retried to discover whether it succeeded; reconcile with the system of record or hold. Checks count as progress only when they produce new, independently usable information.
