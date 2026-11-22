# Governed local skill execution

The first-party catalogue under `skills/` contains instruction workflows. The curated plugin package under plugins/shards-core/skills/ has its own reviewed descriptors. scripts/dispatch_skills.py maps exact approved names to exact first-party Python entry points.

## Commands from the repository root

    python scripts/dispatch_skills.py list
    python scripts/dispatch_skills.py plan --skill shards-repository-health
    python scripts/dispatch_skills.py run --skill shards-repository-health --execute --save-receipt
    python scripts/dispatch_skills.py plan --skill shards-skill-audit --target-skill release-readiness
    python scripts/dispatch_skills.py run --skill shards-skill-audit --target-skill release-readiness --execute
    python scripts/dispatch_skills.py run --skill shards-automation-operator --profile weekly --execute --expect-plan-sha256 <reviewed-digest> --save-receipt
    python scripts/dispatch_skills.py run --skill shards-skill-dispatch --execute

For a **plan-pinned run**, inspect the full JSON returned by `plan`, retain its
`plan_sha256`, then pass it to `run` with matching arguments:

    python scripts/dispatch_skills.py plan --skill shards-repository-health
    python scripts/dispatch_skills.py run --skill shards-repository-health --execute --expect-plan-sha256 <reviewed-64-character-sha256> --save-receipt

The digest covers the script argv, effect, timeout, entry point, allowlisted
local Python imports, interpreter launcher and checkout revision.
For commands with an explicit JSON input, the plan also records the absolute
`input_file` and the SHA-256 of its bytes in `input_sha256`. The child receives those
bytes on stdin (`--input -`). The dispatcher rechecks the path, file digest, argv,
descriptor, executable and revision, then runs the verified entry point and
local imports without reopening their files. A missing revision or mismatched digest exits 2.
Regenerate plans created before this digest format.

File-input operations, local writes, maintenance runs and release gates require
a reviewed digest through `--expect-plan-sha256` or the Python entry point's
`expect_plan_sha256` argument. Generate the plan with the same options and
retain its digest after reviewing it. Other read-only commands accept an
optional digest. Source trees inspected by a workflow and scripts launched by
a secondary runner remain outside the explicit JSON input digest.

A release check may yield HOLD and a nonzero CLI exit code; this is an expected gate outcome.

The authority preflight and execution contract validators include their structured
result in `observation.report`. The diagnostic tails can be truncated. If the
sanitised result exceeds 262,144 characters or cannot be read as a JSON object,
the dispatcher records `observation.status` as `fail` with an explicit error and
retains the child process exit code for diagnosis.

For a validated checkpoint handoff, create sanitized JSON input in .shards/state/ then explicitly allow a local output:

    python scripts/dispatch_skills.py run --skill shards-agent-handoff --input-file .shards/state/input.json --output-file .shards/state/output.json --allow-local-write --execute --expect-plan-sha256 <reviewed-digest>

The plan records the destination in `output_file`. The dispatcher publishes the
complete checkpoint from private staging only after the validator exits successfully.
The filesystem must support hard links for create-only publication. Publication
uses directory-relative operations on POSIX and retained path handles on Windows.
Other platforms require a supported way to anchor the destination before writing.

No dispatcher operation can publish packages, deploy, merge pull requests, call external APIs or run imported scripts. The dispatcher audit can inspect a first-party skill by name. For an external folder, use the local `audit-skill --path` command directly in a disposable environment.

## Safety and evidence

The dispatcher checks curated descriptors and trusted executable paths before constructing an argv list. It does not invoke shell expansion or dynamically evaluate model-generated commands. A timeout applies to each process. JSON execution receipts include status, exit code, script SHA-256 and current Git revision. --save-receipt writes a create-only JSON file in ignored reports/dispatch/.

The plan command is read-only. The run command additionally requires --execute. Handoff additionally requires --allow-local-write, and input/output paths must be under .shards/state/*.json. The underlying handoff validator provides another validation layer. CLI flags and plan hashes are integrity checks, **not** identity-bound approvals, a process sandbox, cryptographic permits or a production policy-enforcement boundary. A caller able to recompute and supply its own digest is not independently authorised. Plan validation is not an atomic filesystem snapshot and cannot eliminate a malicious local race after validation. The trusted host must independently enforce authorization.

Inspect external skills with the static audit in an isolated checkout. A static scan is not proof of trust. Manifest validation does not establish actual compatibility with any particular AI host.

## Verification commands

    python scripts/verify_plugins.py --check
    python -m unittest discover -s tests -v
    python scripts/automate.py run --workflow verify --output-dir reports/automation
