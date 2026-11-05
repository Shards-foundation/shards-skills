---
name: shards-skill-audit
description: "Use before executing, importing or publishing an agent skill to inspect frontmatter, links, scripts, provenance and trust status."
license: MIT
---
# shards-skill-audit

## Preconditions
Python 3.11+ and a local checkout with permission to inspect the requested path. The host must expose a shell or Python execution tool. The skill cannot grant itself more authority.

## Workflow
1. Identify the exact local skill directory; do not fetch or execute unreviewed code.
2. Execute the packaged read-only audit command against its SKILL.md and adjacent files.
3. Examine metadata, relative paths, source provenance and listed scripts; escalate any imported or review-stage package.
4. Return explicit pass/review/block status and human-review items; never certify code safety from a heuristic scan.

## Execution
Invoke from the plugin package root: python scripts/run.py audit-skill --path SKILL_DIRECTORY [--output REPORT.json]
For the repository checkout use: python plugins/shards-core/scripts/run.py audit-skill --path SKILL_DIRECTORY [--output REPORT.json]

## Output contract
JSON with metadata, script inventory, findings and execution eligibility.

## Verification
Confirm inspected files and paths; manual review and sandbox tests remain required before executing third-party scripts.

## Failure handling
If SKILL.md or provenance is missing, fail closed and do not invoke scripts from that package.

## Trust boundary
This workflow is local and does not access networks, credentials or remote APIs. A reported pass is limited to the checks described above; verify the host supports process execution before invoking.
