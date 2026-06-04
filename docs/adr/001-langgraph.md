# ADR 001 — Use LangGraph for Agent Orchestration

**Date**: 2026-06-04
**Status**: Accepted

## Context

The agent needs to conditionally route between RAG retrieval and direct LLM generation,
maintain typed state across steps, and support future extension to multi-agent workflows.

## Decision

Use **LangGraph** (`StateGraph`) as the agent orchestration framework.

## Rationale

| Criterion | LangGraph | Simple LangChain chain | Semantic Kernel |
|---|---|---|---|
| Conditional routing | Native (edge functions) | Manual, verbose | Plugin-based |
| Typed state | `TypedDict` / Pydantic | No | Yes |
| Tool use | First-class | Via agent executor | Via plugins |
| Multi-agent extension | Native (`send()`) | Requires rewrite | Possible |
| Python SDK maturity | High | High | Medium |

LangGraph's explicit state graph makes the agent's control flow auditable and testable.
Each node is a pure function on `AgentState`, making unit testing straightforward.

## Consequences

- `src/agent/graph.py` defines a `StateGraph` compiled into a `CompiledGraph`
- Agent state is defined as `AgentState` TypedDict in `src/core/models.py`
- Adding a new step = adding a node and edges, no structural changes to existing code
