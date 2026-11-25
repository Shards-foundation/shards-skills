# Shards Skills Cookbook

Practical, small recipes for operators and agents. New or updating users should start with the [user guide](user-guide.md) to choose a host and installation route. Begin with the [README walkthrough](../README.md#start-here-a-first-skill-walkthrough), use [the playbook](playbook.md) for sequencing, and check [the rulebook](rulebook.md) before any action. [`agent-index.yaml`](../agent-index.yaml) provides machine-readable route hints.

**All shell commands below assume a trusted repository checkout and Python 3.11+.** They are *examples to run*, not evidence that they were run in your environment. The `skills/` catalogue contains instructions; it does not itself execute scripts or grant tools.

## Recipe chooser

| Objective | Recipe | Primary descriptor | Expected outcome |
| --- | --- | --- | --- |
| Choose a capability | [Find a skill](#1-find-a-skill-without-executing-it) | `skills/shards-tool-selection/SKILL.md` | Ranked shortlist and rationale |
| Review a PR safely | [PR review](#2-review-a-pr-without-merging-it) | `skills/shards-review-resolution/SKILL.md` | Evidence-backed review verdict |
| Repair a reproducible defect | [Debugging](#3-debug-one-reproducible-defect) | `skills/systematic-debugging/SKILL.md` | Patch plus tested regression |
| Resume interrupted work | [Recovery](#4-resume-an-interrupted-task) | `skills/shards-context-recovery/SKILL.md` | Reconciled checkpoint, one next action |
| Scope a security review | [Security intake](#5-scope-a-security-review) | `skills/shards-sec-intake/SKILL.md` | Authorised boundary and evidence plan |
| Check curated workflows | [Local dispatcher](#6-plan-a-curated-local-check) | `plugins/shards-core/README.md` | Read-only execution plan |
| Use a phone | [GitHub Actions](#7-use-github-actions-from-a-phone) | [Manual workflow guide](manual-skill-runs.md) | GitHub-native summary and receipts |

## 1. Find a skill without executing it

~~~bash
python scripts/search_skills.py --query "Review an interrupted GitHub PR repair and verify changes" --limit 5
python scripts/search_skills.py --skill shards-review-resolution
~~~

Read the JSON score and `reason`; check the chosen descriptor, its `status`, inputs, host requirements and referenced paths. **Expected:** a shortlist and one exact skill descriptor. **If empty:** simplify the query or inspect [discovery guidance](skill-discovery.md); do not invent a match. This finder neither installs nor runs skills.

## 2. Review a PR without merging it

Choose a host that supports Agent Skills and actually has access to the target repository. In the **destination project**, with Node.js 22.20+ and a trusted local Shards Skills checkout:

~~~bash
npm install --ignore-scripts --no-save skills@1.8.1
# Inspect the package and local executable before invoking them.
npx --no-install skills add /path/to/shards-skills --skill code-review shards-review-resolution shards-evidence-verification -a codex --copy -y
npx --no-install skills list
~~~

The downloaded installer must be inspected before execution, and the full trusted checkout must remain visible to the host because selected descriptors reference repository-root resources. Where `python` is unavailable, substitute your Python 3.11+ executable (for example `python3` or Windows `py -3.11`). Verify the host **discovers** the skills. Example agent request:

> Inspect PR #NUMBER on the exact current head SHA. Review changed code and risks; label every test as RUN, NOT RUN or BLOCKED. Return APPROVE, REQUEST CHANGES or BLOCKED, with evidence and unresolved items. Read-only review; do not modify, approve on GitHub, merge or deploy.

**Expected:** head SHA, files inspected, findings with references, test provenance, decision and blockers. This prompt is not an authenticated GitHub review. To publish a formal review, obtain the required permission and verify the actual account/review identity. See [review resolution](../skills/shards-review-resolution/SKILL.md) and [evidence verification](../skills/shards-evidence-verification/SKILL.md).

## 3. Debug one reproducible defect

~~~bash
python scripts/search_skills.py --skill systematic-debugging
python scripts/search_skills.py --skill test-driven-development
~~~

Define the observable failure, a minimal reproducible case, the expected outcome and the in-scope files. Make a small fix on the authorised branch, run a regression test and report the **exact** command, exit code and changed commit SHA. If tests cannot run, label the fix **implemented, not tested**. Descriptors offer procedure; a local host must supply execution and permissions.

## 4. Resume an interrupted task

First read [context recovery](../skills/shards-context-recovery/SKILL.md) and the [operating loop](operating-loop.md). If an existing task record is available locally:

~~~bash
python scripts/operating_ledger.py show --task example-fix
~~~

Replace `example-fix` with the **actual existing task ID**. Compare the recorded revision, branch, PR, failures, accepted criteria and reviewer status with live sources. Preserve the original task contract, note stale evidence and select just **one next authorised action**. Never initialise a replacement ledger merely because the existing one is unavailable.

**Expected:** verified facts, unresolved items, blockers and a fresh checkpoint. **Stop:** live identity or authorisation cannot be reconciled.

## 5. Scope a security review

Read [security intake](../skills/shards-sec-intake/SKILL.md) first. Confirm the asset owner, exact systems, permission level, environment and exclusions, then—only in a trusted checkout—generate a **reference** control plan:

~~~bash
python scripts/security_assurance.py plan --profiles base --system "example-api"
~~~

**Expected:** an assessment charter and control checklist, not a vulnerability scan or security certification. Choose at most one or two additional `shards-sec-*` workflows. Unauthorised scanning, unknown ownership, real credentials and production changes are **BLOCKED**.

## 6. Plan a curated local check

~~~bash
python scripts/dispatch_skills.py list
python scripts/dispatch_skills.py plan --skill shards-repository-health
~~~

**Expected:** a reviewed, read-only plan with an actual `plan_sha256`. If execution is separately authorised in the real host, the operator may pass the *digest from that plan*:

~~~bash
python scripts/dispatch_skills.py run --skill shards-repository-health --execute --expect-plan-sha256 'REPLACE_WITH_REVIEWED_PLAN_SHA256' --save-receipt
~~~

Replace the quoted placeholder with the actual digest from the reviewed plan; the placeholder itself is not valid. The hash is an integrity check, **not** an identity-bound approval or sandbox. Check [dispatcher guidance](skill-dispatch.md).

## 7. Use GitHub Actions from a phone

Open **Shards-foundation/shards-skills → Actions**. Where you have workflow-dispatch permission:

1. Use **Search Shards Skill Catalogue** for a metadata-only shortlist.
2. Use **Portable Agent Skills ZIP** for one of the seven permitted instruction-only skill bundles; download the artifact, extract the **inner ZIP** and upload it only where a host explicitly supports that.
3. Use **Run Curated Shards Skill** for one of seven reviewed local, read-only checks; inspect the summary, exact revision and receipt artifact.

See [installation and portability](portable-agent-skills.md) and [manual Action runs](manual-skill-runs.md). These workflows cannot install skills into a remote chat account, perform network A2A, or create a general-purpose autonomous agent.

## Verify local repository quality

Already have a checkout? Navigate to its root and skip the clone step. For a new checkout only, run from a parent directory:

~~~bash
git clone https://github.com/Shards-foundation/shards-skills.git && cd shards-skills
~~~

Existing users should navigate to the root of their existing checkout instead. Do not clone inside it. Record the revision and Python version:

~~~bash
git rev-parse HEAD; git status --short; python --version;
~~~

Run each check from the repository root in a compatible Python 3.11+ environment. These POSIX shell examples print each exit status immediately; record every result, not just the final shell status. Substitute your Python executable if needed:

~~~bash
python scripts/validate_skills.py; printf 'check 1 exit: %s\n' "$?";
python scripts/security_lint.py; printf 'check 2 exit: %s\n' "$?";
python scripts/agent_adoption_eval.py; printf 'check 3 exit: %s\n' "$?";
python -m unittest discover -s tests -v; printf 'check 4 exit: %s\n' "$?";
~~~

Some restricted environments (including Android/Termux) lack required filesystem operations. Report those limitations rather than bypassing safeguards. See the [user guide](user-guide.md#9-optional-verify-the-repository-locally).

Record **which** commands really ran, their exit status, the checkout revision and unverified areas. Synthetic retrieval success is not real host performance. For tested adoption, use [host evidence stages](agent-adoption.md).

## Failure and reporting contract

Return a consistent handoff record using the [playbook's exact field names](playbook.md#final-handoff): `task_id`, `repository`, `base_sha`, `head_sha`, `scope`, `selected_skills`, `actions_taken`, `checks`, `evidence`, `review_state`, `blockers`, `next_authorised_action`. Do not invent a receipt, deployment, independent approval or observed benefit. Use the [playbook](playbook.md#final-handoff) for a concise handoff.
