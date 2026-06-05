from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from src.core.config import settings


def _get_client_ip(request: Request) -> str:
    if settings.trusted_proxies > 0:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ips = [ip.strip() for ip in forwarded.split(",")]
            idx = max(len(ips) - settings.trusted_proxies, 0)
            return ips[idx]
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_client_ip)
