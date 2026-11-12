# Upstream record

- Source: https://github.com/Jakeschincariol/day-trader-skill
- Author: Jake Schincariol
- Commit: `3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd`
- Original path: `trader-budget`
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

- Original package: https://github.com/Jakeschincariol/day-trader-skill/tree/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd/trader-budget
- Original offline tests: https://github.com/Jakeschincariol/day-trader-skill/tree/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd/tests
