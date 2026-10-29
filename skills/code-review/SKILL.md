---
name: code-review
description: "Use when reviewing a diff, pull request, patch, or proposed implementation for correctness, security, maintainability and regression risk."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Code Review

## Workflow
1. Read the task specification and diff; inspect surrounding code only where needed to establish behaviour.
2. Prioritise defects by impact: data loss/security, correctness, reliability, performance, maintainability and style.
3. Trace changed code through callers, state transitions, error paths, concurrency boundaries and input validation.
4. Check tests against behaviour, not merely line coverage. Look for missing negative and boundary cases.
5. For each finding, cite file/line, describe a concrete failure scenario, explain impact, and suggest a fix.
6. Separate actionable defects from questions, preferences and speculative concerns.

## Output contract
List findings highest severity first, then tests/gaps and residual risks. If no defects are found, say what was examined and what remains unverified.

## Verification
Findings must be reproducible or supported by a clear code path. Do not invent line numbers or assert that CI ran unless evidence is available.

## Failure handling
If context is insufficient, label the finding as a question or risk, not a confirmed bug.
