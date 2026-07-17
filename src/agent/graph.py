from __future__ import annotations

import time

from src.agent.tools import RAGSearchTool
from src.domain.models import AgentState, ChatMessage, ChatResponse, Source
from src.domain.ports import ILLMClient, ISessionStore
from src.observability.telemetry import (
    active_sessions,
    llm_latency_seconds,
    retrieval_latency_seconds,
)

ROUTE_PROMPT = """You are a routing assistant. Given a user question, decide if it needs
document retrieval (RAG) or can be answered directly.
Reply with only "RAG" or "DIRECT"."""

GENERATE_PROMPT = """You are a helpful enterprise assistant. Answer the user's question
based on the provided context. Always cite your sources using [Source: filename].
If the context is empty, answer from your general knowledge and say so."""


class AgentGraph:
    def __init__(
        self,
        llm_client: ILLMClient,
        rag_tool: RAGSearchTool,
        session_store: ISessionStore,
    ) -> None:
        self._llm = llm_client
        self._rag = rag_tool
        self._sessions = session_store

    async def _route(self, state: AgentState) -> AgentState:
        last_message = state["messages"][-1].content
        response = await self._llm.complete(
            [
                {"role": "system", "content": ROUTE_PROMPT},
                {"role": "user", "content": last_message},
            ]
        )
        state["used_retrieval"] = response.strip().upper().startswith("RAG")
        return state

    async def _rag_search(self, state: AgentState) -> AgentState:
        query = state["messages"][-1].content
        result = await self._rag.run(query)
        state["retrieved_docs"] = result.chunks
        return state

    async def _generate(self, state: AgentState) -> AgentState:
        session_id = state["session_id"]
        history = await self._sessions.get_history(session_id)
        context_parts: list[str] = []

        if history:
            history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history)
            context_parts.append(f"Conversation history:\n{history_text}")

        if state["retrieved_docs"]:
            docs_text = "\n\n".join(
                f"[Source: {c.source}]\n{c.content}" for c in state["retrieved_docs"]
            )
            context_parts.append(f"Relevant documents:\n{docs_text}")

        system_content = GENERATE_PROMPT
        if context_parts:
            system_content += "\n\n" + "\n\n".join(context_parts)

        messages = [{"role": "system", "content": system_content}]
        messages += [{"role": m.role, "content": m.content} for m in state["messages"]]

        answer = await self._llm.complete(messages)
        assistant_msg = ChatMessage(role="assistant", content=answer)
        state["messages"].append(assistant_msg)

        user_msg = state["messages"][-2]
        await self._sessions.add_message(session_id, user_msg)
        await self._sessions.add_message(session_id, assistant_msg)

        return state

    async def invoke(self, request_message: str, session_id: str) -> ChatResponse:
        start = time.monotonic()

        state: AgentState = {
            "messages": [ChatMessage(role="user", content=request_message)],
            "retrieved_docs": [],
            "memory_context": "",
            "session_id": session_id,
            "used_retrieval": False,
        }

        state = await self._route(state)

        if state["used_retrieval"]:
            t0 = time.monotonic()
            state = await self._rag_search(state)
            retrieval_latency_seconds.observe(time.monotonic() - t0)

        t0 = time.monotonic()
        state = await self._generate(state)
        llm_latency_seconds.observe(time.monotonic() - t0)

        active_sessions.set(await self._sessions.count())

        answer = state["messages"][-1].content
        sources = [
            Source(document_id=c.document_id, chunk=c.content[:200], score=0.0)
            for c in state["retrieved_docs"]
        ]

        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id,
            used_retrieval=state["used_retrieval"],
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


def build_agent(
    llm_client: ILLMClient,
    rag_tool: RAGSearchTool,
    session_store: ISessionStore,
) -> AgentGraph:
    return AgentGraph(llm_client, rag_tool, session_store)
