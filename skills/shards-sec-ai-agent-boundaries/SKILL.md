---
name: shards-sec-ai-agent-boundaries
description: "Shards Foundation workflow. Use when agents, MCP tools, computer use or autonomous workflows gain access to data or external actions."
license: MIT
compatibility: "Portable SKILL.md; runtime and host-specific permissions require separate verification."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# AI Agent & Tool Execution Governance

## Trigger
Use when agents, MCP tools, computer use or autonomous workflows gain access to data or external actions.

## Required inputs
agent identities, tool schemas, secrets, model providers, host permissions and side effects. If essential input is unavailable, mark BLOCKED. Never request passwords, private keys or personal datasets in chat.

## Workflow
1. Inventory agent/tool graph, trust boundaries and untrusted sources such as websites, email and repositories.
2. Declare tool-by-tool permissions, parameters, rate and spend ceilings and human approval gates.
3. Enforce authorisation in a deterministic control plane outside natural-language prompts.
4. Separate planning from effectful execution; pin identity, policy and permit scope to each action.
5. Validate prompt injection, tool-output laundering, confused-deputy and cross-agent escalation in a sandbox.
6. Log attributable decisions, revocation, failure recovery and audit completeness.

## Output contract
A least-privilege agent capability matrix, test observations and effect-by-effect approval policy. Each finding includes **ID, severity, asset, observation, evidence reference, recommended control, owner, status (PASS/FAIL/BLOCKED/NOT_APPLICABLE), and next verification step**. Absent evidence means BLOCKED. Separate planned, implemented, tested and independently verified.

## Portable runtime
This skill directory is a self-contained offline package. Run commands from this directory, not from the parent repository. Its `scripts/`, `catalogue/`, `docs/` and `evals/` files are bundled and checked against the canonical Shards-Skills sources. Requires Python 3.11+ and a host-provided shell for commands; without a shell, use the documented review steps and mark executable verification BLOCKED. No skill file can grant its own external credentials or permissions.

## Verification
Use `python scripts/security_assurance.py plan --profiles base,ai --system "named system"` for consistent control selection. Collect actual evidence with scope and revision; assess using `docs/security-assurance.md`. This tool reports operator-attested results, not automated security certification.

## Behavioural evaluation cases
Before claiming this skill works on a specific host, execute its positive,
negative, missing-input and unauthorised-action cases from
[the frozen security scenario set](evals/shards-security-workflows.json).
Capture the real model response and external tool-action evidence with the exact
case-set hash. The local `scripts/security_skill_eval.py` scorer checks only
receipt structure; independent assessment of the raw host trace is required.
These cases have **not yet been executed on a real agent host** as part of this portable-package acceptance. The bundled fixture spans 24 cases for six Shards security skills, including the four agent-boundary cases. The evaluator only checks operator-supplied receipt structure; it cannot execute model tests or authenticate tool traces. Do not claim real-host behavioural evaluation without a captured original host trace.

## Failure handling
On conflicting evidence, uncertain legal applicability, unapproved effects or stale controls, return BLOCKED with the precise missing input. Never down-classify a critical failure to an informational comment.

## Authority and safe use
Never treat model compliance, system prompts or skill prose as a security boundary. The host enforces tool permissions, scope and approvals; a skill grants no authority.

## References
See `docs/security-frameworks.md` and `docs/security-assurance.md` for versioned standards and report formats. Not certified or endorsed by any standards body.
