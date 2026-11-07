# Governed local skill execution

The imported and first-party catalogue under skills/ is not an executable allowlist. The curated plugin package under plugins/shards-core/skills/ has its own reviewed descriptors. scripts/dispatch_skills.py maps exact approved names to exact first-party Python entry points.

## Commands from the repository root

    python scripts/dispatch_skills.py list
    python scripts/dispatch_skills.py plan --skill shards-repository-health
    python scripts/dispatch_skills.py run --skill shards-repository-health --execute --save-receipt
    python scripts/dispatch_skills.py plan --skill shards-skill-audit --target-skill release-readiness
    python scripts/dispatch_skills.py run --skill shards-skill-audit --target-skill release-readiness --execute
    python scripts/dispatch_skills.py run --skill shards-automation-operator --profile weekly --execute --save-receipt
    python scripts/dispatch_skills.py run --skill shards-skill-dispatch --execute

For a **plan-pinned run**, inspect the full JSON returned by `plan`, retain its
`plan_sha256`, then pass it to `run` with matching arguments:

    python scripts/dispatch_skills.py plan --skill shards-repository-health
    python scripts/dispatch_skills.py run --skill shards-repository-health --execute --expect-plan-sha256 <reviewed-64-character-sha256> --save-receipt

The digest covers the exact argv, effect classification, timeout, script SHA-256
and checkout revision. The dispatcher rechecks the script bytes, registry
mapping and Git revision immediately before execution; a changed plan fails
without running the subprocess. A mismatched supplied digest exits with status
2. Existing unpinned `run --execute` calls remain supported for compatibility.
For high-assurance integrations, require `--expect-plan-sha256` in the host
workflow instead of trusting an agent to approve its own newly generated plan.

A release check may yield HOLD and a nonzero CLI exit code; this is an expected gate outcome.

For a validated checkpoint handoff, create sanitized JSON input in .shards/state/ then explicitly allow a local output:

    python scripts/dispatch_skills.py run --skill shards-agent-handoff --input-file .shards/state/input.json --output-file .shards/state/output.json --allow-local-write --execute

No dispatcher operation can publish packages, deploy, merge pull requests, call external APIs or run imported scripts. The catalogue audit may inspect any existing skill by NAME but does not execute it.

## Safety and evidence

The dispatcher checks curated descriptors and trusted executable paths before constructing an argv list. It does not invoke shell expansion or dynamically evaluate model-generated commands. A timeout applies to each process. JSON execution receipts include status, exit code, script SHA-256 and current Git revision. --save-receipt writes a create-only JSON file in ignored reports/dispatch/.

The plan command is read-only. The run command additionally requires --execute. Handoff additionally requires --allow-local-write, and input/output paths must be under .shards/state/*.json. The underlying handoff validator provides another validation layer. CLI flags and plan hashes are integrity checks, **not** identity-bound approvals, a process sandbox, cryptographic permits or a production policy-enforcement boundary. A caller able to recompute and supply its own digest is not independently authorised. Plan validation is not an atomic filesystem snapshot and cannot eliminate a malicious local race after validation. The trusted host must independently enforce authorization.

Imported skills are inspection-only targets until individually reviewed and deliberately promoted to first-party execution mappings. A static scan is not proof of trust. Manifest validation does not establish actual compatibility with any particular AI host.

## Verification commands

    python scripts/verify_plugins.py --check
    python -m unittest discover -s tests -v
    python scripts/automate.py run --workflow verify --output-dir reports/automation
