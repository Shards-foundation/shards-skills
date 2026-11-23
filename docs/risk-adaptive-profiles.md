# Selecting an assurance profile

Use the standalone selector to decide how much evidence to collect for a task. Its output is advisory. Permit issuance, A2A transport and runtime policy enforcement are outside its scope. The host retains authority over every operation. A known host denial takes precedence at every level, including when the CLI returns `CLASSIFIED`.

## Selection criteria

| Profile | Example of an observed effect | Additional evidence to collect |
| --- | --- | --- |
| `L0_MINIMAL` | A reversible spelling correction that only affects what an ordinary reader sees | Scope, existing authority reference, verification of the relevant change, failure report |
| `L1_STANDARD` | Run an existing script that only reads local data, or refresh a generated documentation index through routine maintenance | Revision, relevant checks, receipts |
| `L2_ENGINEERING` | Change executable behaviour, introduce a local write, or edit instructions consumed by an agent | Regression evidence, security consideration, review where required |
| `L3_CRITICAL` | Change an approval rule, publish externally, touch production, handle sensitive data, or perform an irreversible operation | Strict approval, independent assurance, explicit operational gates |

Evidence requirements accumulate across levels. A prose edit refers to the effect of the content change. Use `local-write` when execution introduces a local write. A run that reads sensitive data still triggers the sensitive floor. Describe the intended operation, the effects of the proposed change and the independently observed effects of changed content.

The registry assigns each effect class a rule ID and a floor. Several signals can apply to the same task. The selector takes the maximum of all observed, declared, repository and requested floors. Listed path patterns can only raise the result. A pattern without a slash matches a basename, and one with a slash matches the whole repository-relative path using case-sensitive shell wildcards. Diff size has no role. A trusted operator can request escalation. An explicit override below any applicable floor produces `HOLD`. The receipt identifies the attempted downgrade and the floor to preserve. [Profile registry](../catalogue/risk-profiles.json)

## Input

Run with Python 3.11+ from a trusted checkout. The CLI reads one UTF-8 JSON object from standard input and the fixed sibling catalogue from disk. It has no options for choosing a replacement policy or opening a task-supplied path. The following input models a README correction at a known repository revision. The correction is illustrative.

```sh
python -IB scripts/classify_risk_profile.py <<'JSON'
{
  "schema_version": 1,
  "target": {
    "repository": "Shards-foundation/shards-skills",
    "revision": "5d42830b59e62c776e5bc638b66fc79f79f9bff2"
  },
  "task_intent": "prose-only",
  "observed_changed_paths": [{"path": "README.md", "effects": ["prose-only"]}],
  "declared_execution_effects": ["prose-only"],
  "instruction_bearing_changes": false,
  "authorization_or_policy_changes": false,
  "external_side_effects": "none",
  "reversibility": "reversible",
  "production_impact": false,
  "minimum_requested_profile": "L0_MINIMAL",
  "repository_policy_constraints": {"minimum_profile": "L0_MINIMAL", "hold": false}
}
JSON
```

The root object is closed. All fields in the example are required. Only `operator_override` is optional.

| Field | Type and meaning |
| --- | --- |
| `schema_version` | Integer `1` for the classification input schema, versioned separately from the execution contract. |
| `target` | Object containing the canonical `repository` (`owner/repo`) and `revision` (full lowercase 40- or 64-hex Git object ID). The caller verifies the target and identifies the exact observed change in its evidence. |
| `task_intent` | One registry effect class describing the intended outcome. Use the other inputs to describe additional effects. Free-form instructions cannot supply an effect class. |
| `observed_changed_paths` | Array of objects with a normalized relative `path` and a nonempty `effects` array of registry classes. Include every changed path and both sides of a rename. Use `[]` for a verified empty change set, such as running an existing read-only check. Use `null` for an uninspected change set. A prose edit requires an identified change. |
| `declared_execution_effects` | Nonempty array of effect classes covering the planned operation. Any class can independently raise the floor. |
| `instruction_bearing_changes`, `authorization_or_policy_changes`, `production_impact` | JSON booleans. A true value applies the corresponding agent-instruction, policy or production floor. Supply `null` for unknown. |
| `external_side_effects` | `none`, `external-read` or `external-write`. Declare sensitive data or privileged access separately even for reads. |
| `reversibility` | `reversible`, `costly-rollback` or `irreversible`. |
| `minimum_requested_profile` | Operator's minimum profile ID. Use `L0_MINIMAL` when the operator imposes no extra floor. |
| `repository_policy_constraints` | Object with a `minimum_profile` ID and a boolean `hold`. A trusted caller supplies the applicable repository policy. Use `null` when it is unknown. A hold survives every operator request. |
| `operator_override` | Optional exact profile ID. An equal or higher value is acceptable. A lower value requires the operator to resolve the conflict. |

