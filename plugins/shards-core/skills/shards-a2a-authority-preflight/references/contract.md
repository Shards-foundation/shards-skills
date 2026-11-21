# Authority inventory contract v1

Use one task and only the actions the task actually requires. The JSON is a **sanitised claim inventory**, not a permission token or a complete security attestation. Preserve the original request separately in an operator-controlled store; put only a short non-sensitive goal in this record.

## Required shape

Use a UTF-8 JSON document of at most 256 KiB with at most 32 nested containers. The CLI reads a local file or standard input (`--input -`) with the same limits. Each JSON field name must be unique within its object.

- `schema_version`: exactly integer `1`.
- `task`: `id`, `goal`, `repository` (`owner/name`), `branch`, `head_sha` (full 40-character lowercase hex). An unknown repository or SHA cannot be represented as verified: resolve through read-only discovery or return HOLD manually without manufacturing values.
- `roles`: string IDs `delegator`, `coordinator`, `executor`, `integrator`, `reviewer`, `merge_decider`. Reviewer must differ from executor and integrator. Use consistent spelling for each actor. Case-only variants across roles are ambiguous and yield `INVALID`. Compatible roles may use exactly the same label. The host authenticates identities.
- `actions`: 1–48 objects with `actor`, exact `operation`, `repository` and `branch` matching the task, `permission`, `access`, `policy`, `access_issue`, `evidence_ids`. Only actions in the validator's fixed operation list are accepted; unrecognised effects are not automatically downgraded to READ.
- `evidence`: up to 96 nonsecret source references with unique `id`, `kind` (`delegation`, `capability`, `policy`), `reference`, `revision` (same SHA as relevant action), and `observed_by`. To support an action, every kind also needs `subject_actor`, `operation`, `repository` and `branch` matching that action. `observed_by` identifies the reporting actor assigned to a task role and may differ from the subject. Each source reference must identify a single observation with consistent attribution and kind. For a combined report, use a stable per-record locator such as `local:observations#access-1`. Reusing one locator with conflicting metadata yields `HOLD` for an action citing it as support. The destination host retrieves and verifies the observation.

Status vocabulary:

| Field | Allowed states | Interpretation |
|---|---|---|
| `permission` | `GRANTED`, `UNKNOWN`, `DENIED` | Whether original delegation permits this exact action (not a runtime privilege) |
| `access` | `OBSERVED`, `UNKNOWN`, `DENIED` | Whether this actor's current host/tool access was actually observed |
| `policy` | `VERIFIED`, `UNKNOWN`, `DENIED`, `NOT_APPLICABLE` | Destination gate evidence; `NOT_APPLICABLE` cannot be used for remote writes/merges/deployment |
| `access_issue` | `NONE`, `MISSING_CONNECTOR`, `MISSING_CREDENTIAL`, `TOOL_UNAVAILABLE`, `PERMISSION_DENIED`, `UNVERIFIED` | Cause of missing access; `NONE` only when `access=OBSERVED` |

For any `GRANTED` permission, current-revision `delegation` evidence is required; for any `OBSERVED` access, current-revision `capability` evidence is required; for any `VERIFIED` policy, current-revision `policy` evidence is required. Evidence for a different subject, operation, target or SHA and evidence from an unknown observer cannot satisfy a gate. For legacy v1 inputs, add the four attribution fields from the original observation. Leave unavailable fields absent to preserve the claim as unverified (`HOLD`). Do not infer the subject from the observer. An evidence ID can be checked structurally, but the program does **not** fetch, authenticate or trust its content.

`pr.approve` must belong to the independent reviewer; `pr.merge` to the merge decider; `source.edit` to the executor. The formal reviewer must also be independent of authorship and publication recorded in this inventory (commit, push or PR creation). The merge decider may hold other roles subject to the review independence rule. A merge claim requires its own delegation, capability and destination policy evidence even when the assigned decider also has push access. The validator does not transfer those permissions or prove GitHub account independence. A real review must be a GitHub review with state `APPROVED`, not a comment.

## Decisions and safety

- `CLAIMS_COMPLETE` (exit 0): all **self-reported** required gates contain current-revision supporting references. This **never** authorises an effect, demonstrates host enforcement or proves a real permission.
- `HOLD` (exit 1): one or more effects lack scoped delegation, current effective access, destination-policy evidence or fresh supporting references. Output lists per-action causes and the role to escalate to; it never automatically changes the executor.
- `INVALID` (exit 2): malformed schema, invalid target/scope, unknown operation/status, inconsistent access issue, duplicate IDs, self-review, misassigned merge/review/edit or apparent secret data. Errors do not echo the rejected source content.

Practical interpretation: Claude `git.fetch` can be observed while `git.push` remains UNKNOWN/MISSING_CREDENTIAL. Route an exact file+SHA to an integrator, but require a **separate** authorised task/verification before that integrator publishes. Branch protection 403 means policy UNKNOWN, not disabled. `git.pull` is a local working-tree mutation, unlike `git.fetch`.

## Interoperability

A separate A2A harness may embed this output as **untrusted data-channel evidence**; the coordinator retains lifecycle/authority decisions in its control channel. This validator does not expose an A2A endpoint, issue an Agent Card, connect MCP clients, probe credentials or modify the repository. On handoff recheck live actor, target revision, access and policy.
