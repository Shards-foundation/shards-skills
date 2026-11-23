# Shards Skills automation operations

Three Python 3.11+ standard-library scripts now provide reusable local automation and observable evidence:

- scripts/automate.py runs allowlisted maintenance profiles and writes per-run JSON reports.
- scripts/catalogue_sync.py checks and optionally repairs metadata drift in catalogue/catalogue.json.
- scripts/audit_portfolio.py reads the SKILL.md portfolio, lists script files and produces JSON/Markdown review reports.

## Run locally

From the full Shards Skills checkout:

    python scripts/automate.py list
    python scripts/automate.py plan --workflow weekly
    python scripts/automate.py run --workflow quick
    python scripts/automate.py run --workflow weekly --output-dir reports/automation
    python scripts/automate.py run --workflow verify --output-dir reports/automation
    python scripts/catalogue_sync.py --check
    python scripts/audit_portfolio.py --json-output reports/automation/portfolio.json --markdown-output reports/automation/portfolio.md

When paths are intact and descriptive metadata drift needs correction, the operator may explicitly authorize a tracked-file change:

    python scripts/catalogue_sync.py --write --approve-write

Review the Git diff before committing. The repair refuses to guess when paths/entries are missing. It never edits skill sources or third-party notices.

## Named profiles

quick: catalogue integrity, structural metadata validation, curated plugin audit.
weekly: catalogue integrity, metadata validation, heuristic security lint, portfolio inventory.
verify: catalogue integrity, metadata validation, security lint, curated plugin audit, full unit test suite.

The controller uses a fixed Python argv allowlist, launches children directly, and records their exit codes or timeouts. It rejects missing scripts, direct symlinks and script paths that resolve outside the checkout. Plans list the commands without launching maintenance steps. The run command authorises execution of the selected profile. With `--fail-fast`, the receipt lists the remaining step IDs in `pending_steps`. The `completed` count includes checks that reported an error before launch.

The CLI includes the starting Git `commit` in plans and receipts when the checkout has a readable revision. A source archive without Git metadata records `null`. The revision identifies Git HEAD. Use a clean checkout when attributing results to tracked source. Plans list the commands for operator inspection. The checkout and interpreter must stay under the operator's control between planning and execution.

### Subprocess environment and threat boundary

Maintenance subprocesses receive a **minimal allowlisted environment**: path and platform locale/temp directory essentials, plus `CI`/`GITHUB_ACTIONS` indicators when present. Parent tokens and credential variables, `PYTHONPATH`, dynamic-loader overrides such as `LD_PRELOAD`, and other unlisted variables are not forwarded. The runner explicitly sets `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, and `PYTHONNOUSERSITE=1`.

This reduces accidental credential propagation and Python import injection; it is **not a sandbox**. Subprocesses can still access filesystem locations permitted to the current operating-system user, and tests execute first-party repository code. Only run maintenance against a trusted checkout in a least-privilege environment. Log redaction recognises known patterns but cannot guarantee removal of every possible secret. A local attacker able to modify the executable after path validation may still create a time-of-check/time-of-use race.

## Report publication

With `--output-dir`, the controller writes a complete receipt to a temporary file beside the final report and publishes it atomically without replacing an existing receipt. Choose a trusted output directory on a filesystem that supports hard links. An interruption before publication can leave a hidden temporary file, which can be removed after confirming the writer has stopped. A publication error exits 2 and prints a JSON result with `status: error`, the underlying `workflow_status` and `report_error`. A complete failed maintenance run exits 1 and can still publish its failure receipt. Successful runs exit 0.

### Reproduce the weekly workflow offline

Review the ordered commands in the planned profile, run them and exercise the failure path in a disposable checkout of the same revision.

```bash
evidence="$(mktemp -d)"
python scripts/automate.py plan --workflow weekly > "$evidence/plan.json"
python scripts/automate.py run --workflow weekly --output-dir "$evidence"
python -m unittest discover -s tests -p test_automation.py -v

git worktree add --detach "$evidence/fixture" HEAD
printf '{\n' > "$evidence/fixture/catalogue/catalogue.json"
if python "$evidence/fixture/scripts/automate.py" run --workflow weekly --fail-fast \
    --output-dir "$evidence/failure"; then
  echo "Unexpected success with malformed catalogue" >&2
  exit 1
else
  test "$?" -eq 1
fi
```

The success receipt should record all five planned commands with exit 0. The failure receipt should record `catalogue-check` with exit 2, a JSON parse diagnostic and four pending steps. The worktree contains deliberate fixture changes. Its receipt records the starting commit, and the command above identifies the local input change.

## Scheduling

GitHub Actions scheduled-skill-automation.yml runs every Monday at 05:17 UTC and supports manual dispatch. Runs triggered by relevant PRs/pushes validate changes before merge. It has contents: read permission only; scheduled report artifacts are retained for 14 days. GitHub scheduling is best-effort and may run later than the configured cron time.

The automation workflow tests PRs at the exact source-head SHA. Core plugin gates also test GitHub's merge checkout. The scheduled workflow saves the revision, plan, dated automation receipt, and portfolio JSON and Markdown under `reports/automation`. It validates the saved receipt against the plan and checkout before reporting success. The artifact name includes the checkout SHA and run attempt. Once `Record checkout revision` succeeds, the workflow attempts to collect portfolio evidence and upload available files even if a later step fails. A failed revision-recording step or a cancelled run skips both evidence steps.

## Output status and limitations

Automation pass: each enabled, trusted maintenance subprocess finished with exit code zero. Failed, timed-out and unavailable steps have distinct statuses.
Catalogue PASS: metadata in sync. DRIFT: descriptive metadata differs but identity/count/paths are intact. FAIL: inconsistent paths or counts. ERROR: invalid catalogue data, including duplicate entries, unsupported schema or unreadable JSON.
Portfolio OBSERVED: inventory was collected, not security-certified. FAIL: missing or malformed skill instructions detected.

The portfolio audit lists metadata and scripts without executing them. The same audit can inspect a separate checkout with `--root`. Heuristic warning counts are a triage queue, not confirmed vulnerabilities. Host-specific plugin installation, live MCP tool use, service availability and production-readiness checks remain separate.

Never schedule automatic repair or trust promotion without independent provenance validation and narrow approval.

## Curated skill dispatch
Use scripts/dispatch_skills.py list, plan --skill shards-repository-health, and run --skill shards-repository-health --execute. All commands are fixed trusted mappings, with exit-code and source-hash evidence. See skill-dispatch.md for the permission model. The new plugin-integrity step runs in quick, weekly and verify maintenance profiles.
