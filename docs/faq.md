# Frequently asked questions

For installation steps, start with the [user guide](user-guide.md). For practical examples, use the [cookbook](cookbook.md).

## What is Shards Skills?

An independently developed library of reusable procedures for AI-assisted engineering, security, research and operations. Each skill describes when to use it, how to approach a task, what to return and how to verify the outcome.

## What is the difference between a skill, an agent and an MCP tool?

A skill provides procedural instructions. An agent interprets instructions and may plan or act using available tools. An MCP tool exposes a capability through the Model Context Protocol. None of these automatically grants permission to perform an action.

Some Shards workflows also have separately reviewed executable adapters; see the [dispatcher guide](skill-dispatch.md).

## Which AI platforms can use Shards Skills?

Platforms that can load the Agent Skills format, accept instruction files, or provide a suitable retrieval mechanism may be able to use selected skills. Installation, discovery, execution and tool access depend on the particular host and account. Consult the [compatibility reference](portable-agent-skills.md) for documented routes and the evidence available for each.

## Can I import skills directly from GitHub?

Yes, where the host supports the repository or individual skill format. Use the host's native importer and select the relevant source. Some hosts require a marketplace manifest rather than a plain skills directory. An import route being available does not mean this repository's layout has been verified with that importer.

**Example — Manus:** Open **Skills → Import from GitHub**, paste the public repository URL into the URL field and select **Import**:

```text
https://github.com/Shards-foundation/shards-skills
```

If your host accepts individual skill-directory URLs, you can also try a specific skill, such as:

```text
https://github.com/Shards-foundation/shards-skills/tree/main/skills/systematic-debugging
```

Select the intended skill if prompted and check that it appears in your skills list. These are real source URLs; successful import depends on the host's supported layout and has not been verified for every importer.

## Can I upload individual skills or ZIP files?

Yes, where the host supports those formats. Use a standalone SKILL.md only when no companion resources are required. Use a compatible ZIP when the skill needs additional files. Some hosts accept one skill per upload; others support collections. The repository's general-purpose exporter currently permits a limited selection of self-contained skills. See the [user guide](user-guide.md#4-upload-a-zip-or-markdown-skill).

## Do I need Python, Node.js or Git?

Not for a native import or upload of a self-contained instruction-only skill. Git and Python 3.11+ are used for the documented local repository checks and utilities; Node.js is needed for the optional Skills CLI installer. Individual workflows may have additional requirements. Check the selected skill and host documentation.

## Do I need Shards MCP or Shards Kernel?

No. Standalone instruction skills do not require either. MCP can provide retrieval or tool access where the relevant capabilities exist. Shards Kernel may be used as a separate governance component in an integration; neither component is an automatic dependency of the skill format.

## Will my agent use a skill automatically?

Possibly, if its host supports native discovery and selection. Other hosts require explicit selection or invocation. Installing a skill does not guarantee it will be discovered or applied. You can ask the agent to use a specific skill and check its actual host evidence.

## Can I use multiple skills together?

Yes, where the host supports it. Select the smallest relevant combination, such as systematic debugging and test-driven development. Resolve conflicting instructions against the authorised task, host policies and existing evidence. More skills do not necessarily improve an outcome.

## Can skills execute commands or access my credentials?

A descriptor is instruction content, not a permission grant. A host may execute bundled scripts or act on instructions using its available tools, so imported skills must be reviewed. Use least privilege and avoid unnecessary credentials or network access. Follow the [security policy](../SECURITY.md) and [rulebook](rulebook.md).

## Why are some skills marked as draft?

Status describes the recorded maturity of a skill, not whether a particular host will load it. A draft may be usable as guidance but should not be treated as independently verified. Static validation and successful retrieval do not certify behaviour, safety or usefulness.

## How do I know an agent actually used a skill?

Check the host's discovery or execution evidence for the selected skill, exact revision, instructions opened and steps applied. Inspect the actual outcome independently. A model's assertion alone is not proof of invocation; metadata ranking is not agent use. See the [adoption guide](agent-adoption.md).

## How do I update an installed skill?

Record the installed revision, review upstream changes and use your host's supported update or re-import process. Keep local customisations and a rollback copy. Verify the active version and run a bounded task after updating. Do not assume an uploaded or copied skill automatically tracks GitHub.

## Can I create or customise my own skills?

Yes. Use the existing descriptors as examples: define a specific trigger, prerequisites, workflow, output contract, verification and failure handling. Preserve licence and attribution requirements. Review changes and test them before using them with consequential tools. See [contributing](../CONTRIBUTING.md).

## Can I use Shards Skills commercially?

The repository's first-party software and documentation are distributed under the [MIT licence](../LICENSE), which permits commercial use, modification and distribution subject to its conditions, including retaining the applicable notices. Third-party material can have separate terms; review the [third-party notices](../THIRD_PARTY_NOTICES.md). The licence does not grant access to paid AI services or external tools.

## How do I contribute or report an issue?

Follow the [contribution guide](../CONTRIBUTING.md). For ordinary issues, provide the skill name, source revision, host, reproduction steps, expected and observed results, and redacted evidence. Use the [security reporting policy](../SECURITY.md) for suspected vulnerabilities; do not post credentials or sensitive security details publicly.

## Where should I go next?

- [User guide](user-guide.md): installation, updates and first use.
- [Cookbook](cookbook.md): practical tasks.
- [Playbook](playbook.md): sequencing and recovery.
- [Rulebook](rulebook.md): permission and evidence boundaries.
