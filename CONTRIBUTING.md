# Contributing

## Before opening a PR

1. Read the repository security model and third-party import policy.
2. Run `python scripts/validate_skills.py` and `python -m unittest discover -s tests -v`.
3. Add or update an eval case for changed behaviour.
4. Include provenance and licence evidence for any imported material.
5. Explain compatibility tested, limitations, and any commands or network access the skill may request.

## Review checklist

- [ ] The skill has a specific, discoverable trigger.
- [ ] Inputs, prerequisites, steps and output contract are explicit.
- [ ] Verification is objective and does not claim tools ran when they did not.
- [ ] Failure/uncertainty paths are defined.
- [ ] No request to reveal secrets, bypass approvals, disable safeguards or execute untrusted payloads.
- [ ] Scripts are minimal, reviewed and tested in isolation.
- [ ] Licences, notices and source revisions are recorded.
- [ ] CI and relevant evaluations pass.
