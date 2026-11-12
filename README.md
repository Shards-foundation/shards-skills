# Shards Skills

**A security-aware, cross-agent skills library for engineering, research, design, security, data, AI agents, blockchain, and operations.**

> Status: curated mega-library release candidate. Shards-authored and imported packages are clearly separated by provenance and review status; third-party content is not silently treated as first-party.

## Goals

- Reusable skills with consistent metadata and concrete verification steps.
- Portable `SKILL.md` structure where possible, with explicit platform-specific notes when not.
- Security-first ingestion: provenance, licensing, static checks, review, and test evidence.
- Progressive disclosure: concise entry instructions, deeper references and scripts loaded only when needed.
- Measurable quality: schema checks, safety checks, smoke tests, and skill-specific evals.

## Quick start

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
```

No third-party Python dependencies are required for the baseline checks. Python 3.11+ is recommended.

## Layout

```text
skills/                 First-party skill packages (SKILL.md + optional references/scripts)
catalogue/              Machine-readable catalogue and upstream source register
schemas/                Metadata schema and policy definitions
scripts/                Validation, security lint and catalogue utilities
tests/                  Unit and repository integrity tests
evals/                  Repeatable skill-quality evaluation cases
.github/workflows/      CI, security and contribution automation
```

## Current first-party skill families

- Engineering: problem framing, planning, TDD, debugging, code review, release readiness.
- Security: threat modelling, secure code review, skill supply-chain review, incident triage.
- Research: source-grounded research and evidence synthesis.
- Agent systems: agent architecture, tool contracts, evaluation and orchestration.
- Data: reproducible data analysis and dataset quality.
- Product/design: interface critique and accessibility review.
- Blockchain: smart-contract review and protocol risk analysis.
- Operations: runbooks and post-incident learning.

## Security model

Skills are executable influence: their instructions can direct agents to use tools, inspect secrets, run commands or transmit data. Treat every imported skill as untrusted until reviewed. Static scanning is a signal, not a proof of safety. Do not run scripts from a newly imported skill in CI or on a developer machine before review.

The baseline scanner flags high-risk instruction patterns and unsafe script characteristics. It does not claim to detect every prompt injection, exploit, or exfiltration path. Human review and sandboxed behavioural tests remain required for imported skills.

## Importing third-party skills

1. Record the upstream URL, exact commit/tag, retrieval date, upstream owner, declared licence and local modifications in `catalogue/upstreams.json`.
2. Inspect the repository's licence and any per-directory/file notices. Do not infer a licence from a public GitHub URL.
3. Prefer linking or a documented install adapter when redistribution rights are unclear.
4. Preserve required copyright notices and attribution for permitted copies.
5. Run static checks, inspect every script/reference, and test the skill in a disposable sandbox with no secrets and restricted network access.
6. Add provenance and test evidence before marking a skill `verified`.

## Quality gates

A skill is not `verified` merely because its Markdown parses. It should pass metadata validation, policy lint, task-specific evaluations, compatibility checks and a reviewer checklist. The status vocabulary is `draft`, `review`, `verified`, `deprecated`.

## Runtime compatibility

See [`docs/compatibility.md`](docs/compatibility.md) for manual installation, CLI notes, and the evidence required before claiming a runtime is supported.

## Contribution contract

- One skill per directory; directory names are lowercase kebab-case.
- Every skill has a `SKILL.md` with YAML frontmatter including `name` and `description`.
- State triggers, prerequisites, workflow, output contract, failure handling and verification.
- Keep instructions task-focused; put long references in `references/`.
- No embedded credentials, opaque binaries, unexplained network calls, destructive commands, or claims of verification without evidence.
- Update tests/evals when behaviour changes.

## Upstream inspirations

See [`catalogue/upstreams.json`](catalogue/upstreams.json) for the user-supplied sources and the intended integration approach. This project is an independent collection and integration layer; it is not affiliated with those upstream projects unless explicitly stated.

## Licence

Original first-party content is licensed under MIT unless a file states otherwise. Third-party materials, when later added, retain their own licence and attribution requirements; see `THIRD_PARTY_NOTICES.md`.

## Curated mega-library

The bootstrap collection has been expanded into a curated catalogue of **304 skill packages** across agents, engineering, security, research, science, design, data, blockchain and operations. The imported packages come from 14 upstream repositories selected from the larger source set documented in [`catalogue/upstreams.json`](catalogue/upstreams.json).

Imported packages are not silently treated as first-party. Each one is marked `review`, includes its immutable upstream commit and original path in frontmatter, and contains an `UPSTREAM.md` record. Package-level provenance is indexed in [`catalogue/imported-skills.json`](catalogue/imported-skills.json), with preserved source notices under [`third_party/`](third_party/).

The selection deliberately excludes whole application frameworks, mutable installers, licensing-ambiguous packages, unreviewed hooks, credential automation, and offensive-security dumps. See the [catalogue guide](docs/catalogue-guide.md) for lifecycle, selection, and safety rules.

Run the complete local gate with:

```bash
python scripts/build_catalogue.py
python scripts/validate_skills.py
python scripts/security_lint.py
python -m unittest discover -s tests -v
```


## Agent operating contract and runnable core plugin

Agents should start with [AGENTS.md](AGENTS.md) and [agent.md](agent.md). The curated, installable [Shards Agent Core plugin](plugins/shards-core/README.md) provides four runnable local workflows for repository health, skill auditing, release-gate evidence and structured handoffs. Installations are opt-in via the [local plugin marketplace](.agents/plugins/marketplace.json). Existing imported catalogue skills are **not** automatically trusted, executed or bundled into the curated plugin. See [runtime compatibility](docs/agent-runtime.md).

## Automated skill maintenance

Use the [automation operations guide](docs/automation.md) to plan and run bounded maintenance workflows, generate skill-portfolio reports, and explicitly reconcile catalogue metadata. A GitHub Actions audit runs every Monday at 05:17 UTC and retains JSON/Markdown artifacts for 14 days. Imported skill scripts are never auto-executed; catalogue write mode is deliberately excluded from unattended schedules.

## Governed skill execution
The eleven curated plugin skills are exposed through a bounded, JSON-reporting dispatcher. Use scripts/dispatch_skills.py list and plan first, then explicitly run approved read-only or scoped local workflows. Details: [Governed skill execution](docs/skill-dispatch.md). Imported catalogue skills are not executable by discovery alone.

## Deterministic skill discovery

Use the [metadata-only skill finder](docs/skill-discovery.md) to locate relevant
packages without loading or executing third-party skill code:

```bash
python scripts/search_skills.py --query "code review" --limit 10
python scripts/search_skills.py --query "repository health" --status curated
python scripts/search_skills.py --query "blockchain" --category blockchain
```

The JSON response distinguishes catalogue-only skill descriptions from curated
dispatcher allowlist entries. Search results are **not** execution permissions.

## One-click curated skill checks

Repo collaborators can run approved, read-only Shards workflows directly
from the GitHub **Actions → Run Curated Shards Skill** page without a local
Python environment. Choose repository health, catalogue consistency, or
plugin/dispatcher integrity; each run produces a JSON plan, a pinned
execution receipt, and a downloadable evidence artifact. This cannot execute
third-party imported skills or deploy anything.

See the [manual Actions runner guide](docs/manual-skill-runs.md).

## Search skills from GitHub

Use **Actions → Search Shards Skill Catalogue** to search the repository's
metadata catalogue remotely, filter by category/status and open ranked
`SKILL.md` links. The workflow is manually triggered, read-only and emits
a downloadable JSON results artifact; no imported skill code runs.

See the [skill discovery guide](docs/skill-discovery.md).


## Dual-channel, sub-agent and parallel swarm skills

Four runnable curated skills now use the local [Shards multi-agent harness](docs/agent-harness.md):
shards-a2a-harness, shards-dual-channel, shards-subagents and
shards-parallel-swarm. They delegate real, allowlisted read-only checks with
stable sub-agent IDs, separate control/data results, bounded concurrency,
and JSON receipts.

~~~bash
python scripts/shards_agent_harness.py plan --profile swarm
python scripts/shards_agent_harness.py run --profile swarm --execute --save-receipt
~~~

These are useful local orchestration primitives. They do not yet implement
the network Agent2Agent protocol or spawn independent AI models.


## Day Trader skills

All eleven skills from [Jake Schincariol's Day Trader pack](https://github.com/Jakeschincariol/day-trader-skill)
are included with their Python tools, example configurations and MIT attribution.

| Skill | Purpose |
| --- | --- |
| [trader-scanner](skills/trader-scanner/SKILL.md) | Chart and opening-range scans |
| [trader-news](skills/trader-news/SKILL.md) | Watchlist headlines and SEC filings |
| [trader-entry](skills/trader-entry/SKILL.md) | Bar-based entry signals |
| [trader-exit](skills/trader-exit/SKILL.md) | Stop, target and exit plans |
| [trader-timemachine](skills/trader-timemachine/SKILL.md) | Historical replay and Monte Carlo simulation |
| [trader-budget](skills/trader-budget/SKILL.md) | Position sizing |
| [trader-risk](skills/trader-risk/SKILL.md) | Order and daily risk checks |
| [trader-broker](skills/trader-broker/SKILL.md) | Approval-gated order tickets and decision logs |
| [trader-alerts](skills/trader-alerts/SKILL.md) | Price, stop, target and session alerts |
| [trader-analyst](skills/trader-analyst/SKILL.md) | Earnings and SEC financial analysis |
| [trader-pelosi](skills/trader-pelosi/SKILL.md) | Public congressional trade disclosures |

Find them with `python scripts/search_skills.py --query "trader" --category finance --limit 20`.
See the [import and usage notes](docs/day-trader-skills.md) for provenance,
paths, prerequisites and verification scope. They are review-stage catalogue
packages, not part of the executable Shards Core dispatcher. Importing the pack
does not connect a broker or start monitoring. Paper trading is the example default.

Two known upstream risk defects block use for trade approval until corrected;
see the [open findings](docs/day-trader-skills.md#open-upstream-findings).


## Evidence-gated skill improvement (experimental)

The first-party [shards-skill-improver](skills/shards-skill-improver/SKILL.md) creates
a hash-pinned, reviewable proposed change to a single first-party skill, requires
operator-supplied baseline/candidate evaluation evidence, and writes a local
backup before an explicitly authorised apply. It does **not** independently
produce eval results, run third-party scripts, modify remote repositories,
auto-merge PRs or grant execution privileges.

```bash
python scripts/skill_improver.py plan --target skills/release-readiness/SKILL.md --candidate candidate.md --output change-plan.json
# Run fixed baseline and candidate evaluations; prepare eval.json from real results.
python scripts/skill_improver.py apply --plan change-plan.json --candidate candidate.md --eval eval.json --approve --expect-plan-sha256 <reviewed-plan-sha256>
# Rollback requires the exact recorded backup and after_sha256:
python scripts/skill_improver.py rollback --target skills/release-readiness/SKILL.md --backup <recorded-backup-path> --expect-current-sha256 <after_sha256> --approve
```

Apply and rollback operate on the local checkout only. The eval receipt is not
cryptographically authenticated and must be reviewed against independently
recorded test artifacts. The host remains responsible for authorization,
GitHub branch protection, permissions and independent approval.


## Ten operating skills: complete work without losing context

The [operating-loop guide](docs/operating-loop.md) links ten Shards-authored,
draft skills: task contract, context recovery, tool selection, progress control,
evidence verification, review resolution, learning capture, skill evaluation,
controlled skill updates and host compatibility. It includes an append-only,
hash-chained **local task ledger** for durable criteria, attempts and evidence,
plus a testable interrupted-agent handoff scenario. This local tool does not
independently authenticate external observations or connect ChatGPT/Claude.

```bash
python scripts/operating_ledger.py --help
python -m unittest discover -s tests -p 'test_operating_ledger.py' -v
python -m unittest discover -s tests -p 'test_skill_improver.py' -v
```
