# ADR 003 — Use OpenRouter via litellm for LLM Access

**Date**: 2026-06-04
**Status**: Accepted

## Context

The system needs LLM access for generation and embedding.
The user has an OpenRouter API key, not a direct OpenAI or Azure OpenAI key.
Model selection should be configurable without code changes.

## Decision

Use **litellm** as the LLM gateway with **OpenRouter** as the provider.

## Rationale

| Criterion | litellm + OpenRouter | OpenAI SDK directly | Azure OpenAI SDK |
|---|---|---|---|
| Model portability | 100+ models via one API | OpenAI models only | Azure-hosted models only |
| User's existing key | OpenRouter key works | Requires OpenAI key | Requires Azure account |
| Swap model | Change `LLM_MODEL` env var | Code change needed | Config + code change |
| Async support | `acompletion()` / `aembedding()` | Yes | Yes |
| Cost tracking | Built-in | Manual | Manual |

litellm provides a unified interface: `litellm.acompletion()` and `litellm.aembedding()`
accept the same arguments regardless of provider. Changing `LLM_MODEL=anthropic/claude-3-5-sonnet`
in `.env` requires zero code changes.

## Consequences

- `src/infra/llm_client.py` wraps `litellm.acompletion()` and `litellm.aembedding()`
- `OPENROUTER_API_KEY` and `LLM_MODEL` are the only config needed in `.env`
- Unit tests mock `llm_client.complete()` and `llm_client.embed()` at the interface level
- Switching to a direct provider requires only changing env vars (no code)
