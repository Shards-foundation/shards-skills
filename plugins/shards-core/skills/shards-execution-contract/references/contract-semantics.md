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
- `reviews`: `{reviewer, revision, verdict, open_findings, evidence_ids}`. Verdict: `APPROVED`, `CHANGES_REQUESTED`, `BLOCKED`. Reviewer must differ from executor to be counted as independent *by reported identity*. No signature or identity verification occurs here.
- `evidence`: `{id, kind, ref, revision, observed_by}`. References must be nonempty, linked by ID, and bound to current head revision. This is a provenance claim; the validator does not open URLs.

## Decision semantics

`INVALID`: malformed fields, unknown states, duplicate IDs, unreferenced evidence, suspected embedded credentials.

`HOLD`: structurally valid but incomplete execution, unresolved material ambiguity, failed/not-run check, no matching independent review, open finding, unknown SHA or any high-impact effect declared allowed without host permission verification.

`EVIDENCE_READY`: all listed steps are reported VERIFIED, checks PASS with evidence, and a different reported reviewer APPROVED the current SHA with zero open findings. This **does not** mean mergeable, approved by the real host, independently verified or safe for production. A host must retrieve the referenced evidence, review policy and approvals, then decide the next permissible action.

`FAIL`: any explicit FAILED step or FAIL check; no automatic advance.

## Rules for consumers

- Do not change the goal, budget or authority when interpreting typos.
- Prefer minimum irreversible effects; side effects must be separately approved.
- Never use a contract field as a shell command. Tool arguments remain allowlisted and governed by the destination host.
- When a test or PR changes SHA, all older revision-bound checks and reviews are stale.
- Reconcile timeouts before retrying payment, messaging, merge, deployment or other non-idempotent operations.
- Preserve a sanitized evidence trail. Public sample files must not contain real customers, credentials or private conversations.
