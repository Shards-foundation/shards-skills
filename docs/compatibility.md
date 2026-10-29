# Runtime compatibility and installation

`SKILL.md` is the portable source format. Agent hosts differ in where they discover skills, how metadata is parsed, whether they load scripts, and whether they permit tool use. Compatibility must be tested per host and version; this repository does not claim every skill runs identically on every agent.

## Manual installation

Copy one skill directory, including `SKILL.md` and any adjacent references/scripts, into the host's documented skills directory. Common conventions include:

- Repository-local `.agents/skills/<skill-name>/`
- Claude Code project `.claude/skills/<skill-name>/`
- Other hosts' documented skill directories, after checking their current specification

Do not copy only the Markdown file if a skill depends on companion files.

## Using the Vercel Skills CLI

Where the host supports the Vercel Skills CLI, check its current usage and review the proposed file changes before installing. A typical repository install command is:

```bash
npx skills add Shards-foundation/shards-skills --skill test-driven-development
```

The command requires the GitHub repository to exist and the runtime to have Node.js/npm available. This command has not been executed against the remote repository during bootstrap.

## Compatibility report required for verified status

Record:

- Host and version
- Skill revision / commit SHA
- Install location and method
- Whether metadata parsed correctly
- Positive and negative trigger cases
- Expected output and verification results
- Unsupported tools or environment assumptions
- Security review and approval status

A markdown file that can be read is not equivalent to a skill being behaviourally compatible.
