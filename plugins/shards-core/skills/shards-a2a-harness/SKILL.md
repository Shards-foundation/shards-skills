---
name: shards-a2a-harness
description: "Use when checking that the local Shards agent harness can delegate read-only tasks with independent agent identities and verifiable receipts."
license: MIT
---

# shards-a2a-harness

## Preconditions

Python 3.11+, trusted full Shards Skills checkout, and local permission from the host to run first-party read-only scripts. No network account or LLM API credentials required.

## Workflow

1. Review the current repository scope and the exact curated delegation targets.
2. Inspect a plan with `python scripts/shards_agent_harness.py plan --profile a2a`.
3. Obtain host authorisation before running the fixed action.
4. Local A2A-oriented handshake: coordinator delegates repository health and curated plugin integrity checks. This does not implement the A2A wire protocol.
5. Examine `control_channel`, `data_channel`, sub-agent exit codes, plan digest, run identifier and aggregate result.
6. Do not execute or promote imported review-stage skill code.

## Execution

From the full repository root:

    python scripts/shards_agent_harness.py plan --profile a2a
    python scripts/shards_agent_harness.py a2a-check --execute

The same curated operation is exposed through the governed dispatcher:

    python scripts/dispatch_skills.py plan --skill shards-a2a-harness
    python scripts/dispatch_skills.py run --skill shards-a2a-harness --execute

For a separately stored JSON receipt:

    python scripts/shards_agent_harness.py run --profile a2a --execute --save-receipt

## Output contract

A JSON record with distinct control and data channels, exact task and sub-agent IDs, observed statuses, a bounded worker count, plan SHA-256, sub-receipts and an aggregate pass/fail result. Any failing sub-agent produces a failing aggregate.

## Verification

Run `python -m unittest discover -s tests -p 'test_agent_harness.py' -v`. Check aggregate status and reported per-task evidence. Passing local checks does not prove A2A network compatibility, durability, sandboxing or cross-vendor runtime interoperability.

## Failure handling

Unknown skills, excessive tasks or workers, altered plans, missing descriptors, revision drift and unapproved execution fail closed. Task failures remain attributed to their subagent. No retries, untrusted command injection, external writes or remote agent connections are permitted.

## Trust boundary

This is a local, deterministic, one-level agent harness, not a network A2A service. It does not publish an Agent Card, transport A2A requests, establish cryptographic identity or enforce OS sandbox isolation. Host permissions and review gates remain authoritative.
