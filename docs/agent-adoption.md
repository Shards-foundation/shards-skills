# Shards Skills — agent adoption, not catalogue size

## Evidence levels

Record how far each host run actually got.

| Stage | Evidence |
| --- | --- |
| A. Discovered | The host's native listing contains the ID and path |
| B. Selected | The host trace identifies the skill chosen for the task |
| C. Instructions loaded | The trace shows the exact descriptor or bundle revision being opened |
| D. Procedure applied | Actions and artifacts show the relevant workflow steps |
| E. Outcome verified | An independent reviewer checks the artifact and the acceptance criteria |
| F. Improvement measured | Matched runs with and without the skill show a repeatable difference |

Existing [historical task evidence](first-party-skill-task-evidence.md) and
[external pilot feedback](host-ab-evaluation.md#first-external-host-pilot-14-november-2026)
record observations and self-reports. They motivate tests at later stages.

## Repeatable checks

From the repository root (Python 3.11+, no API key):

```bash
python scripts/agent_adoption_eval.py > /tmp/shards-retrieval.json
python -m unittest discover -s tests -p 'test_agent_adoption_eval.py' -v
```

The first command replays `evals/trigger-cases.json` against the metadata
finder. The 23 synthetic cases cover engineering, security, recovery, review
resolution and research. The report gives positive-case recall at ranks 1, 3
and 5, and how often a negative target still appears in the first three.

On this fixture set, the original mixed catalogue ranked 9 of 16 positive
targets first and 12 in the first three. With the same old ranker and the 60
original skills plus 13 curated workflows, these counts were 11 and 15.
The new ranking returned all 16 first and none of the seven negative targets
in its first three. The baseline is pinned to
[the pre-migration revision](https://github.com/Shards-foundation/shards-skills/tree/4f6f2376a403eb5ccfacbacf2adc1c7daa7a47bf).
These cases guided the ranking changes. Reserve unseen tasks for broader
validation. Retrieval scores measure shortlist quality on these fixtures.

## Real host acceptance protocol

Pin the skill and task revisions. Use fresh sessions on the same host and
model, with equivalent tool permissions and the same synthetic task text.
Keep the expected skill name out of the prompt. Use one condition with the
skill available and one without it. Include a negative task and repeat trials
to reduce the effect of run-to-run variance. On the negative task, check the host trace for abstention. Fail the case if the irrelevant or prohibited skill was selected or opened. Record an incomplete trace as unverified.

Record stages A–E from a redacted trace or an access-controlled reference.
An independent reviewer checks the acceptance criteria and compares supported
findings, task correctness, permission violations and actual test outcomes.
Record time and model tokens when measured comparably. Use the
[paired checker](host-ab-evaluation.md) to flag mismatched conditions and
compare the reported metrics. Keep raw prompts, credentials and proprietary
content out of fixtures and reports. Collect evidence only with operator
authorisation.

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

Promote a skill for a specific agent host only when its own positive and negative trigger cases pass, original tool traces support actual use, permissions remain bounded, and results are better than or at least no worse than a no-skill baseline. Keep untested host behaviours marked unverified. Improve or retire skills with persistent false triggers, execution failures, irrelevant output, or zero measured benefit. Re-run cases after changing metadata, ranking, source code, or host integration.

This gate complements the local dispatcher and the independent security checks. It does not authorize imports, deployments, trading, spending or publication.
