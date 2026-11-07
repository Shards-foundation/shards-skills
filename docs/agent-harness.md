# Shards local multi-agent harness

This is the **first executable local orchestration layer** for Shards Skills.
It exposes four reviewed and repeatable curated skills: A2A-oriented harness
checks, dual-channel evidence separation, one-level sub-agent delegation, and
bounded parallel swarm execution.

**Protocol status:** not A2A wire-protocol compliant. The current implementation
does **not** serve an Agent Card well-known endpoint, expose HTTP or JSON-RPC,
use the official A2A SDK, discover third-party agents, or maintain durable tasks.
The official protocol and its Python SDK are separate interoperability work:
https://a2a-protocol.org/latest/specification/
https://github.com/a2aproject/a2a-python

## Quick start

Run these commands in a trusted full checkout, with Python 3.11+ and no
third-party dependencies:

~~~bash
python scripts/shards_agent_harness.py list
python scripts/shards_agent_harness.py plan --profile swarm
python scripts/shards_agent_harness.py run --profile swarm --execute --save-receipt
~~~

Run the four fixed repeatable skills:

| Curated skill | Fixed harness operation | Delegates | Concurrency |
|---|---|---|---|
| shards-a2a-harness | a2a-check | Repository health + plugin integrity | Sequential |
| shards-dual-channel | dual-channel-check | Repository health + catalogue consistency | Sequential |
| shards-subagents | subagent-check | Catalogue consistency + plugin integrity | Sequential |
| shards-parallel-swarm | swarm-check | All three safe delegates | 3 workers |

Every fixed operation requires the explicit execution flag:

~~~bash
python scripts/shards_agent_harness.py subagent-check --execute
python scripts/shards_agent_harness.py dual-channel-check --execute
python scripts/shards_agent_harness.py swarm-check --execute
~~~

The same operations are registered in the governed dispatcher:

~~~bash
python scripts/dispatch_skills.py list
python scripts/dispatch_skills.py plan --skill shards-parallel-swarm
python scripts/dispatch_skills.py run --skill shards-parallel-swarm --execute
~~~

For a separately reviewed SHA-256-pinned dispatcher plan, supply the
plan_sha256 returned by plan via --expect-plan-sha256 on run.

## Compose a custom read-only swarm

Only **three exact first-party** dispatch targets are allowed:
shards-repository-health, shards-catalogue-sync, shards-skill-dispatch.

~~~bash
python scripts/shards_agent_harness.py plan --profile custom --skill shards-catalogue-sync --skill shards-skill-dispatch --workers 2
python scripts/shards_agent_harness.py run --profile custom --skill shards-catalogue-sync --skill shards-skill-dispatch --workers 2 --execute --save-receipt
~~~

The custom profile permits 1–8 tasks and 1–4 workers. Every target is
checked against the dedicated read-only allowlist and the existing
dispatcher registry; no paths, shell commands, user-defined Python modules,
untrusted skill imports, privilege-changing operations, or nested agents can
be supplied. Preset skill overrides are refused. A CLI invocation without
--execute is refused.

## Dual-channel contract

A run produces a JSON record with **logically separate** structures:

- control_channel: ordered coordinator/task lifecycle events (swarm-started,
  delegated, completed or failed, swarm-finished). Contains IDs, status
  and worker counts—not executable instructions or skill outputs.
- data_channel: typed task evidence entries (task_id, agent_id, skill,
  sub-receipt). Data is never evaluated as policy or an executable command.

Each delegated task has a distinct stable ID within the run and a sub-agent
identity. In parallel mode, workers execute concurrently, then return
results in the original task order for deterministic joins. Aggregate status
is pass only when every delegate passes; fail, hold, timeout and
error remain failures. There are no hidden retries.

receipt_sha256 detects accidental changes to JSON data after generation.
It is **not** a signature, an append-only audit ledger, or evidence of
cross-host exactly-once execution. Optional --save-receipt performs a
create-exclusive write inside ignored reports/agent-harness/. The saved JSON\nand printed JSON are identical; the file location is not injected into the\nchecksummed record. To validate, remove only receipt_sha256 and compute the\ncanonical sorted-key JSON SHA-256 using the harness fingerprint function.

These channels are currently in-process JSON structures, not separate
authenticated network transports or an interprocess message broker.

## Security and resource envelope

- One level of delegation; no recursive tool calls or automatic self-spawning.
- Only three curated, read-only first-party operations; no imported scripts.
- Up to 8 tasks and 4 concurrent threads, with inherited bounded subprocess
  timeouts from the governed dispatcher.
- No externally visible effects, downloads, package installation,
  deployments, publications or secrets access requested.
- A changed plan, missing/mutated trusted script, unsafe executable path,
  repository SHA drift or disallowed skill fails before or during dispatch.
- Executor failure yields an attributed task error, and the aggregate fails.
- OS-level filesystem permissions remain those of the host process.
- The dispatcher applies best-effort secret redaction; raw process access and
  local filesystem races are not eliminated by this harness.

## Tests and evidence

~~~bash
python -m unittest discover -s tests -p 'test_agent_harness.py' -v
python -m unittest discover -s tests -v
python scripts/verify_plugins.py --check
python scripts/shards_agent_harness.py run --profile swarm --execute
~~~

Unit tests exercise real fan-out using a thread barrier, failed delegates,
tampered plans, forbidden skills, bounds, ordering, and separate channels.
GitHub Actions performs an end-to-end safe read-only swarm smoke test.
Passing these tests demonstrates this **specific local execution envelope**,
not general autonomous multi-model operation or A2A interoperation.

## Next A2A interoperability phase

Integrate the official A2A 1.x SDK behind a separately reviewed adapter.
Priorities: verified Agent Card, authenticated peers, remote task lifecycle,
message/artifact mappings, cancellation/deadline propagation, streaming,
transport-level authorization and two-host E2E tests. Fail closed when a
provider lacks a required capability. Do not claim remote A2A support until
those tests are run against actual external agent endpoints.
