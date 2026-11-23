# Shards operating loop: ten skills, one durable contract

The operating skills live under `skills/shards-*/SKILL.md`. They are reusable procedures and do not confer permissions. Nine of these workflows use a common append-only task ledger. The skill improver has separate plan and backup files; operators must explicitly record its receipts in the ledger. The ledger is local and portable, not a remote multi-agent database.

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
    {
      "id": "C1",
      "acceptance": "Regression tests pass and an independent reviewer approves",
      "target_revision": "0123456789abcdef0123456789abcdef01234567",
      "resource": "OWNER/REPO",
      "subject_actor": "builder-id",
      "required_evidence": ["tested", "reviewed"]
    }
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
  "revision": "0123456789abcdef0123456789abcdef01234567",
  "subject_actor": "builder-id",
  "observed_by": "ci-id",
  "resource": "OWNER/REPO",
  "observation": "Document the actual result, not the expected result"
}
```

```bash
python scripts/operating_ledger.py record --task example-fix --kind evidence --payload evidence.json
python scripts/operating_ledger.py verify --task example-fix
```

Set the actual target Git object ID, canonical repository identifier and work owner's stable host ID before initialization. Evidence types are `implemented`, `tested`, `reviewed`, `deployed` and `production-verified`. Each listed type needs its own matching observation. A formal approval requires status `reviewed`, decision `APPROVED` and an observer independent of the work owner. A comment or test receipt cannot fulfill that requirement.

The offline CLI displays recorded evidence. Its `verify` command exits 1 while completion is unverified. A trusted host may call `summary(root, task, verify_observation=...)`. Its verifier receives the task ID, immutable criterion and complete evidence payload. It must authenticate the underlying source and check the actor identities, operation, exact target, revision, result and reference. For approval it must check the formal review record and independence. Return exactly `True` only for a matching observation. No default host verifier is installed.

The summary retains contrary records. Failed or blocked observations and negative review decisions keep the criterion open until a verified current observation explicitly lists the resolved event hashes in `resolves`. Each resolution requires a distinct reference for the affected evidence type. Case and surrounding whitespace alone establish neither a distinct reviewer nor a fresh receipt. Hosts should supply stable, canonical actor and artifact identifiers. A dismissed or negative review needs fresh approval. A `fail` or `blocked` observation may name its affected `evidence_type`. An unspecified failure requires every criterion requirement to be reconfirmed. The host must confirm each resolution. Existing ledgers remain readable. Old criteria without typed requirements and a target remain unverified. Start a new linked task for new acceptance terms and retain the original history.

## Skill improvement

The standalone `skill_improver.py apply` checks the proposed plan, candidate, counts and approval, and returns a blocked result with exit 1 when independent execution evidence is unavailable. Malformed or failing receipts exit 2. Planning and rollback retain their existing interface.

Apply and rollback share an exclusive `.skill-improver.lock` next to the target. Use a trusted checkout and prevent editors or other processes from changing the target, directory or backups during a revision. The lock coordinates this tool's writers. After an interrupted run, confirm no writer is live and review the target and backup digests before removing a stale lock.

A trusted embedding host can call `apply(args, get_verified_evaluation=lookup)`. The lookup receives the full checked plan including target and baseline/candidate digests. It must retrieve an independently authenticated run for that target and both files, verify the fixed case set actually ran, and derive the counts from its outcomes. On success it returns `kind` equal to `executed-evaluation`, the independently recorded `plan_sha256` for that execution, the nonempty authenticated `evaluator` identity and `source` identifier, and a `results` object containing all seven evaluation fields. Return `None` if this cannot be established. The tool compares this record to the candidate's claimed results before writing. Supplying the candidate's JSON as the lookup implementation would invalidate the trust boundary. Authorisation remains the caller's responsibility.

## Other events

`record --kind` accepts `attempt`, `checkpoint`, `review`, `lesson`, `decision`, `amendment`, and `evidence`.

For attempt/checkpoint/review/lesson/decision use JSON fields `criterion_id` (string or null), `action`, `result`, `reference`. The last three must be non-empty strings. Three matching attempts produce a repetition warning in `show`.

An amendment requires `reason`, `authority` and `criteria` (new IDs only); original criteria are retained. Never amend merely to mask a failed task.

Ledger rows are SHA-256 chained and append-only under `.shards/state/tasks` by default. This detects casual corruption, **not malicious edits by anyone who can rewrite the entire file**. A lock file rejects concurrent writers. If a crash leaves `<task>.lock`, first establish that no writer is running on that machine, verify the latest `show`/ledger hash chain, then manually remove only the matching stale lock file before retrying. Never delete the lock while a writer might be active. The ledger does not replicate between hosts; transfer it using the organisation's approved artifact or repository-state mechanism, never secrets.

## Host compatibility checklist

Codex, Claude, ChatGPT Work and other hosts may read the shared descriptors; actual integration requires an adapter validation record that names the host/version, tool bindings, filesystem permissions, context-refresh behavior, attempted unauthorised action, receipt export and exact test results. No host is marked verified by this documentation alone.

## Acceptance test

Agent A begins `example-fix`, records the contract and a checkpoint, and stops. Agent B loads the ledger, checks the actual branch/reviewer status, fixes one defect, records review disposition and tests, and demonstrates C1 without inventing a new PR or asking for previously granted authority. Capture unnecessary tool calls, elapsed time and user interventions for comparison with a baseline.

## Known limitations

The operating ledger is not a service-side permit authority, is not tamper-proof against a filesystem owner and cannot attest external facts. The improver's eval receipt is operator-supplied, not authenticated independent evidence. The new nine skills are **draft**, not certified adapters or unattended automation.
