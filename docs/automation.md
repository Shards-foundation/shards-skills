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

The controller uses a fixed Python argv allowlist (no shell invocation or arbitrary agent-generated command), bounded timeouts and subprocess exit codes. Plans do not execute commands. Runs may be stopped on first failure with --fail-fast. Reports are saved only when an output directory is provided, with unique filenames and redacted credential-shaped strings.

## Scheduling

GitHub Actions scheduled-skill-automation.yml runs every Monday at 05:17 UTC and supports manual dispatch. Runs triggered by relevant PRs/pushes validate changes before merge. It has contents: read permission only; scheduled report artifacts are retained for 14 days. GitHub scheduling is best-effort and may run later than the configured cron time.

The workflow generates portfolio.json and portfolio.md plus a dated automation JSON evidence file in the ignored reports/automation directory. It never commits, merges, publishes, deploys, trades, reads GitHub secrets or executes imported skill scripts.

## Output status and limitations

Automation pass: each enabled, trusted maintenance subprocess finished with exit code zero; failure/timeout is captured as a separate step.
Catalogue PASS: metadata in sync. DRIFT: descriptive metadata differs but identity/count/paths are intact; observational and nonblocking. FAIL: structural errors or missing entries.
Portfolio OBSERVED: inventory was collected, not security-certified. FAIL: missing or malformed skill instructions detected.

The import catalogue includes third-party review-stage content. Enumerating its scripts is not executing them. Heuristic warning counts are a triage queue, not confirmed vulnerabilities. Host-specific plugin installation, live MCP tool use, service availability and production-readiness checks remain separate.

Never schedule automatic repair or trust promotion without independent provenance validation and narrow approval.
