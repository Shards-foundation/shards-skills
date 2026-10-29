# Shards Skills

**A security-aware, cross-agent skills library for engineering, research, design, security, data, AI agents, blockchain, and operations.**

> Status: bootstrap release candidate. First-party skills in this repository are original Shards-authored material. Third-party catalogues are tracked as upstream sources; their contents are not silently copied into this repository.

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
