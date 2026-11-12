# Shards Skills

**A security-aware, cross-agent skills library for engineering, research, design, security, data, AI agents, blockchain, and operations.**

> **Usable now:** First-party skills are written procedures that an agent can read and apply immediately. The `draft` metadata records the limits of independent host-level evaluation; it does **not** disable use. The Python preflight and assurance tools run locally. Imported skills remain separate and subject to their own provenance reviews.

## Get a useful result — no paid AI credits required

This repository has **two distinct capabilities**: instructions for agents (the
`skills/` catalogue) and **eleven curated workflows with executable entrypoints**
under `plugins/shards-core/`. Finding an imported skill does not authorise
running its scripts. The list of catalogue skills is not a count of tested agents.

From a local checkout with Python 3.11+:

```bash
# 1. Discover a candidate for an actual task (does not run imported code).
python scripts/search_skills.py --query "check repository health" --status curated --limit 3

# 2. Run a useful read-only check on a Git repository you own.
python plugins/shards-core/scripts/run.py repository-health --repo /path/to/your/project

# 3. Measure whether natural-language tasks retrieve relevant skills.
python scripts/agent_adoption_eval.py
```

For an Android-only operator with no local Python, the existing
[Run Curated Shards Skill](docs/manual-skill-runs.md) GitHub Action runs reviewed
read-only checks and provides JSON receipts. To see skill matches rather than
run one, use [Search Shards Skill Catalogue](docs/skill-discovery.md).

To use an **instruction-only** skill with an agent, provide its
`skills/<name>/SKILL.md` and the project task. The agent must actually read it
and produce task evidence; simply listing or selecting a skill is not
proof of execution. [Agent adoption evidence](docs/agent-adoption.md) records
the retrieval and host-verification boundaries.

## Use Shards Security Skills now

**No certification or special agent integration is required to start using the workflows.**
For any ChatGPT or Claude session that can read this repository, give the agent the specific `SKILL.md` file and your owned project context. Example:

> Read [shards-sec-vibecoding-gate](skills/shards-sec-vibecoding-gate/SKILL.md) and apply its workflow to my authorised web-app repository. Show actual findings, missing evidence and next changes. Don't claim tests ran unless you executed them.

If your agent cannot open GitHub, paste or upload the individual `SKILL.md` file. A skill describes **how** to perform work; it is not executable code and does not require a privileged dispatcher entry.

For hands-on local checks on a repository you own, run these commands in a terminal:

```bash
git clone https://github.com/Shards-foundation/shards-skills.git
cd shards-skills

# Select an assessment checklist appropriate for your app:
python scripts/security_assurance.py plan --system "My application" --profiles web,ai

# Inspect your OWN local code for selected risky patterns without running the app:
python scripts/vibecode_guard.py --repo /path/to/your/app
```

The `plan` command returns controls to investigate, not results. The local guard uses
**0 = no configured patterns found**, **1 = warnings found**, and **2 = blocked input**.
A clean run is not an automatic security sign-off. For observed evidence and a
reproducible assessment, follow [the evidence and assessment walkthrough](docs/security-assurance.md).

**What is ready today:** 25 structured security workflows, 45 reference controls,
an offline planning/evidence CLI and a bounded local preflight, all committed to
`main`. **What is not claimed:** automatic full-stack scanning, independently
validated performance on every agent host, regulatory certification, or a
guarantee that an application has no vulnerabilities. Those are separate
properties, not prerequisites to reading and applying the skills.

## Shards Foundation first-party skills

**Shards-authored workflows, not imported prompt packs.** Our first-party skills are intended to help humans and AI agents do verifiable work with less ambiguity. Each one has a defined trigger, ordered procedure, output requirements, evidence expectations and stop conditions. **Draft** means documented and under test; it is not production certification or an endorsement by NIST, OWASP or a regulator.

**Start here if you are vibe-coding:** [Secure AI-built applications](skills/shards-sec-vibecoding-gate/SKILL.md) · [Security intake](skills/shards-sec-intake/SKILL.md) · [Identity and access](skills/shards-sec-identity-access/SKILL.md) · [API assurance](skills/shards-sec-web-api/SKILL.md) · [Privacy screening](skills/shards-sec-privacy-dpia/SKILL.md). Generate a read-only checklist with:

