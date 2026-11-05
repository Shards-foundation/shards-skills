---
name: shards-repository-health
description: "Use when inspecting the state, metadata and basic integrity of a local code repository before making changes."
license: MIT
---
# shards-repository-health

## Preconditions
Python 3.11+ and a local checkout with permission to inspect the requested path. The host must expose a shell or Python execution tool. The skill cannot grant itself more authority.

## Workflow
1. Identify the authorised local repository path and collect its current commit and working-tree state.
2. Execute the packaged read-only repository-health command; it never executes arbitrary repo code.
3. Review reported missing metadata, changes and tool failures; do not overstate check coverage.
4. Report observed commit, dirty-state, metadata checklist and further tests required.

## Execution
Invoke from the plugin package root: python scripts/run.py repository-health --repo PATH [--output REPORT.json]
For the repository checkout use: python plugins/shards-core/scripts/run.py repository-health --repo PATH [--output REPORT.json]

## Output contract
Structured JSON report with path, commit, changed state, checks and overall status.

## Verification
Compare reported SHA to git rev-parse HEAD and inspect evidence fields. Metadata checks are not tests.

## Failure handling
If not a git repository or Git cannot run, report incomplete evidence. Do not infer a clean or safe build.

## Trust boundary
This workflow is local and does not access networks, credentials or remote APIs. A reported pass is limited to the checks described above; verify the host supports process execution before invoking.
