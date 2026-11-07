# Run approved Shards skills through GitHub Actions

The [Run Curated Shards Skill](../.github/workflows/run-curated-skill.yml)
workflow offers **manual, read-only** access to three reviewed first-party
workflows on a temporary GitHub Actions runner. It is designed for operators
who do not have a local Python checkout.

## Running a skill

1. Open this repository on GitHub and select **Actions**.
2. Select **Run Curated Shards Skill**.
3. Select **Run workflow** on `main` and choose a supported skill.
4. Inspect the job summary for the observed result and checkout revision.
5. Download **shards-curated-skill-receipts** under that run's artifacts.
   The archive contains the input plan, execution receipt and hashed
   dispatcher receipt. Artifacts are retained for **7 days**.

Only users who already have permission to dispatch workflows in this
repository can trigger a run. The workflow does not grant new repository
permissions.

| Selection | Operation | Effect |
| --- | --- | --- |
| `shards-repository-health` | Check Git checkout state and important files | Read-only |
| `shards-catalogue-sync` | Compare catalogue metadata with checked-out skills | Read-only |
| `shards-skill-dispatch` | Verify curated plugin descriptors and registry integrity | Read-only |

The workflow does **not** offer handoff writes, automated maintenance execution,
local tests of untrusted code, releases, deployments, or imported skill
execution. No secrets are requested. GitHub's token is `contents: read` and
checkout persistence is disabled.

## Evidence contract

The runner constructs a JSON plan, derives its `plan_sha256`, and executes
the same allowlisted skill with `--execute --expect-plan-sha256`. The
dispatcher checks the local executable, registry arguments, revision, effect,
and timeout before launching the subprocess. Receipts include exit code,
observed status, SHA-256 and commit identity. The workflow fails when the
dispatcher exits unsuccessfully and still uploads available evidence.

**Scope limitation:** the plan hash is an integrity check, not independent
approval or cryptographic authorization. Workflow access is enforced by
GitHub; the host must protect its action permissions. Passing these checks
does not establish production readiness, external service availability,
independent security certification, or any runtime host compatibility.

## Local equivalence

For manual verification in a trusted checkout:

```bash
python scripts/dispatch_skills.py plan --skill shards-catalogue-sync
python scripts/dispatch_skills.py run --skill shards-catalogue-sync --execute --expect-plan-sha256 <digest-from-plan> --save-receipt
python -m unittest discover -s tests -p 'test_manual_skill_actions.py' -v
```

Do not paste the placeholder digest as-is; use the `plan_sha256` of the
reviewed plan. To audit an imported skill, use the local static audit
entry point separately after checking provenance. This workflow deliberately
does not allow arbitrary audit targets.
