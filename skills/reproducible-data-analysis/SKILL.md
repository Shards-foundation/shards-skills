---
name: reproducible-data-analysis
description: "Use when analysing a dataset and producing results that need to be reproducible, auditable and resistant to silent data-quality errors."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: data
status: draft
version: 0.1.0
author: Shards Foundation
---

# Reproducible Data Analysis

## Workflow
1. Record dataset origin, retrieval time, licence, schema, row count and known limitations.
2. Preserve the raw input; create a reproducible transformation pipeline rather than editing source data manually.
3. Check missingness, duplicates, type validity, units, outliers, sampling bias and leakage before analysis.
4. State the estimand/question, assumptions, exclusions and statistical method before interpreting results.
5. Use appropriate baselines, uncertainty intervals and sensitivity checks; distinguish correlation from causation.
6. Record code, parameters, environment and random seeds where applicable.
7. Reconcile summary statistics against raw counts and independently check critical calculations.

## Output contract
Include data provenance, quality checks, methods, results with uncertainty, assumptions, reproducibility steps and limitations.

## Verification
A reviewer should be able to rerun the pipeline from documented inputs and reproduce key outputs within stated tolerance.

## Failure handling
If sample size, quality or assumptions are insufficient, report descriptive findings only or state that no defensible conclusion can be drawn.
