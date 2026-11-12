# Security frameworks and jurisdiction evidence registry

**Research snapshot: 12 November 2026, UTC.** These links identify **external authorities**, not certification of the Shards workflows. Check official sources again before providing legal or regulatory guidance. Any date or deadline may change with legislation or regulator guidance. Include the exact source version and consultation timestamp in a case report.

## Defensive standards and technical guidance

| Source / edition | Primary source | Application in Shards |
| --- | --- | --- |
| NIST Cybersecurity Framework 2.0 (2024) | https://www.nist.gov/cyberframework | Six functions: Govern, Identify, Protect, Detect, Respond, Recover. Outcome-based map, not a prescription of technology. |
| NIST SP 800-218 SSDF v1.1 (Feb 2022) | https://csrc.nist.gov/pubs/sp/800/218/final | Secure development, supplier and release controls. |
| OWASP ASVS 5.0.0 (May 2025) | https://asvs.owasp.org/ | Application authentication, authorisation, sessions, API and other security test requirements; select appropriate verification depth. |
| OWASP Top 10 for Agentic Applications 2026 (Dec 2025) | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | Threats from autonomous agent planning, tools, memory and cross-agent actions. |
| OWASP Agentic Skills Top 10 | https://owasp.org/projects/agentic-skills-top-10 | Skill permissions, provenance, isolation and runtime governance. Verify publication/review state before treating as a stable standard. |
| OWASP Smart Contract Top 10 | https://scs.owasp.org/ | Design-time smart contract risk themes; not a substitute for chain-specific audit, economic modelling or testing. |
| UK NCSC Cyber Essentials | https://www.ncsc.gov.uk/cyberessentials/overview | Accessible business baseline; participation and certification are separate from Shards skills. |

The control registry uses labels such as `NIST-CSF-GV` or `OWASP-ASVS-5` as **informative cross-reference tags**, not official mappings to numbered clauses. A future crosswalk must be version-pinned and independently checked before it can support audit reporting. No standards text is copied into this repository.

## Regulatory perimeter and jurisdiction research

| Context | Primary authority or enacted text | Applicability and warning |
| --- | --- | --- |
| UK personal data, DPIA | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/when-do-we-need-to-do-a-dpia/ | A DPIA can be required for likely high-risk personal-data processing. Regulator guidance is under review; re-check before advice. |
| EU financial-sector digital resilience (DORA) | https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/digital-operational-resilience-act-dora | EU DORA has applied since 17 January 2025 for in-scope entities; assess entity and outsourcing roles. |
| EU markets in crypto-assets (MiCA) | https://eur-lex.europa.eu/eli/reg/2023/1114/oj | Assess crypto-asset and CASP activities, EU territorial nexus and transition rules. |
| EU AI Act | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | Phased applicability and risk/activity classifications; do not assume all AI use is high risk. |
| EU DORA legislation | https://eur-lex.europa.eu/eli/reg/2022/2554/oj | Normative text to check where DORA applies. |
| FATF Recommendations, virtual assets/VASPs | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/targeted-updated-virtualassets-vasps-2026.html | International AML/CFT standards and 2026 implementation update; **local laws** determine obligations. |
| UK financial regulator | https://www.fca.org.uk/ | Determine FCA perimeter, activity-specific permissions and applicable handbooks using current authoritative material. |
| PCI Security Standards Council | https://www.pcisecuritystandards.org/document_library/ | Payment-card industry requirements depend on cardholder-data scope and program rules. A Shards checklist is not PCI attestation. |

## Applicability decision record

Never make jurisdiction decisions based only on website visitors' apparent location. At minimum, record:
- **Legal entity and establishment:** who owns and offers the service.
- **Activity:** payments, custody, investing, AI inference, profiling, advertising, cloud hosting, etc.
- **People and data:** customer jurisdictions, residency, special-category information, cross-border flows and controllers/processors.
- **Service and assets:** regulated financial product, crypto-asset, custody controls, outsourcing and operational dependency.
- **Dates and sources:** requirements in force, transitional rules, licensed status, source URL, edition, and time checked.
- **Disposition:** likely applicable, likely inapplicable with reasons, or legal review required; give a named owner and due date.

For material legal questions, mark `BLOCKED — counsel/regulator confirmation required` and do not convert a model inference into a licensing decision. Compliance evidence is meaningful only for an exact scoped entity, activity, system and time period.

## Maintenance expectations

Review authoritative sources at each regulatory change, relevant release, incident or at least annually for general guidance. Never promise passive monitoring without an actual connected monitoring service. Keep old assessments and mapping versions rather than rewriting history. Independently re-test after updating a skill or control registry.
