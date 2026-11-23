<p align="center">
  <img src="assets/shards-skills-banner.webp" alt="Shards Skills — faceted silver S with violet accents" width="800">
</p>

# Shards Skills

Shards Skills is an independently developed library of workflows for AI-assisted engineering, security, research and operations. It contains 60 catalogue skills, 13 curated Shards Core workflows, and four separate native host candidates.

## Three ways to use this repository

| Guide | Use it when |
| --- | --- |
| 📖 [Cookbook](docs/cookbook.md) | You want a copyable, scoped example for a real task |
| 🧭 [Playbook](docs/playbook.md) | You need a repeatable sequence, gates and recovery steps |
| 🛡️ [Rulebook](docs/rulebook.md) | You need permission boundaries, evidence standards and stop conditions |
| ⚙️ [Machine-readable agent index](agent-index.yaml) | An agent needs task-to-skill routing without reading every descriptor |

The machine index is **YAML 1.2 in JSON-compatible syntax**. It can be read with a YAML parser *or* Python's standard-library JSON parser:

~~~bash
python -m json.tool agent-index.yaml > /dev/null
python -c 'import json; d=json.load(open("agent-index.yaml")); print([(r["id"], r["primary_skill"]) for r in d["routes"]])'
python -m unittest discover -s tests -p 'test_agent_index.py' -v
~~~

This index is a **navigation aid**, not an executable skill registry, tool permission or guarantee of host discovery. Agents should read [`AGENTS.md`](AGENTS.md), [`agent.md`](agent.md) and [`SECURITY.md`](SECURITY.md) first, then inspect only selected descriptors.

## Start here: a first-skill walkthrough

**Goal:** find an appropriate skill, inspect its instructions, make it available to an agent, and verify what the agent actually did. Skill files are *instructions*, not remotely connected tools or automatic permissions.

