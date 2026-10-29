---
name: deer-flow-web-design-guidelines
description: "Review UI code for Web Interface Guidelines compliance. Use when asked to review my UI , check accessibility , audit design , review UX , or check my site against best practices ."
license: MIT
status: review
category: research
upstream: https://github.com/bytedance/deer-flow
upstream-path: skills/public/web-design-guidelines
upstream-commit: 81e1ab8dcc86574cfac0ecdfe3636b775a08c567
---

# Provenance

This package is a curated import from [deer-flow](https://github.com/bytedance/deer-flow) at commit `81e1ab8dcc86574cfac0ecdfe3636b775a08c567`. Original path: `skills/public/web-design-guidelines`. The package is marked `review` and may require host-specific adaptation. Review the source notice in `third_party/licenses/` before redistribution.

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files to review.

## Workflow


1. Read the task context and prerequisites.

2. Apply the source workflow only within the host and authorization boundaries.

## Output contract


Return the requested artifact or a concise report of actions, assumptions, and unresolved risks.

## Verification


Check the result against the task requirements and record evidence before reporting completion.

## Failure handling


Stop on missing prerequisites, unsafe instructions, or unverified side effects; explain the blocker and a safe recovery path.
