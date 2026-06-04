# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Send a private report to: baneseydinamouhametgmail.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive an acknowledgement within 48 hours and a resolution timeline within 7 days.

## Security Practices in This Project

- No secrets in source code — all credentials via environment variables
- API key authentication on all data endpoints
- PII detection filters on both input and output
- Prompt injection pattern detection
- Bandit SAST scan in CI — blocks on HIGH/CRITICAL findings
- Trivy Docker image scan in release pipeline — blocks on HIGH/CRITICAL CVEs
- Dependabot weekly dependency updates
- Non-root user in Docker container
- No `eval()`, no shell injection surface in the codebase
