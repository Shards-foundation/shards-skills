# Install Shards Skills across AI platforms

**Distribution does not prove usefulness.** The Agent Skills specification defines a
portable `SKILL.md` package, not an authentication method, MCP server, remote tool
executor, universal permissions model or guarantee that an agent will invoke it.

Sources: [Agent Skills specification](https://agentskills.io/specification.md),
[client integration](https://agentskills.io/client-implementation/adding-skills-support.md),
and [Vercel Skills installer/agent paths](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).

## The quickest supported installation

Use the established `skills` installer (Node.js 22.20+, Git and network access).
Select one or a few skills from the first-party library. A listing establishes availability. Execution requires separate host permission.

```bash
# List discoverable skills before trusting any of them.
npx skills add Shards-foundation/shards-skills --list

# Install a known instruction-only first-party skill into 11 supported agent
# targets in the *current project*. Each name targets a specific agent product.
npx skills add https://github.com/Shards-foundation/shards-skills/tree/main/skills/systematic-debugging \
  -a codex -a claude-code -a cursor -a minimax-code -a mistral-vibe \
  -a grok -a replit -a openclaw -a hermes-agent -a kimi-code-cli \
  -a devin --copy -y

# Confirm the actual installation and inspect the skill content.
npx skills list
npx skills check
```

For a single client, e.g. Codex: `npx skills add Shards-foundation/shards-skills --skill problem-framing -a codex --copy -y`.
The official CLI also supports `-g` for user-wide installation, `skills update`
and lock-file content hashes. Prefer pinning the source to a reviewed commit
when distributing into regulated or production environments. Native clients
must still be restarted/refreshed where their skill discovery requires it.

Prefer an explicit selection matched to the task. Some skills need access to the full checkout.

## Target compatibility and boundaries

Installer agent identifiers below come from the
[official supported-agents list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).
A listed target means a documented installation target, **not** that Shards
has obtained real host execution evidence or access to that user's account.

| User target | Supported distribution route | Actual boundary |
| --- | --- | --- |
| Codex | `-a codex`, project `.agents/skills/` | CLI/IDE/app local skills; not automatic ChatGPT account installation |
| Claude Code | `-a claude-code`, project `.claude/skills/` | Claude Code, not the Claude web account |
| Claude web/app | One skill ZIP, where custom skill uploads are available | Manual account UI upload; no automatic account access |
| Cursor | `-a cursor`, project `.agents/skills/` | Project/workspace availability varies |
| MiniMax Code | `-a minimax-code`, project `.minimax/skills/` | MiniMax Code, not every MiniMax chat product |
| Mistral Vibe | `-a mistral-vibe`, project `.vibe/skills/` | Vibe CLI, not all Le Chat surfaces |
| Grok Build | `-a grok`, project `.grok/skills/` | Grok Build, not Grok consumer chat |
| Replit | `-a replit`, project `.agents/skills/` | Requires access to that project/environment |
| OpenClaw | `-a openclaw`, project `skills/` | Discover via `openclaw skills list`; host tools still gated |
| Hermes Agent | `-a hermes-agent`, project `.hermes/skills/` | Must verify Hermes reads the installed skill |
| Kimi Code CLI | `-a kimi-code-cli`, project `.agents/skills/` | Kimi coding client, not all Kimi chat products |
| Devin for Terminal | `-a devin`, project `.devin/skills/` | Devin Terminal, not every Devin cloud agent |
| Vercel | `npx skills` from vercel-labs, or deploy app with installed skills | Vercel hosting alone does not activate skills |
| Genspark | Manual file/ZIP import only if the host exposes it | Native skill discovery not independently verified here |
| Manus | Self-contained ZIP/import or an explicit runtime adapter | Earlier package imports can miss repo-level references |
| Lovable | Repo/project integration subject to its own product support | No verified native SKILL.md import route here |
| NVIDIA Muse | Depends on the actual NVIDIA runtime/product | Model access alone is not a skills host |
| LangChain / LangGraph | App-defined loader implementing discovery/activation | Framework integration must be coded and tested |
| CrewAI | App-defined skill wrapper/tool integration | Framework is not automatically a SKILL.md client |

Do not manufacture platform-specific plugin manifests or claim a platform
supports features that have not been observed. Hosts with no file import and no
skills interface require a separate adapter; an MCP server can expose tools
but does not itself install instruction skills into every model.

## Mobile-friendly single-skill ZIP for upload-based clients

Once the **Portable Agent Skills ZIP** Action is merged onto the default branch:

1. Open **GitHub → Shards-foundation/shards-skills → Actions → Portable Agent Skills ZIP**.
2. Choose **Run workflow**, select a permitted first-party skill, and run it.
3. Download the `shards-portable-skill` artifact. GitHub wraps the generated
   `<skill>.zip` and `<skill>.receipt.json` into an outer artifact archive.
4. Extract the **inner skill ZIP**. Upload that exact ZIP to a host that
   supports skill-file uploads. Never provide credentials to the ZIP.
5. Verify installation by listing available skills on the host, explicitly
   invoking the skill, and recording the real output and tool traces.

Seven structurally checked instruction-only skills are exposed in the Action:
`problem-framing`, `implementation-planning`, `systematic-debugging`,
`test-driven-development`, `code-review`, `secure-code-review`,
`evidence-based-research`. This is deliberately narrower than the repository's
larger first-party catalogue.

From a local checkout with Python 3.11+:

```bash
python scripts/package_agent_skill.py --list
python scripts/package_agent_skill.py --skill systematic-debugging --check
python scripts/package_agent_skill.py --skill systematic-debugging
python -m unittest discover -s tests -p 'test_portable_skill_export.py' -v
```

The bundler does **not** execute skill code or run installers. It validates
required frontmatter, matching names, local files, Markdown links and obvious
referenced scripts, forbids symlinks/out-of-package links, limits file count and uncompressed package bytes,
emits deterministic ZIP bytes and records per-file and archive SHA-256 hashes.
Ambiguous links or missing resources are **BLOCKED**, not silently omitted.
This is a bounded static test; it cannot prove that every implicit runtime
dependency has been packaged.

Many current `shards-sec-*` skills, executable adapters and curated workflows still
refer to repo-root scripts, evaluation fixtures or the plugin dispatcher.
The export allowlist is deliberately limited to seven instruction-only skills.
Other skills remain **blocked from ZIP export**, even when their local Markdown
passes a structural audit, until every transitive runtime dependency is packaged
and tested in a clean extracted environment. This
is especially important for Manus and Claude upload workflows.

## Acceptance gates for each platform

- **PACKAGE:** syntax, links, self-contained files and reproducible hash pass.
- **INSTALLED:** host-specific path or account upload is observed, with exact version.
- **DISCOVERED:** native skill listing or host transcript shows the skill by name.
- **TRIGGERED:** relevant test task loads the skill; irrelevant task does not.
- **USEFUL:** matched with/without-skill tasks show real output-quality improvements.
- **SAFE:** tests cover missing tools, untrusted inputs, denied actions and no credential leaks.

A static ZIP receipt is only **PACKAGE**, not **INSTALLED** or **USEFUL**.
Record platform, host/model version, skill commit, task fixture, actual output,
negative controls, tool permissions and reviewer decision for each higher gate.
Use existing `docs/agent-adoption.md` and pending A/B evaluation work for the
evidence-gated host comparisons rather than duplicating their evaluators.
