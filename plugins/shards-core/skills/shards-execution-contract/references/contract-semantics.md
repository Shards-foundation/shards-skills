# Execution Contract v1 — semantics

This is a human/agent exchange envelope. It is not a signed permit or proof of execution.

## Required fields

- `schema_version`: integer `1`; unknown versions are rejected.
- `task_id`: lower-case slug, unique in its host/task context.
- `intent`: `reference` (sanitised identifier pointing to the original human request), `goal`, `assumptions` (array of descriptions), `ambiguities` (array of `{description, material, resolved}`). Never paste personal conversations into a public source file.
- `scope`: `repository` (owner/repo), `branch`, and `head_sha` (40 hexadecimal characters for an actual Git commit). Unknown SHA means HOLD. A SHA string is untrusted until looked up independently.
- `constraints`: explicit booleans `allow_paid`, `allow_production`, `allow_merge`, `allow_external_write`. The validator is conservative and returns HOLD when any is true because it cannot authenticate host approval.
- `executor`: agent/operator identifier.
- `steps`: `{id, owner, effect, status, evidence_ids}`. Allowed effects: `read-only`, `local-write`, `local-execute`, `external-write`, `production`, `paid`, `merge`, `destructive`, `sensitive`. Reported executed/verified effects that contradict forbidden constraints cause FAIL; sensitive/destructive effects require host verification and remain HOLD. Status values: `PROPOSED`, `EXECUTED`, `VERIFIED`, `FAILED`, `BLOCKED`. Completed claims must reference evidence. An executed step is not necessarily verified.
- `checks`: `{id, result, evidence_ids}`. Result values: `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`.
- Each review records `reviewer`, `revision`, `verdict`, `open_findings`, `step_ids` and `evidence_ids`. The verdict is one of `APPROVED`, `CHANGES_REQUESTED` or `BLOCKED`. List each covered step ID once. An approval can cover several steps, and separate approvals can cover different steps. The reviewer must differ from the executor and every owner in that review's scope. Independence comparisons ignore surrounding whitespace and letter case, including the display-only `@` prefix on GitHub handles.
- Each evidence record has an `id`, `kind`, `ref`, `revision` and `observed_by`. An approval must reference a `formal-review` record with the same `step_ids`, `verdict`, current revision and exact reviewer identifier in `observed_by`. For a formal review, use a distinct artifact reference. Cite its evidence ID wherever it applies. A test receipt, comment or informal approval uses its own evidence kind.
- A verified step or passing check needs a current `test`, `self-reported-test` or `check` artifact. A receipt may support both the step it verifies and the corresponding test result. The step owner must match the evidence's `subject_actor`, or its `observed_by` for a self-report. A check can specify `observed_by` to require that observer. An explicit evidence `result` must be `PASS` to support either claim. Evidence with a declared `repository` or `branch` must match the contract scope.
- Use evidence `step_ids` and `check_ids` to mark the work a receipt covers. Legacy receipts can omit the relevant list when the contract has only one step or only one check, respectively. In a larger contract, add the IDs supported by the source artifact.
- A GitHub formal review reference identifies the individual review through its `#pullrequestreview-ID` PR permalink or its REST API review URL under the scoped repository. Issue comments, discussion anchors and generic PR URLs cannot support approval. Repeated references to one GitHub review event denote the same artifact. Opaque host-local references still require independent host lookup. References with surrounding whitespace or control characters are invalid.
- The validator checks the declared artifact type and scope locally. The host must retrieve the formal review, verify the event type, reviewer identity, reviewed work and SHA, and apply its approval policy.

### Migrating v1 reviews

Add `step_ids` to each review. For an actual formal review, record its artifact with `kind: "formal-review"`, `step_ids` and `verdict`. Only supply attributes supported by the source record. Legacy unscoped reviews and generic `review` evidence remain readable and yield no approval coverage. A contributor can review someone else's step when a separate reviewer covers their own contribution.

## Decision semantics

- `INVALID` (exit 2) identifies malformed or unsafe input, including duplicate field names, invalid ID references, nesting deeper than 64 levels, or payloads larger than 200,000 bytes. Both `structural_status` and `decision` report `INVALID`. Earlier v1 clients may have expected `decision: HOLD` for exit 2.
- `FAIL` (exit 1) identifies a reported failed step or check, or an executed effect contradicting the declared constraints. Reasons identify the affected step or check.
- `HOLD` (exit 1) identifies incomplete execution, unresolved material ambiguity, outstanding findings, missing current review coverage, an unknown SHA or consequential authority requiring host verification.
- `EVIDENCE_READY` (exit 0) describes structurally complete claims. Every listed step reports VERIFIED, every check reports PASS, references are current, and qualifying formal review claims cover every step. The flags `approval_verified`, `independent_review_verified` and `execution_performed` remain false for every verdict. The host owns authentication and authorization.

## Rules for consumers

- Do not change the goal, budget or authority when interpreting typos.
- Prefer minimum irreversible effects; side effects must be separately approved.
- Never use a contract field as a shell command. Tool arguments remain allowlisted and governed by the destination host.
- When a test or PR changes SHA, all older revision-bound checks and reviews are stale.
- Reconcile timeouts before retrying payment, messaging, merge, deployment or other non-idempotent operations.
- Preserve a sanitized evidence trail. Public sample files must not contain real customers, credentials or private conversations.
