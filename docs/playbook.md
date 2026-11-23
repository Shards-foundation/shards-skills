# Shards Skills Playbook

Operational sequences for applying Shards Skills to real work. The [cookbook](cookbook.md) supplies short commands; the [rulebook](rulebook.md) summarises stop conditions; [`agent-index.yaml`](../agent-index.yaml) is the advisory machine-routing view.

For Python commands, substitute `python3` or `py -3.11` when the host does not expose Python 3.11+ as `python`.

**Source of authority:** [`AGENTS.md`](../AGENTS.md), [`agent.md`](../agent.md), [`SECURITY.md`](../SECURITY.md), task-specific human permission and external host policy. This guide does not create permissions or supersede those sources.

## Default execution loop

| Phase | Agent must establish | Deliverable / gate |
| --- | --- | --- |
| **OBSERVE** | Target repository, branch, current SHA, user outcome and available tools | Reproducible baseline; no inferred access |
| **CONTRACT** | Scope, acceptance criteria, prior decisions and stop condition | Stable task/criterion IDs for multi-step work |
| **SELECT** | Smallest relevant first-party descriptor; status and dependencies | One primary skill, at most necessary helpers |
| **AUTHORISE** | Read, local write, local execute, external write or sensitive effect | Host-enforced permission and precise action scope |
| **EXECUTE** | Bounded next action; timeout, tool failure and retry budget | Actual diff or command output, not a prediction |
| **VERIFY** | Exact revision, commands, exit codes, reviews and missing evidence | PASS, FAIL, BLOCKED or UNVERIFIED with provenance |
| **CHECKPOINT** | Achievements, unresolved findings, one next action | Sanitised handoff with no secrets |

Follow [the operating loop](operating-loop.md) for durable contracts and evidence. Read `AGENTS.md` before any descriptor.

## Risk-scaled gate selection

| Task type | Minimum gate | What is **not** implied |
| --- | --- | --- |
| **Documentation / static metadata** | Check exact changed paths, local links, examples, diff and target branch; submit reviewable change | No need to claim runtime E2E from prose |
| **Local implementation** | Reproduce, add tests, run relevant checks, inspect diff and preserve rollback path | Passing local tests does not certify host support |
| **First-party local execution** | Inspect known script, plan/effect/hash, require `--execute` and verify receipt | Plan hash is not a permission |
| **External write / merge / release** | Specific user authority, current target SHA, independent gates where required, trusted host enforcement | A skill can never approve its own merge |
| **Sensitive / irreversible action** | Separate narrowly scoped approval and real platform policy enforcement; stop on ambiguity | An agent-produced checklist is not a security control |

### Playbook A: existing PR / review-to-resolution

1. Read the **current** PR, branch, head SHA, existing reviews, unresolved threads and CI results. Never rely on a previous transcript as live status.
2. Create or restore a task contract with [`shards-task-contract`](../skills/shards-task-contract/SKILL.md); preserve original acceptance IDs and the existing PR.
3. Route findings through [`shards-review-resolution`](../skills/shards-review-resolution/SKILL.md). Assign finding IDs, link lines/commits, classify severity and evidence.
4. For a fix, alter only approved files; add a regression case. After a head SHA change, rerun the affected checks and reread stale reviews.
5. Use [`shards-evidence-verification`](../skills/shards-evidence-verification/SKILL.md). Report a review recommendation separately from an actual authenticated GitHub review.
6. **Stop at the agreed gate.** Do not merge, deploy or publish unless explicitly authorised and currently permitted.

**Completion evidence:** exact new SHA, changed paths, command/exit results, still-open findings, independently confirmed review state and a clear next action.

### Playbook B: interrupted or handed-over task

1. Read the existing ledger/checkpoint, or report **BLOCKED** if it is unavailable. See [context recovery](../skills/shards-context-recovery/SKILL.md).
2. Compare saved scope, branch, revision, criteria, recorded failures and approvals with the **live** repository.
3. Record only new observations and amendments; never silently reconstruct approval or overwrite history.
4. Use [progress control](../skills/shards-progress-control/SKILL.md) to avoid identical retries without new evidence.
5. Hand off one bounded next action and a defined stop condition. Do not open a duplicate PR unless separately authorised.

**Completion evidence:** task ID, baseline/current SHA, evidence freshness, unresolved issue IDs and checkpoint location.

### Playbook C: security or regulated-domain request

1. Open [security intake](../skills/shards-sec-intake/SKILL.md) before selecting specialist skills.
2. Identify real owner, system, environment, data class, exclusions and named approver.
3. Select one or two relevant `shards-sec-*` procedures. Generate only a *reference* assurance plan with [security assurance](security-assurance.md).
4. Use least privilege and synthetic data for tests where feasible. An unknown permission or target is **BLOCKED**, not implicitly authorised.
5. Record technical observations with exact target revision, source and limitations; escalate uncertain jurisdiction and regulated obligations.

**Completion evidence:** scoped charter, finding IDs, observations, tested controls, unknowns and owner action.

### Playbook D: curated local execution

1. From a trusted full checkout, run `python scripts/dispatch_skills.py list`.
2. Run `python scripts/dispatch_skills.py plan --skill shards-repository-health` and review the actual plan and `plan_sha256`.
3. Obtain host permission for the **specific** planned effect. If not authorised, finish at **PLAN ONLY**.
4. When authorised, use `python scripts/dispatch_skills.py run --skill shards-repository-health --execute --expect-plan-sha256 <reviewed-digest> --save-receipt` with the same options; observe process exit and receipt.
5. Record the distinction between local dispatcher success and any wider agent/production claims.

The dispatcher is *not* a network A2A service, OS sandbox, cryptographic permit or independent policy engine. See [exact execution contract](skill-dispatch.md).

### Playbook E: evaluate a skill on a real host

1. Pin the skill revision, host/model version, task fixture, permission envelope and criteria.
2. Run matched tasks **with and without** the skill, including an irrelevant/negative trigger, without naming the expected skill in the task prompt.
3. Collect genuine native host traces showing discovery → selection → descriptor opened → procedure applied.
4. Verify outcomes independently; record tokens/time only if measured comparably.
5. Conclude `UNVERIFIED` when traces or negative tests are absent, rather than inferring success from installer output.

See [agent adoption](agent-adoption.md).

## On failure

**STOP / BLOCKED:** unknown scope, denied permission, suspicious source, stale or conflicting evidence, unsupported host, missing live review, or failed security boundary. Report the named blocker and required authorised next step. **REPLAN:** tool fails or an attempt repeats without new information; use another permitted path, not a hidden retry loop. **HOLD:** local validation has passed but a higher gate is still pending.

## Final handoff

Use one brief record, with factual values rather than guessed placeholders:

~~~json
{
  "task_id": "known-task-id-or-null",
  "repository": "OWNER/REPO",
  "base_sha": "observed SHA or null",
  "head_sha": "observed SHA or null",
  "scope": "approved effect and exclusions",
  "selected_skills": [],
  "actions_taken": [],
  "checks": [{"command": "observed command", "exit_code": null, "status": "NOT_RUN"}],
  "evidence": [],
  "review_state": "NOT_VERIFIED",
  "blockers": [],
  "next_authorised_action": "one bounded next action"
}
~~~

This is a **handoff example**, not proof of a performed run. Never insert real secrets or private user data. Resolve the existing task rather than creating extra tasks by default.