```bash
python scripts/security_assurance.py list
python scripts/security_assurance.py plan --system "My application" --profiles web,ai
```

For beginners with their own Git checkout, the **read-only local preflight** flags a small set of dangerous coding patterns without running the application or printing secret values:

```bash
python scripts/vibecode_guard.py --repo .
```

A clean heuristic result is **not** a security audit. [Preflight limitations and workflow](docs/security-assurance.md).

The offline [assurance CLI](scripts/security_assurance.py) draws from [45 versioned Shards controls](catalogue/shards-security-controls.json) spanning eight profiles. It does **not** automatically test a running app or certify security. See the [operator guide](docs/security-assurance.md) and [source/version register](docs/security-frameworks.md).

### Shards Security & Governance Suite — 25 first-party workflows

| Domain | Shards skill | What an agent produces |
| --- | --- | --- |
| Scope | [shards-sec-intake](skills/shards-sec-intake/SKILL.md) | Authorised boundary, asset owner and explicit stop conditions |
| Vibe coding | [shards-sec-vibecoding-gate](skills/shards-sec-vibecoding-gate/SKILL.md) | Secure-build checklist, negative tests, fail-closed release recommendation |
| Enterprise | [shards-sec-business-threat-model](skills/shards-sec-business-threat-model/SKILL.md) | Risk-ranked business threat model and control owners |
| Identity | [shards-sec-identity-access](skills/shards-sec-identity-access/SKILL.md) | Role/access matrix and cross-tenant denial tests |
| Keys | [shards-sec-secrets-keys](skills/shards-sec-secrets-keys/SKILL.md) | Secret lifecycle and redacted rotation evidence |
| AppSec | [shards-sec-web-api](skills/shards-sec-web-api/SKILL.md) | API, session, webhook and multi-tenant assurance |
| Cloud | [shards-sec-cloud-devsecops](skills/shards-sec-cloud-devsecops/SKILL.md) | Least-privilege cloud and CI review |
| Supply chain | [shards-sec-supply-chain](skills/shards-sec-supply-chain/SKILL.md) | Dependency provenance and SBOM review |
| Vulnerabilities | [shards-sec-vulnerability-management](skills/shards-sec-vulnerability-management/SKILL.md) | Exploitability-informed remediation and regression evidence |
| Response | [shards-sec-incident-response](skills/shards-sec-incident-response/SKILL.md) | Evidence-preserving incident and recovery plan |
| Detection | [shards-sec-detection-response](skills/shards-sec-detection-response/SKILL.md) | Event coverage, alert drill and responder ownership |
| Human safety | [shards-sec-human-fraud](skills/shards-sec-human-fraud/SKILL.md) | Phishing, AI-impersonation and payment-fraud defence |
| Privacy | [shards-sec-privacy-dpia](skills/shards-sec-privacy-dpia/SKILL.md) | Data-flow and DPIA screening record |
| Governance | [shards-sec-governance-policy](skills/shards-sec-governance-policy/SKILL.md) | Policy lifecycle, approval and exception controls |
| Jurisdictions | [shards-sec-jurisdiction-scope](skills/shards-sec-jurisdiction-scope/SKILL.md) | Jurisdiction/applicability research matrix for legal review |
| Compliance | [shards-sec-compliance-evidence](skills/shards-sec-compliance-evidence/SKILL.md) | Control-to-evidence register with explicit gaps |
| Vendors | [shards-sec-third-party-risk](skills/shards-sec-third-party-risk/SKILL.md) | Supplier assurance, exit and concentration risks |
| Resilience | [shards-sec-resilience-recovery](skills/shards-sec-resilience-recovery/SKILL.md) | Business continuity and measured restore evidence |
| Fintech | [shards-sec-fintech-payments](skills/shards-sec-fintech-payments/SKILL.md) | Funds-flow, transaction authorisation and reconciliation checks |
| Crypto | [shards-sec-crypto-custody](skills/shards-sec-crypto-custody/SKILL.md) | Wallet custody, signing and recovery gates |
| Blockchain | [shards-sec-defi-protocol](skills/shards-sec-defi-protocol/SKILL.md) | Smart contract, oracle, bridge and DeFi risk evidence |
| Agents | [shards-sec-ai-agent-boundaries](skills/shards-sec-ai-agent-boundaries/SKILL.md) | Tool permissions, external enforcement and agent identity checks |
| Jailbreaks | [shards-sec-prompt-injection](skills/shards-sec-prompt-injection/SKILL.md) | Prompt-injection and data-poisoning regression tests |
| Ethical testing | [shards-sec-authorized-testing](skills/shards-sec-authorized-testing/SKILL.md) | Scoped defensive rules of engagement and findings |
| Crypto compliance | [shards-sec-crypto-fincrime](skills/shards-sec-crypto-fincrime/SKILL.md) | FATF/VASP/AML applicability issues and review ownership |

