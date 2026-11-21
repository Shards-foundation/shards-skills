# Portable Shards AI Agent Boundaries — Manus / Claude

**Status:** first-party, offline, read-only governance workflow. This package provides
instructions, a control planner, a heuristic source guard and an evaluation-receipt
checker. It is not an agent sandbox, permit authority, deployed service, risk
certificate or proof of real-host skill efficacy.

## Install

**Manus GitHub import:** select *Import from GitHub*. Use the skill-folder
path under **an exact reviewed commit SHA**, not a mutable `main` link:

    https://github.com/Shards-foundation/shards-skills/tree/REVIEWED_COMMIT_SHA/skills/shards-sec-ai-agent-boundaries

Replace `REVIEWED_COMMIT_SHA` with the complete 40-character merge commit
from the protected `main` branch after review; ensure that the imported
SKILL.md, scripts/, docs/, catalogue/ and evals/ are present. A PR's
head commit is not evidence that it passed the main-branch release gate.
If GitHub folder import omits resources, use a ZIP instead.

**Trusted ZIP fallback:** open the repository's GitHub Actions workflow
`Portable Manus skill package`, select a **successful push-to-main run**
(not a pull-request run), and verify its commit SHA against the reviewed main
revision. Download its `portable-manus-skill` artifact, extract the
`shards-sec-ai-agent-boundaries.zip` from the artifact container, and compare
the ZIP SHA-256 to the checksum printed in that same trusted run's build
step. Then use Manus **Upload a skill** to install the ZIP. The checksum
detects accidental/transport changes; it is not a cryptographic publisher
signature. PR runs intentionally cannot publish installable ZIP artifacts.

Do not interpret an apparently successful import as proof that tools run.

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

The bundled `evals/shards-security-workflows.json` contains the 24-case
scenario inventory for six Shards workflows, including four agent-boundaries
cases. The `cases` command prints counts, a digest and the unexecuted status;
it does *not* print the individual scenario definitions, run those prompts
on Manus or independently validate model traces. For that
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
