from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from decime_api.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_admin,
    user_to_public,
)
from decime_api.config import settings
from decime_api.db.user_store import UserRecord, get_user_store
from decime_api.schemas.auth import (
    AuthConfigResponse,
    AuthTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserCreateRequest,
    UserPreferencesUpdateRequest,
    UserPublic,
    UserUpdateRequest,
)
from decime_api.services.auth.jwt_tokens import create_access_token
from decime_api.services.auth.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: UserRecord) -> AuthTokenResponse:
    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return AuthTokenResponse(access_token=token, expires_in=expires_in)


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config() -> AuthConfigResponse:
    return AuthConfigResponse(
        auth_enabled=settings.auth_enabled,
        allow_registration=settings.auth_allow_registration and settings.auth_enabled,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> AuthTokenResponse:
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth is disabled")
    if not settings.auth_allow_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Ask an admin to create your account.",
        )

    store = get_user_store()
    if store.get_by_email(request.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = store.create_user(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
        role="user",
        is_active=True,
    )
    return _issue_token(user)


@router.post("/login", response_model=AuthTokenResponse)
async def login(request: LoginRequest) -> AuthTokenResponse:
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth is disabled")

    user = get_user_store().get_by_email(request.email)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return _issue_token(user)


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> UserPublic:
    if not settings.auth_enabled or not user.authenticated or user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    record = get_user_store().get_by_id(user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_to_public(record)


@router.patch("/me/preferences", response_model=UserPublic)
async def update_my_preferences(
    request: UserPreferencesUpdateRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> UserPublic:
    if not settings.auth_enabled or not user.authenticated or user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    updated = get_user_store().update_user(user.id, app_language=request.app_language)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_to_public(updated)


@router.get("/users", response_model=list[UserPublic])
async def list_users(_admin: Annotated[CurrentUser, Depends(require_admin)]) -> list[UserPublic]:
    return [user_to_public(user) for user in get_user_store().list_users()]


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> UserPublic:
    store = get_user_store()
    if store.get_by_email(request.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = store.create_user(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
        role=request.role,
        is_active=request.is_active,
    )
    return user_to_public(user)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    admin: Annotated[CurrentUser, Depends(require_admin)],
) -> UserPublic:
    if admin.id == user_id and request.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    updated = get_user_store().update_user(
        user_id,
        display_name=request.display_name,
        role=request.role,
        is_active=request.is_active,
        password=request.password,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_to_public(updated)
