---
name: shards-a2a-authority-preflight
description: "Use before delegating a material cross-agent task to inventory each actor's actual read, edit, execute, push, PR, review, merge and deployment capabilities; reconcile scoped human approval, host access, missing connectors and policy gates; produce an evidence-based hold or handoff receipt."
license: MIT
---

# Shards A2A Authority Preflight

**Purpose:** find the least-privileged *viable* route for a task before dispatch. This is a repeatable, read-only discovery and handoff workflow. It does **not** authenticate agents, mint permits, modify permissions, execute work or certify access. A structured receipt is **not** a permission grant.

**Trigger:** a task must pass between agents, hosts or permission domains; an executor reports missing GitHub/MCP/CLI access; roles for edit/push/review/merge are unclear; a reviewer must verify whether a delegated step is within scope. Do not invoke for ordinary factual questions or trivial single-agent edits without a handoff.

**Composition:** `shards-a2a-harness` runs fixed local read-only checks; `shards-agent-handoff` saves a sanitised checkpoint; `shards-execution-contract` (if present/approved) handles the broader intent-to-evidence plan. This skill is specifically the **actor × action × effective authority** preflight. It never automatically calls those skills.

## Preconditions

- Know the delegator's requested objective, target repository or resource, exact revision or its explicitly unresolved state, scope and acceptance criteria. If the target is ambiguous, use read-only discovery and **HOLD** until it is resolved.
- Identify task roles: delegator, coordinator, executor, integrator/publisher, independent reviewer and merge/production decision maker. A person or agent may hold several roles except that independent review must be independent of execution and publication.
- Inspect *this session's* host tool list, identity and connector status. Do not infer access from another agent's capabilities, earlier conversations, a plugin being installed or a `SKILL.md` file.
- Do not read, print, request, transfer or test raw tokens/keys. Only capture nonsecret credential **presence/absence** and verified capability outcomes when already safely exposed by the host.

## Workflow

1. **Frame the exact task.** Preserve the original goal, scope, prohibited effects and current repo/branch/40-character SHA. Record unknown target or uncertain revision as a blocker, not a guess. Check the actual HEAD and concurrent work before any later write.
2. **Map actors and accountability.** Name one owner for each proposed action. Distinguish task owner (chooses intent), executor (edits), integrator (pushes/opens PR), independent reviewer (reviews formally), and merge decider (authorises merge). Never equate repository write access with permission to merge or approve; do not self-review.
3. **Inventory only needed actions.** Classify `repo.read`, `git.fetch`, `pr.read`, `ci.read`, `source.edit`, `git.commit`, `git.pull` (local working-tree mutation), `tests.run`, `git.push`, `pr.create`, `pr.comment`, `pr.approve`, `pr.merge`, `deployment.run` and `credentials.rotate`. Do not enumerate every connected service for a small task.
4. **Separate three independent gates per action.** (a) *Scoped human/operator delegation*: is this effect within the original task? (b) *Effective current host access*: is the necessary tool/connector actually usable by this actor? (c) *Destination policy*: branch protections, review identity, environment constraints and permit restrictions if relevant. A passing gate does not imply the others pass.
5. **Discover safely.** Prefer introspection and permitted read-only observations: actor identity, advertised tools/scopes, repository metadata, `git ls-remote`, PR/check metadata, available local interpreter, and host policy visibility. `git status`/local file access do **not** prove remote push. A GitHub `write` permission label alone does **not** establish protected-branch merge rights. An API 401/403 may mean inaccessible evidence, not that a control is disabled. Never create a PR, push, approve, deploy, use a credential or run unreviewed code *as an access probe*.
6. **Locate the bottleneck.** For each needed action record `GRANTED/UNKNOWN/DENIED` scoped delegation, `OBSERVED/UNKNOWN/DENIED` effective access, `VERIFIED/UNKNOWN/DENIED/NOT_APPLICABLE` policy and nonsecret evidence. Name missing connector, missing credential, unavailable tool, policy uncertainty or denied permission **only if established**. Distinguish a known denial from `NOT_VERIFIED`.
7. **Choose the minimal continuation.** If Claude can author locally but cannot push, it may return an exact commit/file checksum; an independently authorised integrator can publish, subject to fresh checks. A reviewer may submit a *formal* GitHub `APPROVE` only after reviewing the current SHA and only with actual GitHub privileges and scoped authority. An ordinary comment is not approval. Never auto-transfer tokens or automatically substitute another actor.
8. **Produce a bounded receipt.** Use [contract fields](references/contract.md) and the [synthetic example](references/example-readonly.json). Run the read-only validator against the sanitised JSON. `CLAIMS_COMPLETE` means the *reported metadata* is structurally sufficient; it is **not** an execution permit, proven remote authority, or verified reviewer approval.
9. **Recheck at action time and hand off.** The receiver independently confirms identity, branch/SHA, tool access and actual policy before any effect. On revision drift, capability loss, concurrent write, stale evidence or unresolved review, HOLD and name the next responsible actor. For ongoing work use `shards-agent-handoff` separately; do not silently launch downstream tasks.

