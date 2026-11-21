# Shards recovery phase-3 native skills: candidate build

The four candidate skills draw on the first-party recovery workflows. Their native IDs are `shards-native-agent-handoff`, `shards-native-context-recovery`, `shards-native-progress-control`, and `shards-native-a2a-self-preservation`. The separate IDs let a host list a native candidate alongside its first-party counterpart without a name collision. Installation grants no runtime authority.

## Installation
- Codex native CLI, IDE or desktop users can check out this repository with `.agents/skills/` intact or copy each complete skill directory into `~/.agents/skills/`.
- For OpenHands, pin the checkout to a reviewed commit and open that checkout as the project. OpenHands discovers [project skills in `.agents/skills/`](https://docs.openhands.dev/overview/skills). Each candidate lives in `.agents/skills/<skill-id>/` using the IDs above. Confirm the four names in the host's available skills before using them.
- Codex CLI `0.172.0-alpha.2` found all four candidates and the distinct curated handoff ID in an offline `skills/list` check. The OpenHands SDK `1.63.1` project skill loader also found all four and their descriptions in an offline check. These checks exercised discovery without running a model.

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
