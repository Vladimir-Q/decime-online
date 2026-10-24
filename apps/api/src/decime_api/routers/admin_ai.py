from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from decime_api.auth.dependencies import CurrentUser, require_admin
from decime_api.schemas.admin_ai import AiPowerStatusResponse, AiPowerToggleRequest
from decime_api.services.ai.ai_power_service import (
    build_ai_power_status,
    set_stt_powered,
    set_tts_powered,
)
from decime_api.services.ai.docker_ai_control import DockerAiControlError

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.get("/status", response_model=AiPowerStatusResponse)
async def ai_power_status(
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> AiPowerStatusResponse:
    return AiPowerStatusResponse(**await build_ai_power_status())


@router.post("/stt", response_model=AiPowerStatusResponse)
async def set_stt_power(
    request: AiPowerToggleRequest,
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> AiPowerStatusResponse:
    try:
        status = await set_stt_powered(request.enabled)
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AiPowerStatusResponse(**status)


@router.post("/tts", response_model=AiPowerStatusResponse)
async def set_tts_power(
    request: AiPowerToggleRequest,
    _admin: Annotated[CurrentUser, Depends(require_admin)],
) -> AiPowerStatusResponse:
    try:
        status = await set_tts_powered(request.enabled)
    except DockerAiControlError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AiPowerStatusResponse(**status)
