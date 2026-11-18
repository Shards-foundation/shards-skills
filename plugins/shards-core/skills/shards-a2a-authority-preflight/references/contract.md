# Authority inventory contract v1

Use one task and only the actions the task actually requires. The JSON is a **sanitised claim inventory**, not a permission token or a complete security attestation. Preserve the original request separately in an operator-controlled store; put only a short non-sensitive goal in this record.

## Required shape

- `schema_version`: exactly integer `1`.
- `task`: `id`, `goal`, `repository` (`owner/name`), `branch`, `head_sha` (full 40-character lowercase hex). An unknown repository or SHA cannot be represented as verified: resolve through read-only discovery or return HOLD manually without manufacturing values.
- `roles`: string IDs `delegator`, `coordinator`, `executor`, `integrator`, `reviewer`, `merge_decider`. Reviewer must differ from executor and integrator. IDs are operational labels, not authenticated identities.
- `actions`: 1–48 objects with `actor`, exact `operation`, `repository` and `branch` matching the task, `permission`, `access`, `policy`, `access_issue`, `evidence_ids`. Only actions in the validator's fixed operation list are accepted; unrecognised effects are not automatically downgraded to READ.
- `evidence`: up to 96 nonsecret source references with unique `id`, `kind` (`delegation`, `capability`, `policy`), `reference`, `revision` (same SHA as relevant action), and `observed_by`. These are claims until independently retrieved by the destination host.

Status vocabulary:

| Field | Allowed states | Interpretation |
|---|---|---|
| `permission` | `GRANTED`, `UNKNOWN`, `DENIED` | Whether original delegation permits this exact action (not a runtime privilege) |
| `access` | `OBSERVED`, `UNKNOWN`, `DENIED` | Whether this actor's current host/tool access was actually observed |
| `policy` | `VERIFIED`, `UNKNOWN`, `DENIED`, `NOT_APPLICABLE` | Destination gate evidence; `NOT_APPLICABLE` cannot be used for remote writes/merges/deployment |
| `access_issue` | `NONE`, `MISSING_CONNECTOR`, `MISSING_CREDENTIAL`, `TOOL_UNAVAILABLE`, `PERMISSION_DENIED`, `UNVERIFIED` | Cause of missing access; `NONE` only when `access=OBSERVED` |

For any `GRANTED` permission, current-revision `delegation` evidence is required; for any `OBSERVED` access, current-revision `capability` evidence is required; for any `VERIFIED` policy, current-revision `policy` evidence is required. Missing/stale evidence results in HOLD. An evidence ID can be checked structurally, but the program does **not** fetch, authenticate or trust its content.

`pr.approve` must belong to the independent reviewer; `pr.merge` to the merge decider; `source.edit` to the executor. The validator does not transfer those permissions or prove GitHub account independence. A real review must be a GitHub review with state `APPROVED`, not a comment.

## Decisions and safety

- `CLAIMS_COMPLETE` (exit 0): all **self-reported** required gates contain current-revision supporting references. This **never** authorises an effect, demonstrates host enforcement or proves a real permission.
- `HOLD` (exit 1): one or more effects lack scoped delegation, current effective access, destination-policy evidence or fresh supporting references. Output lists per-action causes and the role to escalate to; it never automatically changes the executor.
- `INVALID` (exit 2): malformed schema, invalid target/scope, unknown operation/status, inconsistent access issue, duplicate IDs, self-review, misassigned merge/review/edit or apparent secret data. Errors do not echo the rejected source content.

Practical interpretation: Claude `git.fetch` can be observed while `git.push` remains UNKNOWN/MISSING_CREDENTIAL. Route an exact file+SHA to an integrator, but require a **separate** authorised task/verification before that integrator publishes. Branch protection 403 means policy UNKNOWN, not disabled. `git.pull` is a local working-tree mutation, unlike `git.fetch`.

## Interoperability

A separate A2A harness may embed this output as **untrusted data-channel evidence**; the coordinator retains lifecycle/authority decisions in its control channel. This validator does not expose an A2A endpoint, issue an Agent Card, connect MCP clients, probe credentials or modify the repository. On handoff recheck live actor, target revision, access and policy.
