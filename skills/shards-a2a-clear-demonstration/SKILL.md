---
name: shards-a2a-clear-demonstration
description: "Turn an agent capability claim into a simple, reproducible, human-readable positive and negative demonstration with honest limitations."
license: MIT
compatibility: "Portable advisory workflow; real host execution and live effects require separately granted tools."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Clear Demonstration: show the evidence, not a claim

## Trigger
Use when an agent reports a capability, completed integration, security control, automation, tool or deliverable that a human or independent reviewer needs to understand or reproduce. Do not require a live demo for every trivial text edit.

## Required inputs
A falsifiable claim, intended audience, exact artifact/revision, available safe environment, tools/access, expected observable success, known limits and one meaningful failure/denial case. Prefer synthetic credentials and test fixtures, never live secrets.

## Workflow
1. **Translate the claim.** State one observable before/after outcome in plain language, with exact target and actor: what is supposed to work, what doesn't, and what evidence would disprove it. Define the demonstration's safety boundary.
2. **Choose the smallest safe route.** Prefer a bounded local/offline demo with synthetic inputs and no external effects. If a live capability requires unavailable infrastructure, label it `NOT_DEMONSTRATED` and offer the smallest authorised setup step, not a fabricated screenshot.
3. **Prepare reproducibility.** Pin source SHA, dependency versions, flags, input fixture, environment and an explicit invocation. Separate commands a human can run from commands *actually executed* in this session.
4. **Show a positive case.** Run or observe one real action through the actual implementation. Capture exit/status code, stable artifact/ref and expected output. If not executed, present it as an executable plan only.
5. **Show a negative/control case.** Demonstrate relevant failure refusal, denied permission, rollback or error path using an authorised harmless test. A positive-only demo is insufficient to claim a security boundary is enforced.
6. **Make it understandable.** Provide a short narrated script: `before -> input -> action -> expected vs observed -> negative case -> limitations -> next step`. Avoid unexplained jargon; provide technical appendix for experts, not as a substitute for the plain-language outcome.
7. **Cross-check independently** where needed. Another actor should be able to reproduce the steps and compare raw outputs at exact SHA. A mock, screenshot, animated UI, simulated agent or test badge cannot establish actual production execution.
8. **Conclude precisely.** `DEMONSTRATED_LOCALLY`, `INDEPENDENTLY_REPRODUCED`, `MOCK_DEMONSTRATED`, `PLAN_ONLY`, `NOT_DEMONSTRATED`, or `FAILED`. Use `MOCK_DEMONSTRATED` only for observed execution of a mock. It establishes only the mock's behaviour. Stop at the agreed evidence threshold.

## Execution
Run only authorised read-only or disposable local tests using reviewed tools; never launch production signing, purchases, live trading, third-party scanning, deployment or credential exposure merely to make a demo impressive. If tooling is missing, record the exact blocker and offer a safe reproduction recipe.

## Output contract
```text
CLAIM / AUDIENCE / ACTOR / ARTIFACT_SHA / ENVIRONMENT:
PREREQUISITES / EXECUTED_COMMANDS / EXIT_CODES / INPUT_FIXTURES:
POSITIVE_CASE: {expected, observed, evidence_ref, status}
NEGATIVE_CASE: {expected, observed, evidence_ref, status}
HUMAN_WALKTHROUGH: before -> action -> visible result -> caveat
REPRODUCTION_STEPS / LIMITATIONS / UNRUN_CHECKS:
VERDICT: DEMONSTRATED_LOCALLY|INDEPENDENTLY_REPRODUCED|MOCK_DEMONSTRATED|PLAN_ONLY|NOT_DEMONSTRATED|FAILED
NEXT_AUTHORIZED_ACTION:
```

## Verification
Ensure both positive and negative results point to real records if reported as executed. Verify the named SHA, commands, environment and scope. Test a still screenshot with no execution (`PLAN_ONLY`), an executed mock (`MOCK_DEMONSTRATED`), an unavailable live service (`NOT_DEMONSTRATED`) and a local positive/negative control of the real implementation (`DEMONSTRATED_LOCALLY`). Use [frozen scenarios](../../evals/shards-a2a-five-workflows.json).

## Failure handling
If an operation cannot be demonstrated safely or with current access, say precisely which component is unobserved and return the minimum safe next step. Do not replace missing evidence with confident narrative, invent a passing test, or infer production certification from a local demo. A failed negative test is a genuine failure and requires correction before claiming the control.

## Trust boundary
This skill cannot prove every requirement of a complex system; it creates inspectable demonstration evidence. Its documented commands and screenshots do not confer host tool access or production authority.
