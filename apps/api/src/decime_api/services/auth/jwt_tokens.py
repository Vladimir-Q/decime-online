from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt

from decime_api.config import settings


class TokenError(Exception):
    pass


def create_access_token(*, user_id: str, email: str, role: str) -> tuple[str, int]:
    expires_minutes = settings.auth_jwt_expire_minutes
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")
    return token, expires_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "email", "role"]},
        )
    except jwt.PyJWTError as error:
        raise TokenError("Invalid or expired token") from error
    return payload
