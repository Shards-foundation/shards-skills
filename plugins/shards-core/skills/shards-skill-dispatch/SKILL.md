---
name: shards-skill-dispatch
description: "Use when an agent must select and invoke a reviewed Shards skill through a bounded, auditable local dispatcher."
license: MIT
---

# Shards Skill Dispatch

## Preconditions
Python 3.11+ and a full Shards Skills checkout. Run only in an authorised repository workspace with access to first-party programs. The host remains responsible for granting execution and filesystem permissions.

## Workflow
1. Discover curated capabilities using the dispatcher list command; never import arbitrary skill source as executable code.
2. Select the exact curated skill identifier, and prepare any validated target skill name or workflow profile.
3. Inspect the plan; verify its command, code revision, script hash, effect classification and timeout.
4. Obtain runtime authorization and execute using the explicit --execute flag.
5. Inspect the observation and status; keep sanitized JSON receipt evidence.
6. For imported packages, use only the read-only audit operation. External side effects and production execution are outside this dispatcher.

## Execution
From repository root:

    python scripts/dispatch_skills.py list
    python scripts/dispatch_skills.py plan --skill shards-repository-health
    python scripts/dispatch_skills.py run --skill shards-repository-health --execute --save-receipt
    python scripts/dispatch_skills.py run --skill shards-skill-audit --target-skill release-readiness --execute

Checkpoint writes require --allow-local-write and use files under .shards/state only.

## Output contract
JSON list, plan, or execution receipt with skill ID, exact command, source revision, code hash, effect classification, timestamps, exit code and observed outcome. HOLD means the local release gate refused to certify readiness.

## Verification
Check the runner exit status, receipt hash and source commit. Passing local checks is not evidence of production readiness or host plugin compatibility.

## Failure handling
Fail closed for unknown skills, missing descriptors, symlinked executables, invalid target names, ambiguous file paths, unapproved writes or failed subprocesses. Never dynamically evaluate commands supplied by SKILL.md or a language model.

## Trust boundary
Skill instructions never grant privileges; repository scripts require trusted review. Plugin installation and execution policy must be independently enforced by the host.
