from __future__ import annotations

from datetime import datetime
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    content: str
    source: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    source: str
    embedding: list[float] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Annotated[str, Field(pattern="^(user|assistant|system)$")]
    content: str


class Source(BaseModel):
    document_id: str
    chunk: str
    score: float


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=4096)]
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    session_id: str
    used_retrieval: bool
    latency_ms: float


class IngestRequest(BaseModel):
    url: str


class IngestResponse(BaseModel):
    document_id: str
    chunks_stored: int
    status: str = "ok"


class DocumentMeta(BaseModel):
    id: str
    chunks: int
    ingested_at: datetime


class AgentState(TypedDict):
    messages: list[ChatMessage]
    retrieved_docs: list[Chunk]
    memory_context: str
    session_id: str
    used_retrieval: bool
