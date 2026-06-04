# Contributing

## Getting Started

```bash
git clone https://github.com/<user>/enterprise-rag-agent
cd enterprise-rag-agent
make install
cp .env.example .env
```

## Workflow

1. **Branch** from `main`: `git checkout -b feat/my-feature`
2. **Make changes** — follow the code style below
3. **Test**: `make check` (lint + typecheck + security + test) — all must pass
4. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/)
5. **Push** and open a PR — CI runs automatically

## Code Style

- Python 3.12+ with strict type hints on all functions
- Line length: 100 characters (enforced by ruff)
- No `Any`, no `# type: ignore` without an explanation
- No comments explaining what the code does — only why (non-obvious constraints)
- One function = one responsibility, max ~30 lines

## Testing Requirements

Every change must include:
- At least one nominal test
- At least one error/edge case test
- Coverage must remain ≥ 80%

Tests naming convention: `test_<function>_<case>`

Example: `test_retrieve_empty_corpus`, `test_chat_guardrail_violation`

## Commit Message Format

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `chore`, `docs`, `test`, `ci`, `refactor`

## Pull Request Checklist

See [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

## Reporting Issues

Use the GitHub issue templates:
- **Bug**: [.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature**: [.github/ISSUE_TEMPLATE/feature_request.md](.github/ISSUE_TEMPLATE/feature_request.md)

## Security

Do not open a public issue for security vulnerabilities — see [SECURITY.md](SECURITY.md).
