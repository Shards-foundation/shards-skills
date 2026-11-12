# Shards Security Assurance — operator and agent guide

Status: **first-party draft workflow**. This is an offline, read-only, dependency-free, Python 3.11+ control planner and evidence triage tool. It does **not** scan hosts, inspect production controls, validate legal obligations, certify regulatory compliance or authorise external actions.

## First 60 seconds

From the Shards Skills repository root:

```bash
python scripts/security_assurance.py list
python scripts/security_assurance.py plan --system "My new AI fintech app" --profiles web,ai,fintech --output security-plan.json
```

Selecting any other profile automatically includes `base`; there are eight profiles: `base`, `web`, `ai`, `crypto`, `fintech`, `cloud`, `privacy`, `governance`. A plan is **a proposed checklist, not proof of a test**.

Before assessing, review system ownership, authorisation, target revision, environment and regulator applicability. Do not paste production passwords, signing keys or customer records into a planning agent.

## Optional local source preflight for beginners

For an **owned Git checkout**, the Shards vibe-coding gate can run a conservative local heuristic:

```bash
python scripts/vibecode_guard.py --repo .
python scripts/vibecode_guard.py --repo . --output local-preflight.json
```

The preflight enumerates tracked files and reads bounded source text without running application code, installing packages, sending network requests, scanning websites or printing matched code/secrets. It flags selected patterns such as tracked .env/key files, disabled TLS checks, dynamic evaluation, unsafe YAML loaders, overly broad CI permissions, public CORS indicators and permissive row policies. Findings contain **rule IDs, file paths, line numbers and remediation hints**, never source snippets. Each finding requires human verification; legitimate code may be flagged. A clear result is only `CLEAR_HEURISTICS_ONLY`, never SAFE. Exit status 0 means no configured findings in a complete scan; 1 means warnings; 2 means blocked or incomplete inspection. Inspect `incomplete`, `truncated` and `skipped_paths` for finding-cap saturation, unsafe paths, missing or oversized tracked sources and undecodable code. This heuristic is not exhaustive and unlisted extensions are intentionally outside its coverage.

This is intentionally narrower than a true static-analysis pipeline, dynamic scan or penetration test. For sensitive products add reviewed tooling, API/authorization negative tests, cloud controls and specialist review. Do not point it at a codebase you do not have permission to inspect.

## Evidence input

Create `assessment.json` (non-production example with **no claimed passes**):

```json
{
  "schema_version": 1,
  "scope": {
    "system": "Example web app",
    "owner": "named operator",
    "jurisdictions": ["GB"],
    "revision": "exact-reviewed-commit",
    "environment": "local-test",
    "authorised_scope": "Owned repository and test environment only",
    "profiles": ["base", "web"]
  },
  "observations": []
}
```

Run:

```bash
python scripts/security_assurance.py assess --input assessment.json --output security-assessment.json
```

This example exits **1** (HOLD), because no control has evidence. Exit 0 means **REVIEW_READY_NOT_CERTIFIED**, not compliant or production-safe. Exit 2 is invalid or unsafe input. Output files are create-only; use a fresh filename for each assessment.

To record an actual observed control, add an object to `observations`:

```json
{
  "control_id": "WEB-01",
  "status": "fail",
  "reference": "local-test/report-tenant-isolation-001",
  "revision": "exact-reviewed-commit",
  "observation": "Synthetic user B could read synthetic user A's record",
  "approver": null
}
```

Only status `pass`, `fail`, or `not_applicable` is accepted. The report changes operator-supplied `pass` to **REPORTED_PASS**, since this CLI does not independently verify URLs or test artifacts. Missing observations become **BLOCKED**. Critical controls cannot be marked not-applicable automatically. Noncritical exclusions require a named approver and still produce **NOT_APPLICABLE_REVIEW**, pending independent validation. Every record must reference the **same exact revision**. Duplicate IDs, unknown controls, unsanctioned profiles and malformed evidence are rejected.

## Scope-preserving reports

Assessment results now include an explicit `scope` object containing the validated
`system`, `owner`, `jurisdictions`, `revision`, `environment`,
`authorised_scope`, and selected `profiles`. Legacy top-level fields
are retained for existing consumers. Store the full scope beside the
report's registry and input SHA-256 values. These fields are **operator-provided**
and are not independently authenticated; never promote them into a legal
authorisation or security approval without corroborating records.

## Behavioural skill evaluation protocol

The six priority skills each have four **scenario-level** trials: positive authorised
read-only work, an invalid security/legal claim, missing essential input and an
unauthorised action request. The 24 frozen cases are at
`evals/shards-security-workflows.json`. Inspect them first:

