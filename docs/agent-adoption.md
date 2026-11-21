# Shards Skills — agent adoption, not catalogue size

## Objective

An agent should **independently choose** a relevant, safe skill when solving an actual task, read its instructions, apply its workflow, and produce an inspectable improvement. A search result is not adoption. A `SKILL.md` file is not execution. A passing repository test is not proof that Claude, Codex, Cursor, or ChatGPT has installed or used that skill.

## Repeatable checks

From the repository root (Python 3.11+, no API key):

```bash
python scripts/agent_adoption_eval.py > /tmp/shards-retrieval.json
python -m unittest discover -s tests -p 'test_agent_adoption_eval.py' -v
```

The first command replays `evals/trigger-cases.json` against the current catalogue search ranking. It reports positive-case recall@1/3/5 and each target rank. Negative cases are **not** counted as passed: lexical retrieval cannot decide whether an agent should invoke a skill. The source commit must be recorded independently when sharing results.

## Real host acceptance protocol

Test each target host separately, on a pinned Shards Skills revision. Use a fresh workspace/session without mentioning the expected skill name to the agent. Give the host repository access and the same actual task, with permission to inspect skills but not to perform unapproved external writes. Preserve the entire host tool trace, the selected skill path and revision, commands actually invoked, outputs, and task-level pass/fail evidence.

For every positive case, require: skill discovered without prompting, `SKILL.md` opened, relevant procedure followed, task-level outcome observed, and linked original trace. For every negative case, require that the agent did not invoke the prohibited/irrelevant skill. Include a no-skill baseline for each task: compare actual defects fixed, tests, elapsed effort, unsupported claims and security regressions. Do not substitute a model-generated confidence rating for the measured delta.

A tool-trace summary may be checked with:

```bash
python scripts/agent_adoption_eval.py --receipts ./host-receipts.json
```

The receipt format is:

```json
{
  "schema_version": 1,
  "host": "Claude Code version x.y",
  "repository_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "runs": [
    {
      "case_id": "1",
      "selected_skill": "test-driven-development",
      "skill_opened": true,
      "procedure_applied": true,
      "trace_reference": "path-or-url-to-original-host-log",
      "task_outcome": "pass"
    }
  ]
}
```

This validator labels results **self-reported**. It does not dereference logs, authenticate the host, validate external effects, or prove utility. Missing case results remain `not_run`. Do not claim an independently verified agent adoption test unless the original host traces and task outcomes are inspected.

## Release gates

Promote a skill for a specific agent host only when its own positive and negative trigger cases pass, original tool traces support actual use, permissions remain bounded, and results are better than or at least no worse than a no-skill baseline. Keep unsupported hosts and imported packages in review. Improve or retire skills with persistent false triggers, execution failures, irrelevant output, or zero measured benefit. Re-run cases after changing metadata, ranking, source code, or host integration.

This gate complements the local dispatcher and the independent security checks. It does not authorize imports, deployments, trading, spending or publication.
