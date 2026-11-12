# Upstream record

- Source: https://github.com/Jakeschincariol/day-trader-skill
- Author: Jake Schincariol
- Commit: `3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd`
- Original path: `trader-broker`
- Retrieved: 2026-11-12
- Declared licence: MIT; the complete notice is in `LICENSE`.
- Upstream plugin version: 2.0.0
- Local status: review

## Local modifications

Flattened the folded description and normalised trigger quotation marks for the
dependency-free Shards metadata parser;
retained the original name and argument hint; added licence, review status,
category, version and immutable provenance. Prepended the Shards import status and
appended workflow, output, verification and failure sections. The original skill
body, Python tool and JSON examples are otherwise unchanged. Added this record
and a package-local copy of the upstream MIT licence.

## Execution boundary

This is a catalogue import, not a broker integration or scheduled service.
No upstream installer, plugin registration, MCP connection or live account was
enabled. Review the source and the pinned upstream tests before running scripts.
Broker actions require separate explicit order approval through the chosen host.
Public-feed availability and real brokerage behaviour were not verified by import.

- Original package: https://github.com/Jakeschincariol/day-trader-skill/tree/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd/trader-broker
- Original offline tests: https://github.com/Jakeschincariol/day-trader-skill/tree/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd/tests

## Open upstream findings — execution blockers

The import review identified two defects in the unchanged pinned source:

1. `trader-risk/check.py` falls back to a stale quote when a market entry has
   no plan entry price. This can produce PASS using data already rejected by
   its freshness check. Reject entries without a usable reference price.
2. `trader-broker/ticket.py` records loss from the original order plan at
   approval, rather than the matching risk verdict's higher loss calculated
   from a fresh quote. Placed records inherit the understatement and can allow
   subsequent trades beyond the daily risk limit. Approval and placed records
   must preserve the matching verdict's calculated loss.

These defects were identified by independent review and confirmed by source
inspection; the import did not execute a trading reproduction or fix them.
Do not use the tools for order approval or submission until both are corrected
and regression-tested. The scripts remain byte-identical to upstream for this
catalogue import and are not registered in the executable dispatcher.
