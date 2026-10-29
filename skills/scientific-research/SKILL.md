---
name: scientific-research
description: "Use for scientific or technical research that requires reproducible methods, source-quality appraisal, uncertainty handling and separation of evidence from interpretation."
license: MIT
compatibility: "Agent Skills-compatible runtimes; tool availability varies by host."
category: research
status: draft
version: 0.1.0
author: Shards Foundation
---

# Scientific Research

## Workflow
1. Define the research question, population/system, outcome, time range and inclusion/exclusion criteria.
2. Search primary literature, standards, datasets and official methods before relying on secondary summaries.
3. Capture bibliographic details, DOI or stable URL, publication date, study type and access limitations.
4. Assess study design, sample size, controls, confounding, measurement validity, statistical power and reproducibility.
5. Compare independent results and distinguish consensus, preliminary findings and unresolved disagreement.
6. Report effect sizes and uncertainty where available; avoid equating statistical significance with practical importance.
7. Record search methods and gaps so another researcher can reproduce the evidence review.

## Output contract
Provide the question, method, evidence table, synthesis, uncertainty, limitations, conflicts of interest where known and reproducibility notes.

## Verification
Trace each consequential claim to a source and verify that the source actually supports it. Do not invent DOIs, datasets or peer-review status.

## Failure handling
If evidence is low quality, inaccessible or contradictory, lower confidence and explain what further evidence would resolve the issue.
