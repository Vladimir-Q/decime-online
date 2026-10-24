"""Simple in-memory sliding-window rate limiter (single API process)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# path prefix → (max_requests, window_seconds)
_RULES: tuple[tuple[str, int, int], ...] = (
    ("/api/v1/auth/login", 10, 60),
    ("/api/v1/auth/register", 5, 60),
    ("/api/v1/translate/", 60, 60),
    ("/api/v1/incoming/", 60, 60),
    ("/api/v1/audio/", 60, 60),
    ("/api/v1/training/extract-candidates", 30, 60),
    ("/api/v1/training/approve-candidates", 30, 60),
)

_HIT_STORE: dict[str, deque[float]] = defaultdict(deque)
_HIT_LOCK = Lock()


def reset_rate_limit_state() -> None:
    """Clear buckets (tests only)."""
    with _HIT_LOCK:
        _HIT_STORE.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        rule = _match_rule(request.url.path)
        if rule is None:
            return await call_next(request)

        max_requests, window = rule
        client = _client_key(request)
        bucket = f"{client}:{request.url.path.split('?')[0]}"

        now = time.monotonic()
        with _HIT_LOCK:
            q = _HIT_STORE[bucket]
            cutoff = now - window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= max_requests:
                retry_after = max(1, int(window - (now - q[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
            q.append(now)

        return await call_next(request)


def _match_rule(path: str) -> tuple[int, int] | None:
    for prefix, max_requests, window in _RULES:
        if path == prefix or path.startswith(prefix):
            return max_requests, window
    return None


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