```bash
python scripts/security_skill_eval.py cases
```

An independent test runner must execute every prompt on the actual named agent
host, capture the full response and tool/action trace as protected artifacts,
and produce a JSON receipt with exactly these fields:

```json
{
  "schema_version": 1,
  "case_set_sha256": "actual SHA-256 from cases command",
  "host": {
    "name": "real host name",
    "model": "actual model ID",
    "version": "exact tested version",
    "test_environment": "isolated test workspace",
    "collector": "name of independent evidence collector"
  },
  "responses": [
    {
      "case_id": "IN-POS",
      "decision": "ASSESS_READ_ONLY",
      "observed_guardrails": ["ownership-stated", "read-only-scope"],
      "affirmative_claims": [],
      "executed_effects": [],
      "artifact_ref": "readable evidence reference to the raw host response and action trace"
    }
  ]
}
```

That is a **partial example**, not a completed trial. Use the actual case-set
hash and include all 24 responses before claiming test coverage. The evaluator
will never synthesize results:

```bash
python scripts/security_skill_eval.py score --receipts host-trial.json --output host-trial-report.json
```

Exit 0 means only that the self-reported receipts match the expected
*structural* decisions and there are no missing cases. The resulting gate is
`HUMAN_REVIEW_REQUIRED` — never `VERIFIED`. Exit 1 means an incomplete or
failed trial; exit 2 means an invalid receipt. A separate reviewer must inspect
each original response, invocation trace, source revision, refusal and
negative control, and record independently attested pass/fail results before
any security skill can advance beyond `draft`. Structural matching can be
gamed by a model and is not itself evidence of security.

The six covered skills are intake, vibe-coding, identity/access, web/API,
AI agent boundaries and jurisdiction applicability. These fixtures currently
have status **unexecuted**. No compatibility or performance claims are being
made for ChatGPT, Claude, Codex or any other host.

## Standard finding record

Each skill should produce a human-readable finding with:
- Identifier and control/profile; affected asset, owner and jurisdiction.
- Observed fact separated from inference; exact revision, environment and date.
- Severity (critical, high, medium, low); impact, likelihood and mitigation.
- Status: PASS (tested), FAIL (reproduced), BLOCKED (missing evidence), NOT_APPLICABLE (reason + reviewer).
- Evidence reference, reproduction steps using synthetic data, acceptance test and accountable owner.

Human-readable PASS means a *specific test passed*; it is not a declaration that the product is secure. For high-risk system changes, require security and legal approvers independently of the agent. Never allow skills to approve their own risk exceptions.

## Safety and trust boundaries

- The 45-control register is `catalogue/shards-security-controls.json`; every report pins its SHA-256 digest to help detect version drift. Registry contents are not legal requirements or authoritative audit conclusions.
- The security skills in `skills/shards-sec-*/SKILL.md` are **instructions**. They neither install a scanner nor grant permissions. They must run only inside the permissions of the host.
- Assessment input is untrusted; keep it below 1 MB. The CLI rejects direct symlink inputs, unusually shaped fields, common key formats and credentials in short text fields, but these are not complete secret detection safeguards.
- No external scanning, vulnerability exploitation, financial transaction or live-wallet signing occurs.
- A risk reviewer must validate that each evidence reference resolves to a real artifact and that the artifact proves the control in this exact environment and date.
- Regulatory applicability varies by legal entity, location, activity, counterparties and effective date. Obtain qualified advice for material legal decisions.

## Suggested beginner route

For a new app built through AI prompts: `shards-sec-intake` → `shards-sec-vibecoding-gate` → `shards-sec-identity-access` → `shards-sec-web-api` → `shards-sec-privacy-dpia` → `shards-sec-cloud-devsecops` → `shards-sec-incident-response`. Add `shards-sec-ai-agent-boundaries` for agents, `shards-sec-crypto-custody` for wallets and `shards-sec-fintech-payments` when handling money.

For enterprise security management: start with `shards-sec-business-threat-model`, then `shards-sec-governance-policy`, `shards-sec-jurisdiction-scope`, `shards-sec-third-party-risk`, `shards-sec-compliance-evidence` and `shards-sec-resilience-recovery`.

## Acceptance contract and continuous improvement

An agent should be able to take a user story, select a skill using its trigger, capture the scoped threat and evidence, produce a reproducible finding, refuse an unauthorised action, and pass the case to another agent without inventing results. When PR #16's operating skills are merged, record attempts and evidence in their task ledger and use the separately governed skill improver to evaluate revisions. These systems are **not wired together on this branch**.

The shared curriculum is anchored to dated primary references in `docs/security-frameworks.md`. Update guidance only after verifying newer editions; do not overwrite old version mappings silently.
