# Shards recovery phase-3 native skills: candidate build

The four candidate skills draw on the first-party recovery workflows. Their native IDs are `shards-native-agent-handoff`, `shards-native-context-recovery`, `shards-native-progress-control`, and `shards-native-a2a-self-preservation`. The separate IDs let a host list a native candidate alongside its first-party counterpart without a name collision. Installation grants no runtime authority.

## Installation
- Codex native CLI, IDE or desktop users can check out this repository with `.agents/skills/` intact or copy each complete skill directory into `~/.agents/skills/`.
- For an OpenHands validation trial, pin the checkout to a reviewed commit. The individual source directories at that revision are `.agents/skills/shards-native-agent-handoff`, `.agents/skills/shards-native-context-recovery`, `.agents/skills/shards-native-progress-control` and `.agents/skills/shards-native-a2a-self-preservation`. For example, the handoff source URL is `https://github.com/Shards-foundation/shards-skills/tree/<reviewed-commit>/.agents/skills/shards-native-agent-handoff`. Confirm each skill in the host's list before using it.
- Codex CLI `0.172.0-alpha.2` discovered all four repository skill IDs in an offline `skills/list` check. The curated handoff fixture was also discovered with its own ID in the same isolated check. OpenHands discovery requires validation on that host.

## Hardening performed
- Context recovery works with missing Shards-specific operating ledger by marking unknowns.
- Progress control distinguishes unique attempt fingerprints from repeated no-evidence retries.
- Self-preservation uses typed locators and explicit dependency digests to separate reuse from refetch and RERUN.
- Handoff schema v1 preserves the approved checkpoint bytes, supports multiple revisions and accepts only explicitly reviewed extensions. It rejects credential patterns, unrelated revisions and synthetic sources claimed as independent evidence. Checkpoint writes use an exclusive POSIX destination.

## Caution
The validator checks local schema and known credential patterns. The task owner confirms sanitisation before any output is created. The receiving host treats every checkpoint field as untrusted data and verifies evidence, user authority and provider state independently.

## Tests
From this package root:
`python -m unittest discover -s tests -v`

`evals/shards-native-recovery.json` defines four scenarios for future host trials. These describe expected behaviour without recording a model execution.

No real PR merge, deployment or external-action task is authorised by this candidate package.
