import hmac
import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from decime_api.config import settings
from decime_api.db.user_store import UserRecord, get_user_store
from decime_api.services.auth.jwt_tokens import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)
AUTOMATION_HEADER_NAME = "X-Decime-Automation-Key"


@dataclass(frozen=True)
class CurrentUser:
    id: str | None
    email: str | None
    role: str
    is_active: bool
    authenticated: bool


def _anonymous_user() -> CurrentUser:
    return CurrentUser(
        id=None,
        email=None,
        role="user",
        is_active=True,
        authenticated=False,
    )


def _record_to_current(user: UserRecord) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        authenticated=True,
    )


def user_to_public(user: UserRecord):
    from decime_api.schemas.auth import UserPublic

    return UserPublic(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,  # type: ignore[arg-type]
        is_active=user.is_active,
        created_at=user.created_at,
        app_language=user.app_language,  # type: ignore[arg-type]
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if not settings.auth_enabled:
        return _anonymous_user()

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = get_user_store().get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.email != str(payload["email"]) or user.role != str(payload["role"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no longer valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from decime_api.services.analytics.request_context import set_current_user_id

    set_current_user_id(user.id)
    return _record_to_current(user)


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoints require AUTH_ENABLED=true",
        )
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """Sheets buttons need a real JWT user even when AUTH_ENABLED=false (no anonymous)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = get_user_store().get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.email != str(payload["email"]) or user.role != str(payload["role"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no longer valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from decime_api.services.analytics.request_context import set_current_user_id

    set_current_user_id(user.id)
    return _record_to_current(user)


async def require_n8n_automation(
    x_decime_automation_key: Annotated[str | None, Header(alias=AUTOMATION_HEADER_NAME)] = None,
) -> None:
    configured = (settings.n8n_automation_key or "").strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="n8n automation is not configured",
        )
    provided = (x_decime_automation_key or "").strip()
    # hmac.compare_digest requires equal length; pad via secrets token of same length.
    matched = False
    if provided:
        if len(provided) == len(configured):
            matched = hmac.compare_digest(provided, configured)
        else:
            # Still burn a compare to reduce trivial timing oracles on length.
            secrets.compare_digest(provided, "x" * len(provided))
            matched = False
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation key",
        )
