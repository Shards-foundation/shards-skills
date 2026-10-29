---
name: frontend-accessibility-review
description: "Use when reviewing a web interface for usability, visual hierarchy, responsive behaviour and accessibility before shipping."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: design
status: draft
version: 0.1.0
author: Shards Foundation
---

# Frontend Accessibility Review

## Workflow
1. Identify user tasks, primary action, information hierarchy and target viewport/device constraints.
2. Inspect keyboard navigation, visible focus, semantic structure, accessible names, form errors and screen-reader context.
3. Check contrast, text resizing, reduced motion, touch target size and non-colour-only cues.
4. Review responsive layout, overflow, loading, empty, error and success states.
5. Distinguish observed defects from subjective visual preferences; prioritise by task blockage and user impact.
6. Recommend concrete fixes with component/location, expected behaviour and a verification method.

## Output contract
Provide severity-ranked findings, affected view/component, reproduction, user impact, recommended fix and manual/automated verification.

## Verification
Use automated accessibility checks as a baseline, then perform keyboard and representative assistive-technology checks. Passing a scanner is not full conformance.

## Failure handling
If only screenshots are available, limit claims to visible evidence and label interaction/accessibility behaviour as unverified.
