# Install Shards Skills across AI platforms

**Distribution does not prove usefulness.** The Agent Skills specification defines a
portable `SKILL.md` package, not an authentication method, MCP server, remote tool
executor, universal permissions model or guarantee that an agent will invoke it.

The [Agent Skills specification](https://agentskills.io/specification.md)
and the [Skills CLI agent list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)
describe the shared format and supported installer destinations.

## Install from a trusted checkout

Use the existing Skills CLI with Node.js 22.20 or later. The first `npx` use needs network access to fetch the pinned CLI. With the CLI already installed locally, replace `npx skills@1.8.1` with its binary path for an offline install from the checkout. Run these commands in
the destination project. The examples list available skills, copy one skill, and
copy a small PR-review collection into a Codex project.

```bash
npx skills@1.8.1 add /path/to/shards-skills --list
npx skills@1.8.1 add /path/to/shards-skills --skill systematic-debugging -a codex --copy -y
npx skills@1.8.1 add /path/to/shards-skills --skill code-review shards-review-resolution shards-evidence-verification -a codex --copy -y
npx skills@1.8.1 list
```

You can also copy only the selected directories into the host's project
skills directory. Include companion files and keep a trusted full checkout
available when the descriptor references repository-level scripts. Pin the
source to a reviewed Git revision for reproducibility.

Codex and OpenHands can read project skills from an existing `.agents/skills/`
directory. Opening the Shards checkout exposes its four native candidates
without a separate installation step. The rest of the catalogue can be indexed
locally with the [finder](skill-discovery.md) before choosing what to copy.
Curated Shards Core workflows have a [separate plugin and dispatcher](agent-runtime.md).

## Target compatibility and boundaries

Installer agent identifiers below come from the
[official supported-agents list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).
A listed target means a documented installation target, **not** that Shards
has obtained real host execution evidence or access to that user's account.

| User target | Supported distribution route | Actual boundary |
| --- | --- | --- |
| Codex | `-a codex`, project `.agents/skills/` | CLI/IDE/app local skills; not automatic ChatGPT account installation |
| OpenHands | Project `.agents/skills/` using the [project loader](https://docs.openhands.dev/overview/skills) | SDK discovery verified offline; agent invocation untested |
| OpenCode | `-a opencode`, project `.agents/skills/` | Installer destination checked; native discovery untested |
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

## Observed compatibility

Skills CLI 1.8.1 listed 60 catalogue skills and four native candidates from a
local checkout with networking disabled. It copied a single descriptor to
`.agents/skills/` for Codex, Cursor and OpenCode, and to `.claude/skills/`
for Claude Code. The copies match the source bytes. It also installed the
three selected PR-review skills in a separate Codex project.

Codex CLI 0.172.0-alpha.2 listed the single skill and the three-skill collection
through its native `skills/list` API. The OpenHands SDK 1.63.1 project loader
found the same three-skill collection. Both checks ran offline. Claude Code,
Cursor and OpenCode were checked at the installer level. Other rows above
describe documented routes. Agent invocation and outcome improvements remain
unverified for this migration.

## Mobile-friendly single-skill ZIP for upload-based clients

The **Portable Agent Skills ZIP** Action is available for manually requested exports:

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
Use the [adoption fixtures](agent-adoption.md) and the [paired host checker](host-ab-evaluation.md) to record higher stages.
