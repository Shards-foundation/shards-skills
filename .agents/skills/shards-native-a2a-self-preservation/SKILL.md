---
name: shards-native-a2a-self-preservation
description: "Use for cross-agent task continuation to preserve verified work, compare dependency fingerprints, reuse immutable receipts and re-fetch mutable status without needless reruns."
license: MIT
compatibility: "Portable advisory workflow; no special persistence, self-protection or elevated permissions."
status: candidate
---
# Shards A2A Self-Preservation — preserve evidence and resources

## Trigger
Agent replaced or interrupted, CI already ran, work transferred between hosts, source SHA changed, approval state pending or delivery status uncertain. This concerns **task continuity**, never the agent's survival or right to keep running.

## Procedure
1. **ACK scope and actor** against current human task and real host capabilities. Record task and owner. A prior checkpoint does not grant permission.
2. **Classify evidence**: for each item record `id`, `actor`, `operation`, `revision_sha`, `observed_at`, `claim_level`, `locator_kind`, `locator_value`, `artifact_digest_sha256`, `dependency_fingerprint_sha256`, and whether a second actor independently verified it. Unqueryable or synthetic locators are not proof of operational success.
3. **Compare dependencies:** code revision, relevant test inputs, config, tool version, execution environment and identity policy. Distinguish immutable commit content from mutable PR/CI/review state.
4. **Choose precisely one action per check:** `REUSE_BY_REF` only with retrievable immutable evidence and unchanged relevant dependencies; `REFETCH_STATUS` for mutable remote status with a valid provider locator; `RERUN_TARGETED` when a changed dependency invalidates affected tests; `RERUN_FULL` only for a recorded global gate or justified broad invalidation; `HOLD` for missing evidence, authority or locator. An original executor's unverified claim can be preserved as testimony, never silently upgraded to reuseable PASS.
5. **Avoid unnecessary reads:** store the exact refetched record, timestamp and dependency comparison. Rechecking a fixed SHA without new information is normally redundant. Revalidate mutable security/review state near consequential decisions.
6. **Interrupt safely:** if an external effect has uncertain outcome, do not retry it. Reconcile against its source of record, or HOLD. Keep prior output/hashes unchanged.
7. **Emit portable delta:** observed changes, validity of prior evidence, missing controls, one next authorised owner/action, and whether closure was verified. Use `shards-native-agent-handoff` to produce a durable record when available.

## Output
`TASK_ID, ACTOR, OWNER, TARGETS, OBSERVED_DELTA, EVIDENCE [{actor, operation, revision_sha, locator_kind, locator_value, dependency_fingerprint_sha256, claim_level}], CHECK_DECISIONS [{check_id, choice, reason, evidence_id}], VERIFIED, REPORTED_ONLY, UNRUN, BLOCKERS, NEXT_OWNER, NEXT_ACTION, DECISION`.

## Verification examples
1. Pending check at fixed SHA + queryable run ID → REFRESH, not rerun. 2. Valid cached unit-test receipt with unchanged inputs → REUSE. 3. Doc change triggers new affected checks only. 4. Synthetic review ID with no real provider locator → HOLD. 5. Payment/dispatch in unknown state → reconcile, never resend. 6. New PR comment can invalidate approval gate without changing head SHA.

## Failure / trust boundary
A digest does not certify that an assertion is true. A local structure validator cannot verify review author identity, CI provider state or permit authority. No further work may be started without real authorisation from the human/host. Stop cleanly on absent evidence or forbidden effects.
