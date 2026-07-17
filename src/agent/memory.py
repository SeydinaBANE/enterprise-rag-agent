from __future__ import annotations

from collections import deque

from src.domain.models import ChatMessage
from src.domain.ports import ISessionStore

MAX_TURNS = 10


class ConversationMemory:
    def __init__(self, max_turns: int = MAX_TURNS) -> None:
        self._messages: deque[ChatMessage] = deque(maxlen=max_turns * 2)

    def add(self, message: ChatMessage) -> None:
        self._messages.append(message)

    def get_history(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()


class InMemorySessionStore(ISessionStore):
    def __init__(self) -> None:
        self._memories: dict[str, ConversationMemory] = {}

    def _get_or_create(self, session_id: str) -> ConversationMemory:
        if session_id not in self._memories:
            self._memories[session_id] = ConversationMemory()
        return self._memories[session_id]

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return self._get_or_create(session_id).get_history()

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        self._get_or_create(session_id).add(message)

    async def count(self) -> int:
        return len(self._memories)

    async def is_healthy(self) -> bool:
        return True
