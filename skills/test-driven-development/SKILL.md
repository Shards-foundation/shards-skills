---
name: test-driven-development
description: "Use when implementing a behaviour change or bug fix where automated tests can express the expected result."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Test Driven Development

## Workflow
1. Inspect existing behaviour, project conventions, and current tests before editing.
2. Write the smallest test that demonstrates the requested behaviour or regression.
3. Run it and confirm it fails for the expected reason. If it fails for setup reasons, fix the test setup first.
4. Implement the minimum change that makes the test pass.
5. Run the focused test, then relevant regression suite, then lint/type checks.
6. Refactor only while tests remain green; add edge cases for boundaries and error paths.
7. Report exact commands, exit codes and any tests not run.

## Output contract
Summarise behaviour changed, tests added, commands executed, results, remaining gaps, and changed files.

## Verification
Never claim a test passed unless its command actually ran and returned success. Tests must fail when the regression is reintroduced.

## Failure handling
If tests cannot run, state the concrete blocker and use static checks only as explicitly weaker evidence. Do not label the work fully tested.
