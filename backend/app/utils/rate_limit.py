"""
Simple in-memory sliding-window rate limiter.

Good enough for a single-instance college deployment. If the app is ever
scaled to multiple worker processes/machines, swap this for a Redis-backed
limiter without changing the dependency's call sites.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)


def rate_limit_dependency(request: Request) -> None:
    settings = get_settings()
    limit = settings.RATE_LIMIT_PER_MINUTE
    key = request.client.host if request.client else "unknown"
    now = time.time()
    window = _hits[key]

    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests - please slow down and try again shortly.",
        )
    window.append(now)
