---
name: shards-agent-handoff
description: "Use when transferring an interrupted or partially completed task to another AI agent or session: validate a portable, evidence-linked, authority-scoped recovery checkpoint without granting permissions."
license: MIT
compatibility: "Python 3.11+ for optional offline schema validator; advisory handoff possible without execution."
status: candidate
---
# Shards Agent Handoff — portable checkpoint v1

## Trigger
A change of executor, model, host, conversation or context; a blocked side-effect or incomplete delivery; a request to preserve results so another agent can resume. **Not** a grant of permission or an instruction to continue automatically.

## Workflow
1. **ACK / scope:** record `task_id`, original goal, owner and executing actor; distinguish delegated actions from actual host permissions. Do not infer access from skill text or another agent's credentials.
2. **Gather minimal durable state:** original scope and blockers; exact target repository and pinned Git SHA(s); execution versus adjudication versus export state; next responsible owner/action. A multi-revision task may have multiple targets with `branch: null`. If a revision is unknown, use `commit_sha: null`, `revision_status: UNKNOWN`, and `HOLD`.
3. **Record typed evidence:** unique receipt ID, claim, actor, operation, applicable SHA, observed time, locator (`github_commit`, `github_check_run`, `github_review`, `local_artifact`, `synthetic`, `unavailable`), optional SHA-256. `REPORTED` is not `INDEPENDENTLY_VERIFIED`; a digest doesn't prove that the data is true or live.
4. **Sanitise:** remove secrets, personal data and internal tokens. Never transfer raw private logs, credentials or connection URLs containing authentication.
5. **Validate offline when permitted:** `python scripts/validate.py --input checkpoint.json --output validated.json` from this skill directory. Exit 0 means **schema valid only**, and exit 2 means input or output was blocked. Use a canonical output path in a host-protected directory on a filesystem that supports hard links. The validator publishes the complete output exclusively and refuses overwrites.
6. **Receiver re-fetches evidence:** verify the target revision against the authoritative source, then verify review/check/permission status when the decision requires it. Refuse to promote a synthetic or unresolvable locator to real-world authority. Use `HOLD` when evidence cannot be retrieved.
7. **Stop:** return one next authorised action, owner, missing dependencies and validated evidence references. Do not automatically execute the continuation.

## Input contract
The required versioned envelope is documented by `scripts/validate.py` and illustrated in the packaged `fixtures/` sample supplied with the phase-3 bundle. Keys include `schema_version`, `task_id`, `goal`, `task_owner`, `executor`, `observed_at`, `authority {basis, allowed, prohibited}`, `targets [{repository, branch, commit_sha, revision_status}]`, `progress {executed, adjudicated, exported, pending}`, `evidence []`, `blockers []`, and `next {owner, action, decision, evidence_required}`.

## Output contract
Preserve the **complete input checkpoint**, plus `checkpoint_sha256` and `validation` describing checks that were performed. The validator never deletes unknown task metadata; its `schema_valid` is deliberately separate from `external_evidence_verified`, `authority_verified`, and `execution_authorised` (all false). `CLOSED` remains a claim until the receiver independently verifies the closure gate.

## Negative testing
Reject malformed SHA, duplicate evidence ID, empty evidence descriptions, false independent verification with synthetic locator, unknown revision paired with CONTINUE, missing actor, secret patterns, overwrites and unsafe timestamp. Preserve unknown but non-sensitive fields without promoting them to verified authority.

## Safety
Do not use a checkpoint as an approval, permit, signature, runtime sandbox, proof of production state or substitute for a live review. Local validation has no GitHub/network access. This is a **candidate hardened variant** of the Shards first-party handoff workflow, not the existing released dispatcher.