## Execution

With a trusted full checkout, Python 3.11+ and an explicitly provided **sanitised** local JSON record, the validator performs no network requests or mutations:

```bash
python plugins/shards-core/skills/shards-a2a-authority-preflight/scripts/validate.py validate --input /path/to/sanitised-authority.json
```

The curated dispatcher accepts only an existing checkpoint under `.shards/state/*.json` (local read only):

```bash
python scripts/dispatch_skills.py plan --skill shards-a2a-authority-preflight --input-file .shards/state/authority.json
# Review the pinned plan SHA and trusted script. Then, with host permission for local read execution:
python scripts/dispatch_skills.py run --skill shards-a2a-authority-preflight --input-file .shards/state/authority.json --execute --expect-plan-sha256 <digest-from-plan>
```

The direct validator exits **0** for complete claims, **1** for `HOLD` and **2** for `INVALID`. The dispatcher exits **0** for `pass` and **1** for both `hold` and `fail`. Use `observation.status` and `observation.exit_code` to distinguish an unresolved gate from invalid input. The dispatch receipt carries the complete bounded validator result in `observation.report`; the diagnostic tails may be truncated. Where Python or shell access is unavailable, perform the procedure manually and label validation **NOT_EXECUTED**.

## Output contract

The handoff summary includes the objective, task owner, pinned revision, each action's scope permission, access and policy, and the smallest permissible next action. Take the owner and status claims from the task instructions and sanitised inventory.

The JSON validator reports the task ID and target revision, each action's actor, effect, claim status and matched evidence IDs, named blockers and their escalation targets, and `CLAIMS_COMPLETE`, `HOLD` or `INVALID`. Retrieve the underlying evidence from the inventory before drawing conclusions about live access.

Always distinguish **operator assertion**, **tool-observed access**, **host-enforced permission**, and **independent reviewer evidence**. No assertion alone makes an action authorised. Do not put credential material, raw environment variables, private chat transcripts or customer data in the receipt.

## Verification

Run `python -m unittest discover -s tests -p 'test_a2a_authority_preflight.py' -v` and `python scripts/verify_plugins.py --check` after changing this skill or its validator. Verify `HOLD` for missing connector/permission, stale revision, unknown policy or missing evidence; reject same-agent reviewer, out-of-scope target, misassigned merge/approval, malformed JSON and embedded secret. Check exit codes and confirm the validator makes no network or write calls.

## Failure handling

Unknown access is **not** assumed denied or granted. Missing credentials are never copied from another agent. Escalate to the named task coordinator or authorised operator with an exact missing capability and a safe next action. Inaccessible policy stays `NOT_VERIFIED`; newly changed HEAD makes earlier approvals and checks stale. Do not retry non-idempotent external effects after an uncertain result. If receipt creation fails, pass a minimal sanitised blocker summary and stop.

## Trust boundary

This skill and validator check only **self-reported metadata structure and consistency**. They cannot independently authenticate delegation, prove a GitHub branch permission, enforce Shards-Kernel permits, certify A2A transport or actually run a remote agent. Real authority remains with the operator, host/tool permissions, destination policy and relevant trusted enforcement systems.
