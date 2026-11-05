---
name: shards-catalogue-sync
description: "Use to check and explicitly repair Shards Skills catalogue metadata drift while preserving skill directory identity and provenance."
license: MIT
---
# shards-catalogue-sync

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

    python scripts/catalogue_sync.py --check

For an explicit execution or local change use:

    python scripts/catalogue_sync.py --write --approve-write

## Output contract
Return discovered skill count, catalogue paths, missing entries, metadata drift and whether a tracked file changed.

## Verification
Review generated JSON and Git diff. Run metadata validation before committing an approved repair.

## Failure handling
If skill paths or catalogue entries are missing or source files malformed, refuse automatic repair and report the blocking condition.

## Trust boundary
No skill documentation or plugin manifest grants new privileges; enforcement of approvals, credentials and external actions belongs to the trusted host.

