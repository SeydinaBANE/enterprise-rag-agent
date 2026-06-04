from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

chat_requests_total = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["status"],
)

ingest_requests_total = Counter(
    "ingest_requests_total",
    "Total document ingest requests",
    ["status"],
)

retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "Time spent on RAG retrieval",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "Time spent on LLM generation",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active chat sessions",
)
