from pydantic import BaseModel, Field


class AiPowerToggleRequest(BaseModel):
    enabled: bool


class AiPowerStatusResponse(BaseModel):
    stt_enabled: bool
    tts_enabled: bool
    stt_status: str
    tts_status: str
    stt_warm: bool = False
    tts_containers: dict[str, str] = Field(default_factory=dict)
    tts_containers_running: bool = False
    docker_control_enabled: bool = False
    docker_control_available: bool = False
    edge_speech: bool = False
    orpheus_tts_base_url: str | None = None
    openai_stt_base_url: str | None = None
    stt_provider: str = "fake"
    tts_provider: str = "fake"
    last_error: str | None = None
