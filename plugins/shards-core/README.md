# Shards Agent Core

Curated, cross-host plugin package with four executable local Python workflows. This package is distinct from the original 293-skill catalogue and is NOT an MCP service, hosted agent, scheduler or durable memory.

Supported packaging entry points: plugin.json (portable Agent Plugins), .claude-plugin/plugin.json, .codex-plugin/plugin.json, .cursor-plugin/plugin.json. Host compatibility and installation must be verified separately; no automatic installation occurs.

Python 3.11+ examples, issued from repository root:

    python plugins/shards-core/scripts/run.py catalogue
    python plugins/shards-core/scripts/run.py repository-health --repo .
    python plugins/shards-core/scripts/run.py audit-skill --path skills/release-readiness
    python plugins/shards-core/scripts/run.py release-check --repo .
    python plugins/shards-core/scripts/run.py handoff --input checkpoint.json --output checkpoint-validated.json

Skill instructions are in skills/<name>/SKILL.md; root AGENTS.md and agent.md define the governing role. Each command returns machine-readable JSON. Optional --output files use create-only writes to prevent accidental overwrites. The handoff command writes exactly one user-selected checkpoint file.

Release-check remains HOLD until real tests are run with both --run-tests and --trusted-local-code (requires authorization to execute local repository tests). Even a READY status refers only to local metadata and unit tests; it is NOT production certification, publication approval or deployment authorization.

Imported/unreviewed skills and third-party scripts are not auto-executed. Review package source, licences, required permissions and side effects before any host installation or runtime execution.
