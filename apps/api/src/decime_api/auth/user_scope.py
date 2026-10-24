"""Auth helpers for per-user data access."""

from fastapi import HTTPException, status

from decime_api.auth.dependencies import CurrentUser
from decime_api.config import settings

LOCAL_ANONYMOUS_USER_ID = "00000000-0000-4000-8000-000000000099"


def resolve_user_id(user: CurrentUser) -> str:
    """Return authenticated user id, or local anonymous id when auth is disabled."""
    if settings.use_postgres:
        if not user.authenticated or not user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user.id

    if user.authenticated and user.id:
        return user.id
    return LOCAL_ANONYMOUS_USER_ID
