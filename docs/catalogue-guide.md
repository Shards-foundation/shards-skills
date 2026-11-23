# Skill catalogue

`skills/<name>/SKILL.md` is the source for the first-party catalogue. Each
descriptor declares a canonical name and task-oriented description. The
generator also reads category, status, `license`, version and declared `compatibility` when available.
Add a matching entry to [the discovery profiles](../catalogue/discovery.json).
Use a few concrete task phrases drawn from the skill's actual workflow.
Add exclusions only for clear misroutes. The profiles live outside skill
frontmatter so hosts continue to receive the existing metadata format.
Keep detailed inputs, outputs, prerequisites and verification in the
descriptor where the reader can inspect them after selection.

Run `python scripts/build_catalogue.py` after changing catalogue metadata.
`python scripts/catalogue_sync.py --check` compares the checked-in index with
the descriptors. The explicit repair command only reconciles catalogue JSON.
Run the descriptor validator and security lint before distributing a skill.

The separately maintained [Shards Core plugin](../plugins/shards-core/README.md)
owns the curated dispatcher entries. Native host candidates under
`.agents/skills/` have distinct names and separate compatibility evidence.
See the [discovery guide](skill-discovery.md) for task queries.

For external packages, use the local [static audit](../plugins/shards-core/skills/shards-skill-audit/SKILL.md).
The [historical source index](../third_party/SOURCES.md) preserves provenance for
the retired collection.
