---
name: writing-skill-packages
description: "Use when authoring or improving an agent skill so it is discoverable, portable, testable and safe to maintain."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Writing Skill Packages

## Workflow
1. Define one capability, the situations that should trigger it, and situations where it should not trigger.
2. Write concise metadata with a specific description; avoid keyword stuffing and claims of universal applicability.
3. Structure instructions as workflow, output contract, verification and failure handling.
4. Move lengthy references and examples into adjacent files; use relative links that resolve inside the package.
5. Avoid assumptions about tools, permissions, environment variables or installed dependencies; state prerequisites explicitly.
6. Add positive and negative trigger examples plus task-specific evaluation cases.
7. Run metadata, link, security and compatibility checks; record version and provenance.

## Runnable local preflight

Validate an existing candidate package before publication. This is one stage, not a full skill authoring or behavioral evaluation.

Prerequisite: full Shards Skills checkout with the curated plugins/shards-core runner and Python 3.11+. From repository root:

    python skills/writing-skill-packages/scripts/run.py --path skills/release-readiness

The [adapter script](scripts/run.py) delegates to the curated Python runner and returns machine-readable JSON. This is a bounded, repeatable preflight, not a substitute for the remaining human or agent-guided Workflow steps.

## Output contract
Return a skill directory with `SKILL.md`, optional references/scripts, test/eval cases, licence/provenance and a short compatibility statement.

## Verification
The skill should trigger on intended tasks, stay inactive on unrelated tasks, produce the promised output and fail safely when prerequisites are absent.

## Failure handling
If a behaviour cannot be tested, mark it unverified and provide a manual test. Do not label the skill production-ready based on formatting alone.
