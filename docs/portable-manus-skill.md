# Portable Shards AI Agent Boundaries — Manus / Claude

**Status:** first-party, offline, read-only governance workflow. This package provides
instructions, a control planner, a heuristic source guard and an evaluation-receipt
checker. It is not an agent sandbox, permit authority, deployed service, risk
certificate or proof of real-host skill efficacy.

## Install

**Manus GitHub import:** select *Import from GitHub* and use the skill folder URL:

https://github.com/Shards-foundation/shards-skills/tree/main/skills/shards-sec-ai-agent-boundaries

If the platform imports only SKILL.md or omits nested files, install the ZIP
from CI's portable-manus-skill artifact instead; verify that the imported
skill contains scripts/, docs/, catalogue/ and evals/. Do not
interpret an apparently successful import as evidence that the tools run.

**Portable ZIP:** from a trusted full checkout, build it locally without network calls:

    python scripts/build_portable_security_skill.py --check
    mkdir -p dist
    python scripts/build_portable_security_skill.py --zip dist/shards-sec-ai-agent-boundaries.zip

The ZIP has exactly one top-level skill directory. MANIFEST.json contains the
SHA-256 of SKILL.md and the seven bundled support files. It deliberately says
host_traces_verified=false (no behavioral evaluation has been run by the builder).

## Run offline after installation

From the imported skill directory, with Python 3.11+ and a permitted shell:

    python scripts/security_assurance.py list
    python scripts/security_assurance.py plan --system "Authorized application" --profiles base,ai
    python scripts/security_skill_eval.py cases
    python scripts/vibecode_guard.py --help

The local evaluator prints a 24-case frozen scenario inventory for six Shards
security workflows, including the four agent-boundaries cases. It does *not*
run those prompts on Manus or independently validate a model trace. For that
claim, capture actual positive/negative/missing-input/unauthorized-action host
runs with tool-call logs, source revision and raw output, then have independent
reviewers inspect the evidence.

## Maintenance

Seven support files are copies of canonical files tracked at the repository
root. Do not edit those embedded copies by hand. After changing a canonical
source, run:

    python scripts/build_portable_security_skill.py --sync
    python scripts/build_portable_security_skill.py --check
    python -m unittest discover -s tests -p 'test_portable_security_skill.py' -v

A missing, corrupted, symlinked or stale file must block the package gate.

## Security

Do not paste credentials, production secrets or user datasets into a skill.
No skill has authority to approve external actions. Tool permissions,
deployment policy, budgets and approvals must be independently enforced by
the host, preferably through a deterministic permit authority.
