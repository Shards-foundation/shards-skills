# Cross-host runtime contract

Three layers are intentionally separate:

1. Identity: AGENTS.md is the canonical repository operating contract. agent.md specifies the operator role and lifecycle.
2. Skills: existing skills/ remains the historical first-party + imported catalogue. plugins/shards-core/skills/ contains an allowlisted, independently packaged executable core.
3. Plugin: plugins/shards-core/plugin.json and compatibility manifests package only curated skills. They do not spawn an MCP server or provide long-term memory.

## Install/discovery boundaries
- ChatGPT / Codex: use the repository-local .agents/plugins/marketplace.json as a local marketplace source on a host that supports repository plugins. No installation happens from committing this file. Private GitHub access is required when obtaining the repository.
- Claude Code: open or install plugins/shards-core as the plugin directory. The package contains .claude-plugin/plugin.json; verify discovery on the installed host.
- Cursor: the package has a portable Agent Plugins manifest and optional .cursor-plugin/plugin.json. Test it as a local plugin before marketplace publication.
- OpenCode: use its documented Agent Skills discovery path with curated skills only. A host adapter must retain each full skill directory, including scripts.
- Hermes, Kimi, Devin, Pi, Antigravity and other agents: do not invent native plugin manifests. Where the host supports Agent Skills, install the curated skill directories with its documented mechanism. Otherwise author and test a separate host adapter.
- GitHub Actions: executes the automated tests from the repository; it does not give the AI agent automatic deployment or merge authority.

## CLI
Run in the repository root: python plugins/shards-core/scripts/run.py --help
Commands: catalogue, repository-health, audit-skill, release-check, handoff.
All default operations are read-only except an explicit handoff output file. A release check is HOLD unless its approved test evidence is present. Running untrusted repository tests is opt-in.

## Coverage and readiness
The existing 293 top-level packages were not converted wholesale. The curated plugin contains six curated skill packages: four core executable workflows and two root-repository automation workflows. Imported packages stay review-stage, are not auto-executed, and are not auto-loaded into the curated plugin. Extend by adding new reviewed wrappers with tests and matching output contracts. Host compatibility must be demonstrated, not inferred from file extensions.
