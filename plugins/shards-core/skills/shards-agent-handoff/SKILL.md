---
name: shards-agent-handoff
description: "Use to validate and write a sanitized structured task checkpoint when transferring work between agents or sessions."
license: MIT
---
# shards-agent-handoff

## Preconditions
Python 3.11+ and a local checkout with permission to inspect the requested path. The host must expose a shell or Python execution tool. The skill cannot grant itself more authority.

## Workflow
1. Prepare factual state: goal, repository, branch, commit, completed steps, decisions, evidence, blockers and next actions.
2. Remove secrets and private data manually; use only a local input file and explicit output path.
3. Run the packaged handoff validation command; inspect the resulting sanitized JSON.
4. On resume, confirm commit and tool state again; the checkpoint is not persistent model memory.

## Execution
Invoke from the plugin package root: python scripts/run.py handoff --input CHECKPOINT.json --output SAFE_CHECKPOINT.json
For the repository checkout use: python plugins/shards-core/scripts/run.py handoff --input CHECKPOINT.json --output SAFE_CHECKPOINT.json

## Output contract
A validated JSON task checkpoint written only to the explicitly selected output file.

## Verification
Re-open the output, confirm required keys, dates/revisions and that no sensitive information is included.

## Failure handling
Reject missing fields, malformed arrays or detected credential patterns. Never overwrite an existing output.

## Trust boundary
This workflow is local and does not access networks, credentials or remote APIs. A reported pass is limited to the checks described above; verify the host supports process execution before invoking.
