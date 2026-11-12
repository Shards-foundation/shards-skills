# Shards operating loop: ten skills, one durable contract

The operating skills live under `skills/shards-*/SKILL.md`. They are reusable procedures and do not confer permissions. Unlike the historical catalogue, these nine new workflows use a common append-only task ledger. The skill improver has separate plan and backup files; operators must explicitly record its receipts in the ledger. The ledger is local and portable, not a remote multi-agent database.

## Execution order

1. **Task contract** establishes stable acceptance IDs and existing authorisation.
2. **Context recovery** restores the original contract and checks live repository state after interruption.
3. **Tool selection** selects an appropriate least-privilege operation.
4. **Progress control** records attempts; repeated identical outcomes trigger route reassessment.
5. **Evidence verification** binds criterion results to traceable revisions and artifacts.
6. **Review resolution** triages findings without confusing code changes with fixes.
7. **Learning capture** preserves narrowly scoped lessons and expiry/revalidation rules.
8. **Skill evaluation** compares baseline/candidate on fixed and holdout test cases.
9. **Controlled skill updates** calls `scripts/skill_improver.py` only after reviewed evidence and explicit approval.
10. **Host compatibility** records what actually runs on each host/version.

## Local task record

Requires Python 3.11+ and a trusted full checkout. No dependency installation, third-party code execution, hosting, git mutation or network operations are performed by `operating_ledger.py`.

Save this as `contract.json`:

```json
{
  "outcome": "Deliver an independently reviewable repository fix",
  "scope": "Only the agreed feature branch; no release",
  "authority": "Local branch edits and tests approved; merge requires protected-branch gates",
  "criteria": [
    {"id": "C1", "acceptance": "Regression is reproduced and corrected"},
    {"id": "C2", "acceptance": "Required tests and independent reviews pass"}
  ]
}
```

```bash
python scripts/operating_ledger.py init --task example-fix --payload contract.json
python scripts/operating_ledger.py show --task example-fix
```

For evidence, save `evidence.json`:

```json
{
  "criterion_id": "C1",
  "status": "tested",
  "reference": "https://github.com/OWNER/REPO/actions/runs/REAL-RUN-ID",
  "revision": "EXACT-COMMIT-SHA",
  "observation": "Document the actual result, not the expected result"
}
```

```bash
python scripts/operating_ledger.py record --task example-fix --kind evidence --payload evidence.json
python scripts/operating_ledger.py verify --task example-fix
```

`verify` returns nonzero until all criteria have qualifying evidence. It checks presence and integrity of **operator-recorded** evidence, not the truth of external URLs or deployment status. Do not promote a task to production-verified without external host-level checks.

## Other events

`record --kind` accepts `attempt`, `checkpoint`, `review`, `lesson`, `decision`, `amendment`, and `evidence`.

For attempt/checkpoint/review/lesson/decision use JSON fields `criterion_id` (string or null), `action`, `result`, `reference`. The last three must be non-empty strings. Three matching attempts produce a repetition warning in `show`.

An amendment requires `reason`, `authority` and `criteria` (new IDs only); original criteria are retained. Never amend merely to mask a failed task.

Ledger rows are SHA-256 chained and append-only under `.shards/state/tasks` by default. This detects casual corruption, **not malicious edits by anyone who can rewrite the entire file**. A lock file rejects concurrent writers. If a crash leaves `<task>.lock`, first establish that no writer is running on that machine, verify the latest `show`/ledger hash chain, then manually remove only the matching stale lock file before retrying. Never delete the lock while a writer might be active. The ledger does not replicate between hosts; transfer it using the organisation's approved artifact or repository-state mechanism, never secrets.

## Host compatibility checklist

Codex, Claude, ChatGPT Work and other hosts may read the shared descriptors; actual integration requires an adapter validation record that names the host/version, tool bindings, filesystem permissions, context-refresh behavior, attempted unauthorised action, receipt export and exact test results. No host is marked verified by this documentation alone.

## Acceptance test

Agent A begins `example-fix`, records the contract and a checkpoint, and stops. Agent B loads the ledger, checks the actual branch/reviewer status, fixes one defect, records review disposition and tests, and demonstrates C1/C2 without inventing a new PR or asking for previously granted authority. Capture unnecessary tool calls, elapsed time and user interventions for comparison with a baseline.

## Known limitations

The operating ledger is not a service-side permit authority, is not tamper-proof against a filesystem owner and cannot attest external facts. The improver's eval receipt is operator-supplied, not authenticated independent evidence. The new nine skills are **draft**, not certified adapters or unattended automation.
