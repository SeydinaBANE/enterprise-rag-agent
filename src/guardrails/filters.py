from __future__ import annotations

import re

from src.core.exceptions import GuardrailViolation

_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b\d{16}\b"),
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
]

_INJECTION_PATTERNS = [
    re.compile(r"ignore.{0,30}instructions?", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"disregard (your|all|previous)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"act as (if )?you (are|were)", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 4096
MAX_OUTPUT_LENGTH = 8192


def check_input(text: str) -> None:
    if len(text) > MAX_INPUT_LENGTH:
        raise GuardrailViolation(f"Input exceeds {MAX_INPUT_LENGTH} characters")

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise GuardrailViolation("Prompt injection attempt detected")


def redact_pii(text: str) -> str:
    result = text
    for pattern in _PII_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def check_output(text: str) -> str:
    if len(text) > MAX_OUTPUT_LENGTH:
        text = text[:MAX_OUTPUT_LENGTH] + "... [truncated]"
    return redact_pii(text)
