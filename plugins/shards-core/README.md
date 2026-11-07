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

## Additional automation skills

This curated plugin now also provides shards-automation-operator and shards-catalogue-sync. Both require the full Shards Skills checkout and Python 3.11+; standalone plugin installation is insufficient for the root scripts.

    python scripts/automate.py plan --workflow weekly
    python scripts/automate.py run --workflow verify --output-dir reports/automation
    python scripts/catalogue_sync.py --check
    python scripts/catalogue_sync.py --write --approve-write

See docs/automation.md for security boundaries and the scheduled workflow.

## Governed execution
A seventh curated skill, shards-skill-dispatch, provides a policy-bounded entry point through scripts/dispatch_skills.py in the full repository checkout. Run plan before run --execute; no imported skill script is directly executable. See docs/skill-dispatch.md at repository root.


## Local multi-agent harness workflows

Four more curated skills are executable from the full checkout:
shards-a2a-harness, shards-dual-channel, shards-subagents and
shards-parallel-swarm. These perform bounded first-party read-only checks
through the existing dispatcher and emit dual-channel JSON receipts.

~~~bash
python scripts/shards_agent_harness.py list
python scripts/shards_agent_harness.py plan --profile swarm
python scripts/shards_agent_harness.py run --profile swarm --execute --save-receipt
~~~

Fixed skills can also be invoked via scripts/dispatch_skills.py.
This is a local harness, not an A2A wire endpoint or OS sandbox.
See docs/agent-harness.md for its execution envelope.
