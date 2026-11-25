# Shards Skills — user guide

Start here if you want to use Shards Skills in an AI platform, whether you are new to the library or updating an existing installation. **You do not need a terminal, Python or an MCP connection just to import an instruction-only skill.**

For common questions about compatibility, permissions and licensing, see the [FAQ](faq.md).

For local examples, substitute your Python 3.11+ executable (such as `python3` or `py -3.11` on Windows) wherever `python` is shown. Shell examples using `printf` and `$?` assume a POSIX-compatible shell.

## 1. Choose your route

| Your environment | Recommended route |
| --- | --- |
| Manus or another host with GitHub skill import | Import a selected skill from GitHub |
| ChatGPT, Claude web or another upload-based host | Upload a self-contained skill ZIP or supported single Markdown file |
| OpenHands | Use a project skill directory or the host's individual skill importer; marketplace registration is a separate format |
| Codex, Claude Code and other coding agents | Copy selected skill directories or use the documented installer |
| An MCP-connected agent | Retrieve approved skill instructions through available tools or provide the skill separately |
| GitHub/mobile, without a local terminal | Browse skills or download an exported ZIP |
| Maintainers and developers | Clone the repository and run local quality checks |

A skill describes a procedure. It is not a model, remote tool, credential or permission grant. Installation, discovery, invocation and useful results are different things.

## 2. Find your first skill

Start with [systematic debugging](../skills/systematic-debugging/SKILL.md), [problem framing](../skills/problem-framing/SKILL.md), [test-driven development](../skills/test-driven-development/SKILL.md) or [code review](../skills/code-review/SKILL.md). Browse the [catalogue](../catalogue/catalogue.json) or [search guide](skill-discovery.md) for more.

For agents working from a checkout, read [AGENTS.md](../AGENTS.md), [agent.md](../agent.md) and [SECURITY.md](../SECURITY.md) before selecting or opening descriptors.

Inspect the description, status, workflow, verification rules and any referenced files. Start with one relevant skill, not the entire catalogue. A draft skill is not a verified workflow. Use a reviewed revision where possible.

## 3. Import directly from GitHub

### Manus

