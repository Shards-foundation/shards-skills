---
name: tool-contract-design
description: "Use when creating an agent tool, MCP tool, API action or automation interface that an LLM will call."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: agents
status: draft
version: 0.1.0
author: Shards Foundation
---

# Tool Contract Design

## Workflow
1. Define one narrow capability and a clear side-effect classification: read-only, reversible write, irreversible write or external communication.
2. Design typed inputs with bounds, enums, defaults and explicit required fields; reject ambiguous payloads.
3. Return structured results with status, stable identifiers, timestamps, provenance and machine-readable errors.
4. Add authorization, tenant boundaries, input validation, rate limits, timeouts and output-size limits outside the model.
5. Make writes idempotent where possible and require confirmation for consequential actions.
6. Document examples, error semantics, retry safety and data-handling rules.
7. Test valid, invalid, adversarial, duplicate and partial-failure requests.

## Output contract
Return schema, examples, permission model, side-effect classification, error catalogue, idempotency strategy and test matrix.

## Verification
The schema must distinguish success from partial failure and refusal. Retrying an operation must not accidentally duplicate irreversible effects.

## Failure handling
Fail closed on missing authorization or invalid inputs. Do not silently coerce ambiguous arguments or leak internal secrets in errors.
