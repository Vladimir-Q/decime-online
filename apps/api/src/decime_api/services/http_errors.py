"""Client-safe HTTP errors — never leak upstream/provider details."""

from __future__ import annotations

import logging
from typing import NoReturn

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_GENERIC_UPSTREAM = "Upstream service error. Please try again."


def raise_upstream_error(route: str, error: BaseException) -> NoReturn:
    """Log the real error server-side; return a generic 502 to the client."""
    logger.exception("Upstream failure on %s: %s", route, error)
    raise HTTPException(status_code=502, detail=_GENERIC_UPSTREAM) from error