### Existing curated Shards Core skills — eleven runnable local workflows

| Purpose | Curated skill |
| --- | --- |
| Repository health | `shards-repository-health` |
| First-party and imported skill assessment | `shards-skill-audit` |
| Release evidence gate | `shards-release-gate` |
| Agent handoff | `shards-agent-handoff` |
| Safe automated maintenance | `shards-automation-operator` |
| Catalogue reconciliation | `shards-catalogue-sync` |
| Reviewed dispatch and receipts | `shards-skill-dispatch` |
| Local A2A-oriented checks | `shards-a2a-harness` |
| Control/data channel separation | `shards-dual-channel` |
| Bounded delegated sub-agent checks | `shards-subagents` |
| Read-only concurrent swarm | `shards-parallel-swarm` |

These live in `plugins/shards-core/skills/`, not `skills/shards-sec-*/`. They use the [governed dispatcher](docs/skill-dispatch.md); the new security suite is **not** automatically granted dispatcher execution. Agent prompts do not substitute for host permission enforcement.

### Existing Shards-authored foundation skills

[problem-framing](skills/problem-framing/SKILL.md) · [implementation-planning](skills/implementation-planning/SKILL.md) · [systematic-debugging](skills/systematic-debugging/SKILL.md) · [test-driven-development](skills/test-driven-development/SKILL.md) · [code-review](skills/code-review/SKILL.md) · [secure-code-review](skills/secure-code-review/SKILL.md) · [threat-modeling](skills/threat-modeling/SKILL.md) · [skill-supply-chain-audit](skills/skill-supply-chain-audit/SKILL.md) · [smart-contract-review](skills/smart-contract-review/SKILL.md) · [release-readiness](skills/release-readiness/SKILL.md) · [incident-runbook](skills/incident-runbook/SKILL.md) · [agent-system-design](skills/agent-system-design/SKILL.md) · [tool-contract-design](skills/tool-contract-design/SKILL.md) · [evidence-based-research](skills/evidence-based-research/SKILL.md) · [reproducible-data-analysis](skills/reproducible-data-analysis/SKILL.md) · [frontend-accessibility-review](skills/frontend-accessibility-review/SKILL.md) · [web-application-testing](skills/web-application-testing/SKILL.md) · [writing-skill-packages](skills/writing-skill-packages/SKILL.md).

**Separate pending work:** the ten operating-loop skills (task contract, context recovery, tool selection, progress control, evidence verification, review resolution, learning capture, skill evaluation, controlled updates and host compatibility) are in [PR #16](https://github.com/Shards-foundation/shards-skills/pull/16), not yet merged into `main`. They are **not** represented as installed or available on the main branch. The security suite is already merged into `main`; the ten operating-loop skills remain a separate pending change.

Third-party packages retain their own licences and their review-stage status. Discovery is not authorisation. For current counts, use `catalogue/catalogue.json`; any examples and totals on a branch describe that branch only.

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

The bootstrap collection has been expanded into a curated catalogue of **329 skill packages** across agents, engineering, security, research, science, design, data, blockchain and operations. The imported packages come from 14 upstream repositories selected from the larger source set documented in [`catalogue/upstreams.json`](catalogue/upstreams.json).

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
