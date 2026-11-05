---
name: shards-release-gate
description: "Use to decide whether a local Python repository has enough verified evidence for release without publishing or deploying."
license: MIT
---
# shards-release-gate

## Preconditions
Python 3.11+ and a local checkout with permission to inspect the requested path. The host must expose a shell or Python execution tool. The skill cannot grant itself more authority.

## Workflow
1. Establish branch, target revision, release scope and authorization.
2. Run the packaged release-check: default is read-only and requires evidence rather than asserting readiness.
3. Only when the repository code is trusted and the user has permitted local execution, supply both test flags.
4. Check reported command exit code, missing evidence, rollback information and HOLD/READY gate.
5. Never publish, deploy, merge or create tags as part of this skill.

## Execution
Invoke from the plugin package root: python scripts/run.py release-check --repo PATH [--run-tests --trusted-local-code] [--output REPORT.json]
For the repository checkout use: python plugins/shards-core/scripts/run.py release-check --repo PATH [--run-tests --trusted-local-code] [--output REPORT.json]

## Output contract
JSON release gate decision HOLD or READY and observed checks, test command and reasons.

## Verification
READY only follows successful opted-in test execution and required metadata; additional integration/production gates are separate.

## Failure handling
If prerequisites, trust, tests or evidence are absent, decision must be HOLD.

## Trust boundary
This workflow is local and does not access networks, credentials or remote APIs. A reported pass is limited to the checks described above; verify the host supports process execution before invoking.
