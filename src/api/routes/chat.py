from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.middleware.auth import require_api_key
from src.api.middleware.ratelimit import limiter
from src.core.config import settings
from src.core.exceptions import GuardrailViolation, LLMError
from src.core.models import ChatRequest, ChatResponse
from src.guardrails import filters
from src.observability.telemetry import chat_requests_total

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    try:
        filters.check_input(body.message)
    except GuardrailViolation as exc:
        chat_requests_total.labels(status="blocked").inc()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from src.agent.graph import AgentGraph

    agent: AgentGraph = request.app.state.agent

    try:
        response = await agent.invoke(body.message, body.session_id)
    except LLMError as exc:
        chat_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=500, detail="LLM error") from exc

    response.answer = filters.check_output(response.answer)
    chat_requests_total.labels(status="ok").inc()
    return response