Build this observation from the actual target, change and applicable policy. Resolve symlinks and inspect executable, generated and instruction-bearing content at the trust boundary. A PR label, filename or model's description alone is insufficient. Supply unknown for any material fact that cannot be established. The selector cannot authenticate the observer, inspect a diff, detect an omitted effect in an otherwise well-formed account, or look up host permissions. It uses the installed policy from the trusted checkout. Keep that checkout stable during classification and verify its revision separately. Supply sanitized metadata only.

## Receipts and failure reporting

The CLI writes one compact JSON object to stdout. The same input and policy bytes produce the same output bytes. Capture stdout and the process exit code together.

| Decision | Exit | Operator action |
| --- | ---: | --- |
| `CLASSIFIED` | 0 | Collect the reported evidence and apply existing host gates. |
| `HOLD` | 1 | Resolve the named material unknown, repository hold or downgrade attempt, then classify again. |
| `INVALID` | 2 | Correct the malformed input or restore the reviewed registry. Duplicate keys, undocumented fields, conflicting rules, invalid encoding and documents over 200,000 bytes are rejected. |

Every receipt contains `receipt_version` (integer 1), `decision`, `profile` (profile ID or null), `authority_granted` (always false), `input_sha256` and `policy_sha256` (hex digests of the complete original bytes when available), `triggered_rules` (array of objects with `rule_id`, input `source` and `floor`), `required_evidence` (sorted string array) and `reasons` (diagnostic strings). Failure receipts have a null profile, an empty evidence list and a reason identifying the first problem. Rules already observed may be present on failure. Only a classified receipt contains a complete decision. Bind it to its input, policy and source revision when retaining it.

The example above selects `L0_MINIMAL` through `EF-01`. These variations use the same target and all other fields from the example.

| Change to the observation | Expected receipt |
| --- | --- |
| Set `task_intent` and the only declared effect to `read-only`, with `observed_changed_paths: []` | L1 through EF-03 |
| Retain `prose-only` intent and filename `README.md`, but observe `effects: ["local-write"]` in content used as an executable | L2 through EF-06 |
| Change the observed path to `skills/shards-task-contract/SKILL.md` | At least L2 from the instruction-bearing basename |
| Set `authorization_or_policy_changes` to true and request `operator_override: "L0_MINIMAL"` | HOLD with the L3 floor in the reason and the EF-09 trigger in the receipt |
| Set `external_side_effects` to null | HOLD naming the missing observation |

## Existing governance and review

This CLI runs alongside Shards Skills. The dispatcher continues to use its existing allowlist. There is no automatic selector invocation, profile enforcement, ledger entry or change to authority preflight. An L0 result cannot waive an existing requirement. [Dispatcher](skill-dispatch.md)

An authorised operator can attach a receipt to the existing task record as a decision. For a `decision` event, use the ledger's fields `criterion_id`, `action`, `result` and `reference` with a durable reference to the receipt. For acceptance, define each criterion's exact target revision, resource, subject actor and `required_evidence`. Map planned evidence to existing ledger types such as `implemented`, `tested` and, when required, `reviewed`. For example, regression evidence needs an actual `tested` observation with a test receipt. A classification receipt cannot itself satisfy that observation. A host verifier must authenticate the underlying observations. [Operating ledger](operating-loop.md)

Execution-contract schema v1 still requires independent, current formal-review coverage of **every step** for `EVIDENCE_READY`, regardless of selected profile. It structurally checks submitted claims. The host authenticates the review, observer, exact revision and coverage. A distinct authorised reviewer should verify the base and final HEAD, inspect every changed file, reproduce the checks and record a verdict for that HEAD. The repository owner or authorised operator decides any subsequent operation. [Execution contract semantics](../plugins/shards-core/skills/shards-execution-contract/references/contract-semantics.md)

## Rollback

Stop invoking the standalone selector and use the existing operating loop. For an isolated feature checkout, switching back to the verified base restores the previous tree. If the prototype is later integrated, an authorised maintainer can revert its additive commit through ordinary review. Preserve prior receipts with their policy hashes and revisions for audit.
