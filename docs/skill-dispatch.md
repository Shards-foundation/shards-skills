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

A release check may yield HOLD and a nonzero CLI exit code; this is an expected gate outcome.

For a validated checkpoint handoff, create sanitized JSON input in .shards/state/ then explicitly allow a local output:

    python scripts/dispatch_skills.py run --skill shards-agent-handoff --input-file .shards/state/input.json --output-file .shards/state/output.json --allow-local-write --execute

No dispatcher operation can publish packages, deploy, merge pull requests, call external APIs or run imported scripts. The catalogue audit may inspect any existing skill by NAME but does not execute it.

## Safety and evidence

The dispatcher checks curated descriptors and trusted executable paths before constructing an argv list. It does not invoke shell expansion or dynamically evaluate model-generated commands. A timeout applies to each process. JSON execution receipts include status, exit code, script SHA-256 and current Git revision. --save-receipt writes a create-only JSON file in ignored reports/dispatch/.

The plan command is read-only. The run command additionally requires --execute. Handoff additionally requires --allow-local-write, and input/output paths must be under .shards/state/*.json. The underlying handoff validator provides another validation layer. CLI flags are intent controls, not a process sandbox, cryptographic permit or production policy-enforcement boundary. The trusted host must independently enforce authorization.

Imported skills are inspection-only targets until individually reviewed and deliberately promoted to first-party execution mappings. A static scan is not proof of trust. Manifest validation does not establish actual compatibility with any particular AI host.

## Verification commands

    python scripts/verify_plugins.py --check
    python -m unittest discover -s tests -v
    python scripts/automate.py run --workflow verify --output-dir reports/automation
