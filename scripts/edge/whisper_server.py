"""
OpenAI-compatible Whisper STT for an edge PC (Tailscale).

Run on your Windows/Linux PC (not the VM):

  pip install fastapi uvicorn python-multipart faster-whisper
  python scripts/edge/whisper_server.py --host 0.0.0.0 --port 8090 --model small

Then on the VM set:
  STT_PROVIDER=openai
  OPENAI_STT_BASE_URL=http://<tailscale-ip>:8090/v1
  OPENAI_STT_MODEL=whisper-small
  OPENAI_API_KEY=sk-local
"""

from __future__ import annotations

import argparse
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger("edge-whisper")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_model = None
_model_name = "small"
_device = "auto"
_compute_type: str | None = None


def _resolve_device(requested: str) -> tuple[str, str]:
    """Return (device, compute_type). auto → cuda if available else cpu."""
    if requested == "auto":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:  # noqa: BLE001
            pass
        return "cpu", "int8"
    if requested == "cuda":
        return "cuda", "float16"
    return requested, "int8"


def get_model():
    global _model, _compute_type
    if _model is None:
        from faster_whisper import WhisperModel

        device, compute = _resolve_device(_device)
        if _compute_type:
            compute = _compute_type
        logger.info(
            "Loading faster-whisper model=%s device=%s compute_type=%s …",
            _model_name,
            device,
            compute,
        )
        _model = WhisperModel(_model_name, device=device, compute_type=compute)
        logger.info("Whisper ready on %s", device)
    return _model


app = FastAPI(title="Decime edge Whisper", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    device, _ = _resolve_device(_device)
    return {"status": "ok", "model": _model_name, "device": device}


@app.get("/v1/models")
def list_models() -> dict:
    return {
        "object": "list",
        "data": [{"id": f"whisper-{_model_name}", "object": "model", "owned_by": "local"}],
    }


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default="whisper-small"),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
) -> JSONResponse:
    _ = model, prompt
    data = await file.read()
    if not data:
        return JSONResponse({"error": "empty file"}, status_code=400)

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = tmp.name

    try:
        whisper = get_model()
        segments, info = whisper.transcribe(
            path,
            language=language or None,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return JSONResponse({"text": text, "language": getattr(info, "language", language)})
    finally:
        Path(path).unlink(missing_ok=True)


def main() -> None:
    global _model_name, _device, _compute_type
    parser = argparse.ArgumentParser(description="Decime edge Whisper (OpenAI-compatible)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--model", default="small", help="tiny|base|small|…")
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "cpu", "cuda"),
        help="auto = cuda if available else cpu",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        help="Override compute type (e.g. int8, float16). Default depends on device.",
    )
    args = parser.parse_args()
    _model_name = args.model
    _device = args.device
    _compute_type = args.compute_type
    get_model()
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
