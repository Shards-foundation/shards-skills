# Shards Skills

Shards Skills is an independently developed library of workflows for AI-assisted engineering, security, research and operations. It contains 60 catalogue skills, 13 curated Shards Core workflows, and four separate native host candidates.

## Find the right skill

Run the metadata finder in a trusted checkout with Python 3.11 or later.

```bash
python scripts/search_skills.py --query "Resume an interrupted GitHub PR repair and verify the changes before merging" --limit 5
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

For the full inventory, see the [catalogue](catalogue/catalogue.json). The [discovery guide](docs/skill-discovery.md) also covers GitHub-hosted search.

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
npx skills add /path/to/shards-skills --skill systematic-debugging -a codex --copy -y
npx skills add /path/to/shards-skills --skill code-review shards-review-resolution shards-evidence-verification -a codex --copy -y
```

Select only the skills needed for the task. Skills that reference repository-level tools need the full checkout available. For upload-based clients, the local ZIP exporter supports a smaller self-contained selection. See the [installation and compatibility guide](docs/portable-agent-skills.md).

## Run a curated workflow

```bash
python scripts/dispatch_skills.py list
python scripts/dispatch_skills.py plan --skill shards-repository-health
```

The registry includes `shards-skill-dispatch`, `shards-a2a-harness`, and `shards-parallel-swarm`.
Review the plan and host permissions before explicitly requesting execution. Use the [dispatcher guide](docs/skill-dispatch.md) for commands, digest requirements and boundaries. To examine an external skill from a separate local checkout, use the [static skill-audit workflow](plugins/shards-core/skills/shards-skill-audit/SKILL.md).

## Verify that a skill was used

Record the skill ID, revision, host and task. Host discovery shows a skill is available. Invocation evidence should show which skill was selected, that its instructions were opened, and which steps were applied. Verify the task outcome independently. Compare equivalent runs with and without the skill before claiming benefits in correctness, time or token use. See the [adoption and evaluation guide](docs/agent-adoption.md).

```bash
python scripts/agent_adoption_eval.py
python scripts/validate_skills.py
python scripts/security_lint.py
python -m unittest discover -s tests -v
```

The [security policy](SECURITY.md) covers untrusted instructions and how to report a concern. The original imported collection is accessible through the pinned revision in the [historical source index](third_party/SOURCES.md). Preserved licences and attribution are listed in [Third-party notices](THIRD_PARTY_NOTICES.md).
