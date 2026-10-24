"""Control compose AI containers via Docker Engine HTTP API (unix socket)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from decime_api.config import settings

logger = logging.getLogger(__name__)

_COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
_COMPOSE_SERVICE_LABEL = "com.docker.compose.service"
_TTS_SERVICES = ("ollama", "orpheus")


@dataclass
class ContainerInfo:
    id: str
    name: str
    service: str
    state: str  # running | exited | created | ...


class DockerAiControlError(RuntimeError):
    pass


class DockerAiController:
    """Start/stop ollama+orpheus by compose labels."""

    def __init__(
        self,
        *,
        socket_path: str | None = None,
        project: str | None = None,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
    ) -> None:
        self.socket_path = socket_path or settings.ai_docker_socket
        self.project = project or settings.ai_docker_project
        self.ollama_base_url = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        self.ollama_model = ollama_model or settings.orpheus_ollama_model

    @property
    def available(self) -> bool:
        if not settings.ai_docker_control_enabled:
            return False
        from pathlib import Path

        return Path(self.socket_path).exists()

    def _client(self) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(uds=self.socket_path)
        return httpx.AsyncClient(
            transport=transport,
            base_url="http://docker.local",
            timeout=120.0,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.available:
            raise DockerAiControlError(
                "Docker AI control is disabled or /var/run/docker.sock is not mounted. "
                "Set AI_DOCKER_CONTROL_ENABLED=true and mount the Docker socket into the API."
            )
        async with self._client() as client:
            response = await client.request(method, path, **kwargs)
        return response

    async def list_tts_containers(self) -> list[ContainerInfo]:
        filters = json.dumps(
            {
                "label": [
                    f"{_COMPOSE_PROJECT_LABEL}={self.project}",
                ]
            }
        )
        response = await self._request(
            "GET",
            "/containers/json",
            params={"all": "true", "filters": filters},
        )
        if response.status_code >= 400:
            raise DockerAiControlError(f"Docker list failed: HTTP {response.status_code}")
        items: list[ContainerInfo] = []
        for row in response.json():
            labels = row.get("Labels") or {}
            service = labels.get(_COMPOSE_SERVICE_LABEL, "")
            if service not in _TTS_SERVICES:
                continue
            names = row.get("Names") or []
            name = names[0].lstrip("/") if names else row.get("Id", "")[:12]
            state = (row.get("State") or "unknown").lower()
            items.append(
                ContainerInfo(
                    id=row["Id"],
                    name=name,
                    service=service,
                    state=state,
                )
            )
        return items

    async def container_states(self) -> dict[str, str]:
        found = {c.service: c.state for c in await self.list_tts_containers()}
        return {service: found.get(service, "missing") for service in _TTS_SERVICES}

    async def start_tts_stack(self) -> dict[str, str]:
        containers = await self.list_tts_containers()
        by_service = {c.service: c for c in containers}
        for service in _TTS_SERVICES:
            container = by_service.get(service)
            if container is None:
                raise DockerAiControlError(
                    f"Compose service '{service}' not found in project '{self.project}'"
                )
            if container.state == "running":
                continue
            response = await self._request("POST", f"/containers/{container.id}/start")
            if response.status_code not in (204, 304):
                detail = response.text[:300]
                raise DockerAiControlError(
                    f"Failed to start {service}: HTTP {response.status_code} {detail}"
                )
            logger.info("docker start service=%s container=%s", service, container.name)
        await self._wait_ollama_ready(timeout_sec=180)
        return await self.container_states()

    async def stop_tts_stack(self) -> dict[str, str]:
        containers = await self.list_tts_containers()
        by_service = {c.service: c for c in containers}
        # Stop orpheus first, then ollama.
        for service in ("orpheus", "ollama"):
            container = by_service.get(service)
            if container is None or container.state != "running":
                continue
            response = await self._request(
                "POST",
                f"/containers/{container.id}/stop",
                params={"t": "20"},
            )
            if response.status_code not in (204, 304):
                detail = response.text[:300]
                raise DockerAiControlError(
                    f"Failed to stop {service}: HTTP {response.status_code} {detail}"
                )
            logger.info("docker stop service=%s container=%s", service, container.name)
        return await self.container_states()

    async def warm_ollama_model(self) -> None:
        url = f"{self.ollama_base_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": " ",
            "stream": False,
            "keep_alive": -1,
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise DockerAiControlError(
                f"Ollama warm failed: HTTP {response.status_code} {response.text[:300]}"
            )
        logger.info("ollama warm model=%s", self.ollama_model)

    async def _wait_ollama_ready(self, timeout_sec: int = 180) -> None:
        import time

        deadline = time.monotonic() + timeout_sec
        last_error = "timeout"
        while time.monotonic() < deadline:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.ollama_base_url}/api/tags")
                if response.status_code < 400:
                    return
                last_error = f"HTTP {response.status_code}"
            except Exception as error:  # noqa: BLE001 — probe until ready
                last_error = str(error)
            await asyncio.sleep(2)
        raise DockerAiControlError(f"Ollama not ready after start: {last_error}")
