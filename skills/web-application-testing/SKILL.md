---
name: web-application-testing
description: "Use when validating a web application or browser workflow across functional states, navigation, forms, accessibility and regressions."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: engineering
status: draft
version: 0.1.0
author: Shards Foundation
---

# Web Application Testing

## Workflow
1. Establish the application URL/environment, test account constraints, target browsers and critical user journeys.
2. Define preconditions, steps and observable expected results before interacting with the application.
3. Cover happy paths, validation failures, empty/loading/error states, permissions, session expiry and retry behaviour.
4. Prefer stable semantic locators and accessible roles over brittle CSS selectors or arbitrary sleeps.
5. Capture screenshots, console/network errors and timestamps for failures, avoiding sensitive data in artefacts.
6. Check keyboard navigation and accessible names on critical flows; use automated scans as a baseline only.
7. Re-run affected journeys after fixes and report environment-specific limitations.

## Output contract
Return test matrix, environment, reproduction steps, expected/actual results, evidence, severity and retest status.

## Verification
A test passes only when the expected state is observed in the target environment. A successful page load does not prove a workflow is correct.

## Failure handling
If authentication, test data or environment access is unavailable, report blocked cases and do not imply end-to-end coverage.
