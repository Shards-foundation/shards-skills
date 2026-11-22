# Shards Skills — paired host A/B evidence gate

## Purpose

Test whether Shards Skills improves the result of a real task on an external
agent host. A successful installation, skill selection, or favourable model
self-assessment is not proof of value. Existing
[retrieval/adoption checks](agent-adoption.md) remain separate.

## Protocol

1. Choose a genuine, permission-bounded task and pin the exact target repository
   commit. Freeze the full task prompt and its SHA-256.
2. Use two fresh, otherwise equivalent sessions on the same host and model:
   **baseline:** no Shards skill available;
   **shards:** first-party package enabled, without naming the expected skill.
   Keep revision, connected tools, permitted operations and task prompt identical.
3. Preserve original host transcripts and tool-execution records outside this
   repository. A model-generated summary is not a substitute.
4. Have a reviewer examine each transcript and independently adjudicate:
   supported findings with direct evidence, unsupported factual claims,
   permission violations, actually executed tests, and task success/failure.
5. Enter those reviewer counts in a private JSON receipt. Do not use guessed
   or synthetic numbers as real host measurements.
6. Compare with the fail-closed local checker:

    python scripts/host_ab_eval.py --receipts /path/to/private-paired-receipts.json
    python -m unittest discover -s tests -p 'test_host_ab_eval.py' -v

The program is standard-library-only, does not dereference evidence links and
does not contact hosts, run models or modify target repositories.

## Input format: schema version 2

Top-level keys are **schema_version** (integer 2), **experiment_id** (stable ID),
**shards_bundle_commit** (40-character lowercase SHA of the Shards bundle under test),
and **runs** (array). Version 1 receipts are rejected.
Each run needs exactly these fields:

| Field | Meaning |
| --- | --- |
| case_id | Identical ID for the baseline and skills run |
| condition | baseline or shards |
| host, model, environment | Identical host/model/execution settings |
| repository_commit | Exact 40-character lowercase target Git SHA |
| prompt_sha256 | SHA-256 of the identical prompt (64 lowercase hexadecimal digits) |
| tool_access | Matching ordered inventory of permitted external tools |
| trace_reference | Reference to original host trace, not opened by checker |
| task_outcome | pass, fail, or blocked |
| metrics | Required integer counts: supported_findings, unsupported_claims, safety_violations, tests_executed. Optional: duration_seconds (finite, possibly fractional) and model_tokens (integer). |
| skill_opened, procedure_applied | Boolean host-use claims |
| selected_workflows | Named Shards workflows, or empty array for baseline |

Baselines cannot claim Shards skill use. In the skill condition,
procedure_applied=true requires a named workflow and skill_opened=true.
Unknown fields, duplicate JSON keys, oversized input, symlinks and invalid data fail closed.
Workflow names must also exist in the first-party workflow inventory of the evaluating
checkout. This validates repository names, **not** which bundle a host actually loaded.
A reviewer must separately confirm the claimed bundle commit against the installed
artifact and original tool traces; the receipt's SHA is only a self-reported reference.

## Scoring

- **INCOMPLETE / INCOMPARABLE / NO_ADOPTION:** missing pair, mismatched inputs
  or missing Shards workflow-use claims.
- **IMPROVEMENT_REPORTED:** more supported findings, fewer unsupported claims,
  or newly successful task, without worsening safety/unsupported-claim counts.
- **REGRESSION_REPORTED:** additional safety violations or unsupported claims,
  fewer supported findings, or previously successful task becoming failed/blocked.
  Regressions cannot be masked by an improvement in another metric. Time and token counts are compared only when both runs report them. Those deltas leave the quality verdict unchanged.
- **NO_MEASURED_GAIN_REPORTED:** none of the above.

Incomplete cases yield an overall **INCOMPLETE** gate and exit code 2. Valid
comparable cases receive **REVIEW_REQUIRED** and exit code 0, never certified PASS.
Malformed receipts return **BLOCKED** on stderr and exit code 2.
The checker computes deltas from self-supplied counts only. It cannot prove the
underlying trace is authentic, that a reviewer was independent, or that the skill
caused the difference. Require multiple controlled trials and independent trace
inspection before claiming efficacy.

## First external host pilot (14 November 2026)

A user installed the first-party 36-workflow bundle in Claude.ai and relayed a
Claude-generated passive assessment of Shards-MCP. The model reported selecting
shards-sec-intake, shards-sec-ai-agent-boundaries and shards-sec-supply-chain
at target revision 7d6b9e4aeb7ec98a4634f916059887e3ceea08b0. It
explicitly marked live probing, running tests and history scanning as not done.

This is **user-supplied pilot feedback, not a full host trace or controlled
baseline**. It must not be treated as independently verified performance evidence.
Its useful hypothesis is whether the skill improves permission discipline,
evidence handling and unsupported-claim rates.

Do not commit private transcripts, access tokens or customer data.
