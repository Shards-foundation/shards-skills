# Upstream provenance / quarantine record

- Source: https://github.com/rebelytics/one-skill-to-rule-them-all
- Pinned revision: ba696b2c2673be959dcd4a1dbdbc92085df8b41a
- Original path: repository root
- Reported upstream licence: CC BY 4.0
- Licence notice: third_party/licenses/rebelytics-observer/LICENSE in the Shards repository
- Local status: review; non-executable quarantine placeholder, not an upstream copy.

Rationale: an erroneous mode-160000 Git link occupied this skill directory but no .gitmodules file existed, preventing normal checkout, catalogue validation and clean Actions teardown. Replacing the invalid link with a clear descriptor preserves the catalogue entry and provenance while deliberately not trusting or installing the original source. Restoration of the full upstream skill requires a separate import, review and compatibility test.
