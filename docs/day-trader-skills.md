# Day Trader skill pack

Eleven packages from Jake Schincariol's
[day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill)
are included under `skills/trader-*`. The source is pinned to commit
`3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd` (upstream plugin version 2.0.0),
retrieved on 2026-11-12. Copyright (c) 2026 Jake Schincariol, MIT License.

## Included files

All eleven `SKILL.md` descriptors, eleven Python tools and five JSON examples
are included. Each package also has a complete `LICENSE` and an `UPSTREAM.md`.
Original Python and JSON files are unchanged. Skill bodies are preserved;
frontmatter is flattened for the Shards parser, with provenance and review
sections added around the original instructions.

The [file manifest](../third_party/day-trader-skill/manifest.json) records
upstream and local SHA-256 hashes for all 27 original files. Upstream plugin
manifests, installers and the upstream test suite are not registered or copied
into Shards CI. The pinned [upstream tests](https://github.com/Jakeschincariol/day-trader-skill/tree/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd/tests)
remain available for a separate execution review.

## Discover and review

```bash
python scripts/search_skills.py --query "trader" --category finance --limit 20
python plugins/shards-core/scripts/run.py audit-skill --path skills/trader-scanner
```

These commands inspect metadata and files only. All eleven packages have
`status: review` and remain outside the executable dispatcher. A successful
import check does not establish that financial calculations, market feeds or
broker integrations are suitable for live trading.

## Paths and prerequisites

The tools use standard-library Python; upstream states Python 3.8 or later.
Shards repository checks use Python 3.11 or later. SEC tools require a valid
`SEC_USER_AGENT` or `sec_user_agent` configuration. Reading disclosure PDFs may
also require the `pdftotext` executable. Optional brokerage connector setup is
described upstream and is not performed by this import.

Keep the eleven original `trader-*` directory names. Upstream examples such as
`python3 trader-scanner/scan.py ...` assume the original repository layout.
When using this checkout, resolve the executable from
`/absolute/path/to/shards-skills/skills/trader-scanner/scan.py` instead.
Use a separate working directory for the shared `trader/` data folder; every
skill in a workflow must use that same working directory. The example configuration
is at `skills/trader-budget/config.example.json`. It uses USD, New York session
times and US market assumptions. Review those settings for the intended account.

The source reads public Yahoo Finance, Nasdaq Trader, SEC EDGAR, House Clerk and
Stooq endpoints. Broker instructions describe optional Alpaca/Interactive Brokers
connectors; `ticket.py` itself only creates tickets and local records. Credentials
and account state should never be committed to this repository.

## Verification scope

The import is checked using repository metadata validation, heuristic security
lint, the existing repository unit suite, static audits of all eleven packages,
Python syntax parsing, JSON parsing, metadata-only discovery and file-hash
comparison against the pinned upstream checkout. These checks do not execute
the imported trading scripts.

Public feeds, scheduled monitoring, host installation, trade calculations and
broker order execution remain unverified by this import. Preserve paper trading
and the upstream per-order approval requirements when separately reviewing a
host integration. No broker connection or live trading is enabled here.


## Open upstream findings

Independent PR review found two defects in the preserved source. Source inspection
confirmed the relevant paths; no trading reproduction was run during this import.

| Finding | Consequence | Required correction before execution |
| --- | --- | --- |
| [Stale market reference](https://github.com/Shards-foundation/shards-skills/pull/15#discussion_r4549614914) in `trader-risk/check.py` | With no planned entry, a quote rejected for freshness can still be used to return PASS. | Reject market entries without a usable price reference; add stale-quote regression coverage. |
| [Understated approved loss](https://github.com/Shards-foundation/shards-skills/pull/15#discussion_r4549614905) in `trader-broker/ticket.py` | Approval/placed logs can understate the risk already calculated from a higher fresh quote, weakening the daily limit. | Preserve the matching risk verdict's calculated loss through approval and placement; add daily-limit regression coverage. |

These are unresolved upstream execution blockers, not fixed defects. The import
preserves the pinned Python source for inspection, records the findings in the
file manifest and affected packages, and keeps every package outside the Shards
executable dispatcher. Do not use these tools to approve or submit trades until
the findings are corrected and independently verified.
