# First-party Shards-Skills: applied-task evidence

**Date:** 2026-11-12 (Europe/London)  
**Repository:** [Shards-foundation/shards-skills](https://github.com/Shards-foundation/shards-skills)  
**PR:** [#21](https://github.com/Shards-foundation/shards-skills/pull/21)  
**Scope:** One actual skill-routing defect; three original Shards-authored skills. No imported skill procedures, brokerage tools or paid external agents were executed.

## User-visible task and success criteria

> Import the day-trading skill files into the catalogue; do not connect a broker or place orders.

The actual original catalogue has 329 indexed entries, of which 44 are original Shards Foundation drafts. Imported skills remain metadata-only and **not dispatchable**.

Acceptance: a search returning up to ten matches must **not recommend** `trader-broker` for this import request; negative-only requests return no skills; a positive request for a broker still retrieves its metadata without executing it; existing CI remains green.

## Original skill 1: `systematic-debugging`

[Source](../skills/systematic-debugging/SKILL.md). Its procedure requires a reproducible fault, competing explanations, narrow repair and evidence of the original behaviour.

- **Observed baseline:** `scripts/search_skills.py` ranked `trader-broker` first for the user's explicit no-broker request. Negation tokens are removed as stopwords, while `broker` and `orders` counted as positive relevance. This is a **routing/recommendation error**, not an executed trade.
- **Reproduction:** Before implementation changes, committed four focused tests. GitHub [Agent Core Plugin Gates #122](https://github.com/Shards-foundation/shards-skills/actions/runs/43311795187) at `a3be17dd7e5fa339a5001598505c1e390ab00f6c` ran 182 tests: **3 deliberate regression failures** and the positive broker-request control passed.
- **Root-cause confidence:** High for the observed lexical-match failure, because the ranking source and pre-fix tests agree.
- **Outcome:** A narrow negative-clause exclusion during ranking. Catalogue trust/execution semantics were unchanged.

**Judgement:** Useful as a repeatable debugging procedure for this task. No causal benefit compared with an independently run, uninstructed model has been demonstrated.

## Original skill 2: `test-driven-development`

[Source](../skills/test-driven-development/SKILL.md). The applicable steps were writing tests before implementation, seeing the expected failures, applying the narrowest code change, and rerunning focused and repository-wide checks.

Four focused cases in `tests/test_skill_search.py`:

| Case | Pre-fix | Final corrected logic |
| --- | --- | --- |
| Import skills while expressly forbidding broker actions | FAIL: broker first | PASS: broker outside top-ten shortlist |
| Only a prohibition, with no affirmative task | FAIL: returned candidates | PASS: no matches |
| A legitimate request to connect a broker and place approved orders | PASS: metadata is retrievable, not dispatchable | PASS: preserved |
| Prohibited broker action followed by affirmative third-party skill audit | FAIL: wrong skill first | PASS: audit skill first |

The implementation strips bounded **explicit negative clauses** only from query relevance scoring. It does not edit descriptions, metadata or the allowlisted execution registry. It is a lexical heuristic, not a comprehensive semantic intent model.

**Observed evidence:** [Agent Core Plugin Gates #125](https://github.com/Shards-foundation/shards-skills/actions/runs/43312209442), commit `16933ea4c6ae4d7207cead4cf274243fd0d172b8`: **182 tests, OK**. [Agent Skill Adoption Evidence #21](https://github.com/Shards-foundation/shards-skills/actions/runs/43312209565): **10 tests, OK**, and the governed first-party repository-health skill smoke executed successfully.

**Judgement:** Real red-to-green regression evidence. The gain is on the code/task outcome; an AI-versus-AI no-skill control was not run.

## Original skill 3: `code-review`

[Source](../skills/code-review/SKILL.md). Reviewed the diff and relevant downstream call path from query to ranked output, prioritising concrete correctness/safety risks and negative cases.

1. **Positive intent:** `trader-broker` remains discoverable when explicitly requested; its `execution: not-dispatchable` flag remains unchanged.
2. **Negative intent:** `don't`, `do not`, `never`, and `without` clauses are excluded from relevance scoring, bounded by punctuation. A negative-only request produces no recommendation.
3. **Trust boundary:** This change is metadata-only; it does not launch scripts, connect external accounts, trade, or infer execution authority from a descriptor.
4. **Critical distinction discovered in verification:** broad lexical ranking still contains some weakly related results, including `trader-broker`, far below the user-facing shortlist. The relevant acceptance criterion is no prohibited skill **in the top-ten recommendations**, not an impossibly broad claim of no token overlap anywhere.
5. **Residual limitations:** quoted negation, nested clauses and long/implicit prohibitions are not fully understood by regex; positive intent, negative intent and relevance are not guaranteed to be semantically correct. Shards-authored skills can still rank behind imported catalogue entries.

**Judgement:** The code-review procedure identified a real over-broad assertion in the first test, prevented an unsupported blanket safety claim, and retained regression coverage. No independent reviewer or blinded A/B control evaluated the procedure's incremental benefit.

## Current status and strict interpretation

| Evidence gate | Result |
| --- | --- |
| Real checkout baseline failure | **Reproduced in GitHub Actions** |
| Fix applied in same PR | **Yes** |
| Regression testing | **4 focused scenarios pass** |
| Full unit suite at tested code head | **182/182 pass** |
| Existing adoption smoke (local CI host) | **PASS** |
| External host autonomously choosing original skills | **NOT TESTED** |
| Blinded no-skill vs skill A/B comparison | **NOT TESTED** |
| Improved ranking for every possible request | **NOT CLAIMED** |
| Independent production/security certification | **NOT CLAIMED** |

**What this proves:** Original Shards Foundation skills were deliberately read and their instructions were followed on a real repository task, resulting in a reproducible, correctly bounded code change and passing automated verification. This verifies **one applied workflow**, not the usefulness of all 44 first-party skills or causal improvement over an AI that never saw their instructions.

**Future re-review triggers:** ranking algorithm changes, new negation patterns, a change to catalogue status/dispatch trust classes, or measured false activations on real host traces.

**Cost and scope:** One existing repository, one PR (#21), standard GitHub CI; no paid reviewer credits and no third-party execution.