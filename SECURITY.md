# Security policy

## Reporting

Do not publish secrets, exploit details against real targets, or malicious skill payloads in public issues. Report suspected vulnerabilities privately to the maintainers through the security contact configured in the GitHub repository. Until a contact is configured, do not assume a private reporting channel exists.

## Threat model

This repository accepts natural-language instructions and potentially scripts that influence agent behaviour. Threats include prompt injection, credential theft, unauthorised network exfiltration, destructive commands, unsafe dependency installation, data poisoning and misleading evaluation results.

## Required controls

- Treat upstream skills as untrusted input.
- Never run an imported script before review.
- Test in a disposable environment without secrets and with restricted network access.
- Require explicit human approval for destructive or externally visible actions.
- Prefer read-only discovery and least-privilege credentials.
- Preserve logs, revision identifiers, reviewer status and test results.
- Treat static scanning as heuristic; passing scans does not certify safety.
