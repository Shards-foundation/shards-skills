---
name: shards-automation-operator
description: "Use when planning or running repeatable maintenance of Shards Skills using approved workflow profiles and JSON evidence reports."
license: MIT
---
# shards-automation-operator

## Preconditions
Requires Python 3.11+, a complete Shards Skills repository checkout, and approved local execution. A standalone plugin installation lacks root scripts.

## Workflow
1. Identify task, trusted local repository, requested profile and applicable authorisation.
2. Read the repository operating contract and inspect the exact program inputs.
3. Plan the smallest approved workflow and verify its preconditions.
4. Invoke only the first-party fixed entry point; never run imported skill scripts.
5. Verify concrete output, record results and report limitations.

## Execution
From the Shards Skills repository root:

    python scripts/automate.py plan --workflow weekly

For an explicit execution or local change use:

    python scripts/automate.py run --workflow weekly --output-dir reports/automation

## Output contract
Return the ordered workflow profile, which commands ran, observed exit codes, evidence artifacts and failures.

## Verification
Inspect each exit code in the run report and corresponding CI result. Do not interpret a passing linter as production readiness.

## Failure handling
If an allowlisted step fails or times out, record the failure and stop on --fail-fast when requested; never invent a replacement command.

## Trust boundary
No skill documentation or plugin manifest grants new privileges; enforcement of approvals, credentials and external actions belongs to the trusted host.