**Choose a route:** [Terminal walkthrough](#1-get-the-library) · [GitHub/mobile walkthrough](#github-and-mobile-no-local-setup) · [Skill directory](#find-the-right-skill) · [Full host guide](docs/portable-agent-skills.md).

### 1. Get the library

Use a trusted checkout. **Python 3.11+** is sufficient for searching and the local read-only demonstrations; **Node.js 22.20+** is only needed for the optional pinned Skills CLI installer.

```bash
git clone https://github.com/Shards-foundation/shards-skills.git
cd shards-skills
python --version
```

For reproducible work, record the Git revision (for example, with `git rev-parse HEAD`) before copying skills into another project. Review unfamiliar files before running repository scripts.

### 2. Describe your task, then discover the skill

Example: you want an agent to review a pull request without merging it.

```bash
python scripts/search_skills.py --query "Review a GitHub PR, verify evidence and report blockers without merging" --limit 5
python scripts/search_skills.py --skill shards-review-resolution
```

The first command returns a **ranked JSON shortlist and match rationale**; the second returns one exact skill descriptor. Open the indicated `skills/<name>/SKILL.md` and check its prerequisites, inputs, boundaries, expected output and failure handling. Search does **not** install or execute a skill. A search hit does not establish that the skill is useful for your task.

### 3. Install only what the agent needs

In the **destination project** where you use Codex, point the pinned Skills CLI at your trusted Shards Skills checkout:

```bash
npx skills@1.8.1 add /path/to/shards-skills --skill code-review shards-review-resolution shards-evidence-verification -a codex --copy -y
npx skills@1.8.1 list
```

Replace `/path/to/shards-skills` with the real checkout path. The initial `npx` invocation downloads the specified installer version; inspect and trust the installer before using it. For Claude Code, OpenHands, Cursor, OpenCode and other clients, use the [host-by-host installation guide](docs/portable-agent-skills.md); an installer target is **not** proof of real agent invocation.

### 4. Give the agent a bounded test task

Try this example request in a host that actually discovers the installed skills:

> Review the current pull request using the available code-review and evidence-verification skills. Inspect the changed files, identify regressions and security concerns, and distinguish tests actually run from unverified claims. Return APPROVE, REQUEST CHANGES or BLOCKED, with supporting evidence. Do not modify files, merge, deploy or publish.

This is a **sample prompt**, not a claim that an agent has been tested here. Check the host's own skill list and trace: **discovered → selected → instructions opened → procedure applied → outcome independently checked**. If any step lacks evidence, record it as *unverified*. See [agent adoption and evaluation](docs/agent-adoption.md).

### 5. Try a governed, local Shards Core workflow

Catalogue skills and curated executable workflows are separate. The latter can be planned through a reviewed local dispatcher:

```bash
python scripts/dispatch_skills.py list
python scripts/dispatch_skills.py plan --skill shards-repository-health
```

The plan is read-only. To execute **only after reviewing the plan and confirming host permission**, use its actual `plan_sha256`:

```bash
python scripts/dispatch_skills.py run --skill shards-repository-health --execute --expect-plan-sha256 <digest-from-reviewed-plan> --save-receipt
```

The digest detects changed execution inputs; it does **not** replace authorisation, a sandbox or an independent security gate. Read the [dispatcher execution contract](docs/skill-dispatch.md).

### 6. Validate what you can prove

```bash
python scripts/validate_skills.py
python scripts/security_lint.py
python scripts/agent_adoption_eval.py
python -m unittest discover -s tests -v
```

These commands check local structure, linting, retrieval fixtures and tests. They do not demonstrate that a particular AI host used a skill correctly. For that, preserve a redacted host trace, the exact skill revision, the task result and an independent assessment.

### GitHub and mobile: no local setup

If you are working from a phone or do not want to set up a checkout, use the repository's **Actions** tab (subject to GitHub workflow-dispatch permissions):

| Objective | GitHub Action | What to do |
| --- | --- | --- |
| Find relevant skills | **Search Shards Skill Catalogue** | Run with ordinary task terms; read the summary and exact-revision links |
| Export one uploadable skill | **Portable Agent Skills ZIP** | Choose a permitted first-party skill; download the artifact and extract the **inner** skill ZIP for a compatible host |
| Run a bounded repository check | **Run Curated Shards Skill** | Select one of seven reviewed, read-only workflows; inspect the summary and receipt artifact |

The portable ZIP option intentionally supports only **seven** self-contained instruction-only skills. Other catalogue and curated skills can require the full checkout. The Actions runner cannot give a consumer chat account remote skills access or grant new permissions. Follow the [portable ZIP instructions](docs/portable-agent-skills.md#mobile-friendly-single-skill-zip-for-upload-based-clients) and [manual workflow guide](docs/manual-skill-runs.md).

---

## Find the right skill

Run the metadata finder in a trusted checkout with Python 3.11 or later.

```bash
python scripts/search_skills.py --query "Resume an interrupted GitHub PR repair and verify the changes before merging" --limit 5
python scripts/search_skills.py --skill shards-review-resolution
```

Open the selected `SKILL.md` and inspect the prerequisites, workflow, expected output and failure handling. The catalogue skills give agents instructions. Curated workflows have separately governed Python entry points.

| Task | Start here |
| --- | --- |
| Diagnose, implement and test | [Systematic debugging](skills/systematic-debugging/SKILL.md), [implementation planning](skills/implementation-planning/SKILL.md), [test-driven development](skills/test-driven-development/SKILL.md) |
| Review changes and verify evidence | [Code review](skills/code-review/SKILL.md), [review resolution](skills/shards-review-resolution/SKILL.md), [evidence verification](skills/shards-evidence-verification/SKILL.md) |
| Resume or hand off work | [Restore and recover](skills/shards-restore-recover/SKILL.md), [context recovery](skills/shards-context-recovery/SKILL.md), [task contract](skills/shards-task-contract/SKILL.md) |
| Assess security and permissions | [Security intake](skills/shards-sec-intake/SKILL.md), [secure code review](skills/secure-code-review/SKILL.md), [security assurance guide](docs/security-assurance.md) |
| Research and analyse | [Evidence-based research](skills/evidence-based-research/SKILL.md), [scientific research](skills/scientific-research/SKILL.md), [reproducible data analysis](skills/reproducible-data-analysis/SKILL.md) |
| Check local repository and agent workflows | [Shards Core](plugins/shards-core/README.md), [governed dispatcher](docs/skill-dispatch.md), [local agent harness](docs/agent-harness.md) |

See the [60 catalogue entries](catalogue/catalogue.json) and the [discovery guide](docs/skill-discovery.md) for curated and native candidate lookup and GitHub-hosted search.

## Security and governance

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

## Install selected skills

Use the existing Skills CLI from a trusted checkout or copy the selected skill directory to the host's documented project location. The examples install one skill and a small review collection in the current Codex project.

```bash
npx skills@1.8.1 add /path/to/shards-skills --skill systematic-debugging -a codex --copy -y
npx skills@1.8.1 add /path/to/shards-skills --skill code-review shards-review-resolution shards-evidence-verification -a codex --copy -y
```

Select only the skills needed for the task. Skills that reference repository-level tools need the full checkout available. For upload-based clients, the local ZIP exporter supports a smaller self-contained selection. See the [installation and compatibility guide](docs/portable-agent-skills.md).

## Run a curated workflow

```bash
python scripts/dispatch_skills.py list
python scripts/dispatch_skills.py plan --skill shards-repository-health
```

The registry includes `shards-skill-dispatch`, `shards-a2a-harness`, and `shards-parallel-swarm`.
Review the plan and host permissions before explicitly requesting execution. Use the [dispatcher guide](docs/skill-dispatch.md) for commands, digest requirements and boundaries. To examine an external skill from a separate local checkout, use the [static skill-audit workflow](plugins/shards-core/skills/shards-skill-audit/SKILL.md).

## Verify skill use

Record the skill ID, revision, host and task. Host discovery shows a skill is available. Use a host receipt or trace to establish which skill was selected, which descriptor was opened and which steps were applied. Verify the task outcome independently. Compare equivalent runs with and without the skill before claiming benefits in correctness, time or token use. See the [adoption and evaluation guide](docs/agent-adoption.md).

### Local retrieval and integrity checks

```bash
python scripts/agent_adoption_eval.py
python scripts/validate_skills.py
python scripts/security_lint.py
python -m unittest discover -s tests -v
```

The [security policy](SECURITY.md) covers untrusted instructions and how to report a concern. The original imported collection is accessible through the pinned revision in the [historical source index](third_party/SOURCES.md). Preserved licences and attribution are listed in [Third-party notices](THIRD_PARTY_NOTICES.md).
