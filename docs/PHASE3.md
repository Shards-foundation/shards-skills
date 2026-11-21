# Shards recovery phase-3 native skills: candidate build

The four candidate skills draw on the first-party recovery workflows. Their native IDs are `shards-native-agent-handoff`, `shards-native-context-recovery`, `shards-native-progress-control`, and `shards-native-a2a-self-preservation`. The separate IDs let a host list a native candidate alongside its first-party counterpart without a name collision. Installation grants no runtime authority.

## Installation
- Codex native CLI/IDE/desktop: place skill directories under a recognised `~/.agents/skills/` or repository `.agents/skills/`, or upload each standalone skill ZIP on a supported Skills surface. Do not assume ChatGPT and Codex have identical skills UI.
- OpenHands repository source: `github:Shards-foundation/shards-skills`, name `shards-recovery-phase3`, Branch/Tag/Commit: pin the candidate feature branch SHA, Repository Path `.agents/skills`. Check the installed skills list before calling the install complete.
- For a portable bundle in this ZIP, each SKILL.md is at `.agents/skills/<name>/SKILL.md`; install the individual skill folders, not the bundle wrapper itself, when the host expects a single skill.
- Codex CLI `0.172.0-alpha.2` discovered all four repository skill IDs in an offline `skills/list` check. The curated handoff fixture was also discovered with its own ID in the same isolated check. OpenHands discovery requires validation on that host.

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
