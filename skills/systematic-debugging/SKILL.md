---
name: systematic-debugging
description: "Use when a system fails, behaves inconsistently, or reports an error whose root cause is not yet established."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Systematic Debugging

## Workflow
1. Capture the exact error, reproduction steps, environment, recent changes, and expected versus observed behaviour.
2. Reproduce the issue with the smallest deterministic case; preserve logs and timestamps.
3. Form competing hypotheses and identify an observation that distinguishes each one.
4. Inspect evidence before changing code. Trace the failure to a root cause rather than patching the first symptom.
5. Apply the narrowest fix and add a regression test.
6. Verify the original reproduction, related edge cases, and relevant suite.
7. Record cause, fix, evidence, risk and any follow-up work.

## Output contract
Include reproduction, root-cause confidence, evidence, fix, verification commands/results, and unresolved hypotheses.

## Verification
The regression test should fail on the pre-fix implementation and pass after the fix. Distinguish proven root cause from likely cause.

## Failure handling
If the issue is not reproducible, gather additional observability instead of making speculative changes. Do not suppress errors merely to obtain a green run.
