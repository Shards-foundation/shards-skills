# Shards recovery phase-3 native skills: candidate build

Scope: four skills only, based on source snapshots from main, PR #16 and PR #28 on 18 November 2026. The branch/packages are **candidates**, not merged or independently reviewed. No production or runtime authorisation comes from installing them.

## Installation
- Codex native CLI/IDE/desktop: place skill directories under a recognised `~/.agents/skills/` or repository `.agents/skills/`, or upload each standalone skill ZIP on a supported Skills surface. Do not assume ChatGPT and Codex have identical skills UI.
- OpenHands repository source: `github:Shards-foundation/shards-skills`, name `shards-recovery-phase3`, Branch/Tag/Commit: pin the candidate feature branch SHA, Repository Path `.agents/skills`. Check the installed skills list before calling the install complete.
- For a portable bundle in this ZIP, each SKILL.md is at `.agents/skills/<name>/SKILL.md`; install the individual skill folders, not the bundle wrapper itself, when the host expects a single skill.

## Hardening performed
- Context recovery works with missing Shards-specific operating ledger by marking unknowns.
- Progress control distinguishes unique attempt fingerprints from repeated no-evidence retries.
- Self-preservation uses typed locators and explicit dependency digests to separate reuse from refetch and RERUN.
- Handoff schema v1 preserves complete input fields, multiple revisions, actor authority, evidence and timestamps, rejects malformed SHA/blank evidence/synthetic claimed independent proof, writes only to an exclusive destination.

## Caution
The validator produces `SCHEMA_VALID` only: it does not verify the truth of an evidence claim, user authority, a GitHub reviewer identity or remote provider state. Self-reported `INDEPENDENTLY_VERIFIED` remains a claim until checked by the receiving host.

## Tests
From this package root:
`python -m unittest discover -s tests -v`

No real PR merge, deployment or external-action task is authorised by this candidate package.
