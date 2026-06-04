# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Send a private report to: baneseydinamouhamet@gmail.com

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
- SSRF guard on URL ingestion — resolves hostnames and blocks private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x, ::1, fc00::/7). Optional `ALLOWED_URL_DOMAINS` allowlist
- File upload size limit (default 50 MB, configurable via `MAX_UPLOAD_SIZE_MB`)
- CORS restricted to `["http://localhost:3000"]` by default — must configure `ALLOWED_ORIGINS` per environment
- Proxy-aware rate limiting IP detection (X-Forwarded-For / X-Real-IP)
- LLM client timeout (default 60s) with exponential backoff retry (max 2)
- Bandit SAST scan in CI — blocks on HIGH/CRITICAL findings
- Trivy Docker image scan in release pipeline — blocks on HIGH/CRITICAL CVEs
- Dependabot weekly dependency updates
- Non-root user in Docker container
- No `eval()`, no shell injection surface in the codebase