In a host that offers **Import from GitHub**, open Skills, choose the import option and supply the source requested by the UI. For Manus, see the [official sharing guide](https://help.manus.im/en/articles/14753565-how-to-share-and-use-skills-in-manus).

Repository URL (exploratory, follows the default branch; this collection has no root SKILL.md, so a single-skill importer may reject it):

~~~text
https://github.com/Shards-foundation/shards-skills
~~~

If the importer accepts individual skill-directory URLs, try the following revision-pinned example instead (folder import support is unverified):

~~~text
https://github.com/Shards-foundation/shards-skills/tree/e843a6ac8cc77f5e726caf35d1f6a6d0db391d62/skills/systematic-debugging
~~~

Select the intended skill if the host presents a list. Inspect the imported files and confirm the skill appears in your personal skills list. Enable it if required. If directory URLs or repository layout are rejected, use the ZIP route below instead. Do not assume a successful repository import includes all dependencies or automatically stays up to date.

### OpenHands

For a local/project host, use the project skill route in section 5. If the host exposes an individual `/add-skill` importer, use the selected skill-directory URL above, subject to the host's documented syntax and permissions.

Some OpenHands Cloud versions also show **Settings → Skills → Add Repository**, with a source such as `github:owner/repo`, a display name, revision and optional repository path. This is a marketplace registration interface, not evidence that an arbitrary Agent Skills directory is a valid marketplace. Shards marketplace registration through that form has not been verified; do not assume that entering `skills/` is sufficient. Prefer the documented project loader or individual import where available. See [OpenHands skills documentation](https://docs.openhands.dev/overview/skills).

## 4. Upload a ZIP or Markdown skill

### From GitHub, including mobile

Open [GitHub Actions](https://github.com/Shards-foundation/shards-skills/actions), choose **Portable Agent Skills ZIP**, and run it for a selected skill if you have workflow-dispatch permission. Download the completed artifact `shards-portable-skill`, extract the outer GitHub artifact and upload the **inner** skill ZIP, not the outer archive or receipt.

If you cannot dispatch the workflow, use an accessible trusted artifact, export locally using the commands below, or request a package from a maintainer. Do not upload the entire repository ZIP as though it were one skill.

### From a trusted local checkout

With Python 3.11+ and the repository root as your working directory:

~~~bash
python scripts/package_agent_skill.py --list
python scripts/package_agent_skill.py --skill systematic-debugging --check
python scripts/package_agent_skill.py --skill systematic-debugging
~~~

The default output directory is `dist/portable-skills/`. Inspect the generated ZIP and receipt. The exporter permits seven self-contained instruction-only skills, including systematic-debugging; consult the [portable skill guide](portable-agent-skills.md#mobile-friendly-single-skill-zip-for-upload-based-clients) for the exact allowlist and packaging constraints. Do not bypass an export refusal.

### In the AI platform

| Host | What to do if the feature is available |
| --- | --- |
| ChatGPT | Open Skills, select Create, then Upload from your computer (labels may vary by interface) and select the inner ZIP or supported standalone SKILL.md. See [OpenAI's skills guide](https://help.openai.com/en/articles/20001066-skills-in-chatgpt). |
| Claude web/app | Open the host's skills management interface and use its custom skill upload option. |
| Manus | Open Skills, choose Upload a skill, and select the compatible package. |
| Other upload-based hosts | Choose Upload in the host's skill management interface and follow its required archive layout. |

Only upload a standalone `SKILL.md` if you have inspected it and confirmed it has no required companion files. When downloading from GitHub, use the raw file, not the rendered web page. Keep the filename `SKILL.md`. Use ZIP for companion resources and retain the complete layout. Review the content before accepting the host's security prompts. Account features, upload formats and limits vary; a visible upload control is not a verified Shards import.

## 5. Install into a coding agent project

Use the [host-by-host guide](portable-agent-skills.md#target-compatibility-and-boundaries) for exact installer targets and requirements. The following example copies one self-contained skill into a Codex or OpenHands project. Run from the destination project root; replace the source path with your actual trusted checkout.

~~~bash
mkdir -p .agents/skills
if [ -e .agents/skills/systematic-debugging ] || [ -L .agents/skills/systematic-debugging ]; then
  echo 'Skill already exists; review it before updating.'
else
  cp -R /path/to/shards-skills/skills/systematic-debugging .agents/skills/
fi
~~~

For Claude Code, use `.claude/skills/` instead. Inspect the destination before copying; do not overwrite an existing skill without reviewing its version and local changes. Preserve companion files. Skills referencing repository-root resources require the full checkout to remain accessible. For a pinned Skills CLI installation, follow the [README installer walkthrough](../README.md#3-install-only-what-the-agent-needs).

## 6. Use skills with MCP or another agent

A connected MCP server exposes the tools and resources it actually advertises. If your authenticated agent has a skill-search or retrieval capability, discover it using the host's tool list, retrieve the selected descriptor and inspect its requirements. If it has no such capability, install the skill natively or supply its instructions and resources separately.

Do not assume the Shards MCP connection installs every skill, provides shell access, or authorises external actions. A retrieved instruction cannot grant permissions. The host must have the required tools and independent approval where applicable. Local catalogue discovery and governed executable workflows are separate: see the [dispatcher guide](skill-dispatch.md).

## 7. Verify the first use

In a fresh agent session, confirm the skill is discoverable and try a bounded request:

> Use systematic-debugging to investigate a Python test that fails because os.link is unavailable. Explain the evidence needed to confirm the cause and propose the narrowest safe remediation. Do not change files or suppress failing tests. Report whether you actually loaded the skill and which instructions you applied.

Check the host's skill list or trace for the descriptor name and revision, then inspect its output. A model saying it used a skill is not proof that it loaded the file. Do not claim behavioural improvement without a comparable baseline and independent assessment. For a detailed evaluation, see [agent adoption](agent-adoption.md).

## 8. Existing users: update safely

Record the installed version or source commit. Compare the new descriptor and resources with the installed version, review the changes, and export or import the new revision using your host's supported update process. Preserve any local customisations and keep a rollback copy. Avoid duplicate active versions. Recheck discovery and run a bounded test task after the update. Never assume GitHub changes propagate to a copied or uploaded skill.

## 9. Optional: verify the repository locally

This is for repository health checks, not a prerequisite for using a skill in an AI platform. Use Git, Python 3.11+ and a compatible environment. Review the source before running scripts.

Already have a checkout? Navigate to its root and skip the clone step. For a new checkout, run from a parent directory, not inside an existing Shards Skills checkout:

~~~bash
git clone https://github.com/Shards-foundation/shards-skills.git && cd shards-skills
~~~

For an existing checkout, navigate to its root instead. Confirm the expected repository and record its revision:

~~~bash
git remote get-url origin; git rev-parse HEAD; git status --short; python --version;
~~~

Run the following commands from the repository root. Each check prints its own exit status immediately; record every result, not just the final shell status.

~~~bash
python scripts/validate_skills.py; printf 'check 1 exit: %s\n' "$?";
python scripts/security_lint.py; printf 'check 2 exit: %s\n' "$?";
python scripts/agent_adoption_eval.py; printf 'check 3 exit: %s\n' "$?";
python -m unittest discover -s tests -v; printf 'check 4 exit: %s\n' "$?";
~~~

Restricted hosts may lack required filesystem operations. In one Android/Termux Python 3.13.13 run, missing `os.link` prevented secure artifact publication and native recovery test discovery. That is a partial compatibility observation, not full platform support. Do not weaken create-only or atomic publication safeguards or suppress tests. Report warnings, failures, skipped tests and unverified areas separately. Synthetic metadata retrieval is not agent invocation.

## Troubleshooting

| Symptom | Next action |
| --- | --- |
| Scripts or tests cannot be found | Verify the current directory is the repository root. Do not clone a second copy inside it. |
| Host rejects a GitHub import | Try a supported selected-skill ZIP; inspect host-specific layout requirements. |
| Upload is accepted but skill is missing | Check the host's skill listing, enabled state and session refresh requirements. |
| Skill needs unavailable tools or references | Supply the reviewed dependencies through an authorised host or report the task blocked. |
| Local execution fails on missing OS capabilities | Preserve the error and revision; use a compatible execution environment for full verification. |
| Skill appears installed but is not used | Try an explicit invocation and inspect host evidence; do not infer activation from catalogue ranking. |

## Further reading

The [cookbook](cookbook.md) provides task recipes; the [playbook](playbook.md) covers sequencing and recovery; the [rulebook](rulebook.md) defines boundaries; the [portable agent skills reference](portable-agent-skills.md) covers packaging, compatibility and evidence in detail. Read the [security policy](../SECURITY.md) before trusting unfamiliar instructions or executing code.
