---
name: evidence-based-research
description: "Use when answering a complex factual question that needs source comparison, current evidence, traceable claims or a decision brief."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: research
status: draft
version: 0.1.0
author: Shards Foundation
---

# Evidence Based Research

## Workflow
1. Convert the question into answerable subquestions and define the time horizon and inclusion criteria.
2. Search primary sources first: specifications, official documentation, papers, repositories, datasets and direct statements.
3. Record source URL, author/publisher, publication or update date, retrieval date and exact claim supported.
4. Cross-check consequential claims against independent sources and distinguish evidence from inference.
5. Track contradictions, missing data, selection bias and source incentives.
6. Summarise the evidence proportionally; preserve uncertainty and identify what would change the conclusion.

## Output contract
Deliver an executive conclusion, evidence table, cited claims, contradictions, confidence, limitations and next verification steps.

## Verification
Every non-trivial external factual claim should be traceable to a source. A search snippet alone is weak evidence for nuanced claims; inspect the source where practical.

## Failure handling
If reliable evidence is unavailable or sources conflict, say so explicitly. Do not fabricate citations, dates, benchmarks or quotations.
