---
name: release-readiness
description: "Use before releasing a library, application, agent, API, or infrastructure change to determine whether evidence supports handover."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Release Readiness

## Workflow
1. Confirm scope, target version, supported environments and rollback path.
2. Verify build, unit tests, integration tests, type checks, lint and packaging appropriate to the project.
3. Inspect dependency/licence changes, secrets exposure, permissions, migration safety and supply-chain signals.
4. Check configuration examples, docs, changelog, observability, health checks and failure recovery.
5. Confirm deployment evidence and smoke tests for the actual target environment; distinguish local from production verification.
6. Record blockers with severity, owner, mitigation and release decision.

## Runnable local preflight

Local release evidence preflight. Default result is HOLD until tests are explicitly approved and run. Even a local READY is not production authorization.

Prerequisite: full Shards Skills checkout with the curated plugins/shards-core runner and Python 3.11+. From repository root:

    python skills/release-readiness/scripts/run.py --repo .

The [adapter script](scripts/run.py) delegates to the curated Python runner and returns machine-readable JSON. This is a bounded, repeatable preflight, not a substitute for the remaining human or agent-guided Workflow steps.

## Output contract
Return a release gate table with status, evidence, timestamp/commit where available, risk and go/no-go recommendation.

## Verification
A green build alone is not release readiness. Each critical acceptance criterion needs evidence or an explicit waiver.

## Failure handling
Block release for unresolved critical security/data-loss risks or missing rollback for a risky migration. Never fabricate deployment status.
