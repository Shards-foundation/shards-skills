# First-party skill discovery

Use the metadata finder to get a shortlist, then open the selected descriptor.
The finder runs locally with Python 3.11+ and uses the standard library.

```bash
python scripts/search_skills.py --query "Resume an interrupted GitHub PR repair and verify changes before merging" --limit 5
python scripts/search_skills.py --query "repository health" --status curated --limit 3
python scripts/search_skills.py --query "context recovery" --status candidate
python scripts/search_skills.py --skill shards-review-resolution
```

`--query` returns JSON with a score and a matching rationale. `--skill` reads
one exact descriptor and returns its path and Markdown as JSON. A successful
search can return zero matches. Invalid inputs or malformed metadata exit 2.

## How ranking works

Exact identifiers and specific multi-word task signals rank ahead of descriptions
with incidental shared terms. The finder gives uncommon terms more weight,
uses category as a small supporting signal, and counts each query word once
even when several inflections match. Each result reports the matched name
terms, description terms, discovery signals and category contribution.

Simple negative clauses and explicit per-skill exclusions suppress obvious
mismatches. Negation handling follows punctuation and common conjunctions.
Unusual syntax, synonyms absent from metadata and overlapping tasks still
need human or agent judgement. For example, an interrupted PR repair can also
rank authority preflight because both mention PR or merge work. Inspect the
reason and shortlist only the steps the task needs.

| Source | What it provides | Execution boundary |
| --- | --- | --- |
| `catalogue` | First-party instructions under `skills/` | The dispatcher cannot execute these entries |
| `curated` | Workflows in the Shards Core registry | Review a dispatcher plan and obtain host permission |
| `native` | Candidate variants in `.agents/skills/` | Use an exact candidate ID or `--status candidate` to include it in discovery. These skills are outside the dispatcher registry |

Search reads catalogue JSON and bounded host descriptor headers. Exact lookup
opens a single named local descriptor. Neither command installs skills, runs
skill code or reaches the network. A review status describes local evidence.
Verify host discovery, applicability and permissions separately.

## GitHub-hosted search

In **Actions → Search Shards Skill Catalogue**, select **Run workflow**, enter
ordinary task terms, and optionally choose category, status and result limit.
The summary links to the exact-revision descriptors. GitHub retains the JSON
results artifact for seven days. Use the separate [curated workflow action](manual-skill-runs.md)
for approved repository checks.

## Check retrieval

```bash
python scripts/agent_adoption_eval.py
python -m unittest discover -s tests -p 'test_skill_search.py' -v
```

See the [evaluation protocol](agent-adoption.md) for fixture results, limitations
and the evidence needed to establish actual use.
