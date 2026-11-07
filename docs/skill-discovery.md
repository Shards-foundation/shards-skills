# Metadata-only skill discovery

The catalogue contains hundreds of heterogeneous skills, including imported
review-stage packages. Finding one does **not** grant permission to execute it.

## CLI

From the repository root:

```bash
python scripts/search_skills.py --query "test driven development"
python scripts/search_skills.py --query "release gate" --status curated --limit 5
python scripts/search_skills.py --query "web research" --category research
```

The command emits JSON with candidate count, match count, ranked results,
descriptions, categories, status, relative descriptor paths, and the
execution boundary. Exit code 0 means a valid search, even with zero matches.
Invalid metadata, unsupported catalogue schema, traversal paths, duplicate
names, invalid query terms or limit values fail with exit code 2. Catalogue\nstatus values must be recognised strings; malformed JSON types (including\narrays and objects) are rejected as metadata errors, not Python tracebacks.

## Matching and trust

Matching is deterministic: token and exact-phrase overlap over catalogue name,
description and category. This is a lexical search, not an LLM judgement,
semantic retrieval service, skill certification or task-level evaluation.
Ranks are relevant candidates, not guarantees of suitability.

- `source=catalogue`, `execution=not-dispatchable`: a skill is listed only.
  Imported scripts are never executed or loaded for search.
- `source=curated`, `execution=dispatcher-plan-required`: a first-party
  skill is present in the explicit dispatcher registry. Review the
  `SKILL.md` and use `scripts/dispatch_skills.py plan` before any approved
  execution. The trusted host must independently authorise tool access.
- A metadata `status=verified` is not proof of platform compatibility or
  operational readiness. Recheck source revision and provenance before use.

Curated descriptors are parsed from their opening, bounded YAML frontmatter only.
A missing closing delimiter, duplicate name/description field, mismatched name,
or oversized header fails closed; text in the Markdown body cannot impersonate
search metadata. This is a narrow metadata boundary, not a full YAML parser.

The finder requires Python 3.11+, the full checkout and no third-party
dependencies. It reads a bounded JSON catalogue plus curated first-party
descriptors, makes no network calls and does not invoke a shell or subprocess.

## Verification

```bash
python -m unittest discover -s tests -p 'test_skill_search.py' -v
python scripts/search_skills.py --query "repository health" --status curated
python scripts/validate_skills.py
```

The Agent Core Plugin GitHub Actions workflow compiles and smoke-tests the
finder and runs the repository unit test suite on matching pull requests.

## Search directly from GitHub (no local Python)

Repository collaborators can open **Actions → Search Shards Skill Catalogue**
and select **Run workflow**. Enter ordinary task terms, choose optional
category/status filters, and select a result limit. The run's summary links to
matching checked-out `SKILL.md` descriptors at the exact commit. A JSON
results artifact is retained for **7 days**.

The workflow passes input as quoted, environment-bound CLI arguments rather
than evaluating it as shell commands. It requests only `contents: read`
permission and disables checkout credential persistence. Search results expose
metadata from imported or review-stage skills; the workflow never executes
those packages or automatically installs them. GitHub workflow permissions
govern who can dispatch the action.

For executable, first-party repository checks, use the separate
[Run Curated Shards Skill](manual-skill-runs.md) manual workflow.
