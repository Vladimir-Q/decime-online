import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

_ALLOWED_EXTENSIONS = frozenset(
    {"webm", "wav", "mp3", "ogg", "m4a", "mpeg", "mp4", "flac", "opus", "aac"}
)


def sanitize_audio_extension(extension: str | None, *, fallback: str = "webm") -> str:
    """Allowlist-only extension; strips path separators and rejects traversal."""
    raw = (extension or fallback).strip().lower()
    if "/" in raw or "\\" in raw or ".." in raw:
        return fallback
    # Take final segment only (handles "foo.webm" mistakenly passed as extension).
    candidate = raw.rsplit(".", 1)[-1]
    if candidate in _ALLOWED_EXTENSIONS:
        return candidate
    return fallback


@dataclass
class StoredAudio:
    audio_id: str
    storage_path: Path
    mime_type: str
    text_hash: str | None = None
    provider: str | None = None
    model: str | None = None
    voice: str | None = None
    user_id: str | None = None


class LocalAudioStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.base_dir / "index.json"
        self._index: dict[str, dict] = self._load_index()

    def _load_index(self) -> dict[str, dict]:
        if not self._index_path.exists():
            return {}
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save_index(self) -> None:
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _user_dir(self, user_id: str | None) -> Path:
        if user_id:
            path = self.base_dir / user_id
            path.mkdir(parents=True, exist_ok=True)
            return path
        return self.base_dir

    def _resolve_under_base(self, *parts: str) -> Path | None:
        base = self.base_dir.resolve()
        candidate = (self.base_dir.joinpath(*parts)).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            return None
        return candidate

    def save_bytes(
        self,
        data: bytes,
        *,
        mime_type: str,
        extension: str,
        text_hash: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        voice: str | None = None,
        user_id: str | None = None,
    ) -> StoredAudio:
        audio_id = str(uuid4())
        safe_ext = sanitize_audio_extension(extension)
        user_dir = self._user_dir(user_id)
        path = user_dir / f"{audio_id}.{safe_ext}"
        path.write_bytes(data)
        record = {
            "audio_id": audio_id,
            "filename": path.name,
            "relative_dir": str(user_dir.relative_to(self.base_dir)),
            "mime_type": mime_type,
            "text_hash": text_hash,
            "provider": provider,
            "model": model,
            "voice": voice,
            "user_id": user_id,
        }
        self._index[audio_id] = record
        if text_hash and user_id:
            self._index[f"hash:{user_id}:{text_hash}"] = record
        elif text_hash:
            self._index[f"hash:{text_hash}"] = record
        self._save_index()
        return StoredAudio(
            audio_id=audio_id,
            storage_path=path,
            mime_type=mime_type,
            text_hash=text_hash,
            provider=provider,
            model=model,
            voice=voice,
            user_id=user_id,
        )

    def get(self, audio_id: str, *, user_id: str | None = None) -> StoredAudio | None:
        record = self._index.get(audio_id)
        if not record:
            return None
        # When a caller scopes by user, require an exact owner match (no legacy null-owner IDOR).
        if user_id is not None:
            record_user = record.get("user_id")
            if not record_user or record_user != user_id:
                return None
        relative_dir = record.get("relative_dir", "") or ""
        filename = record.get("filename") or ""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            return None
        parts = [p for p in Path(relative_dir).parts if p not in ("", ".")]
        if any(part == ".." for part in parts):
            return None
        path = self._resolve_under_base(*parts, filename)
        if path is None or not path.exists() or not path.is_file():
            return None
        return StoredAudio(
            audio_id=audio_id,
            storage_path=path,
            mime_type=record.get("mime_type", "audio/mpeg"),
            text_hash=record.get("text_hash"),
            provider=record.get("provider"),
            model=record.get("model"),
            voice=record.get("voice"),
            user_id=record.get("user_id"),
        )

    def find_by_text_hash(self, text_hash: str, *, user_id: str | None = None) -> StoredAudio | None:
        key = f"hash:{user_id}:{text_hash}" if user_id else f"hash:{text_hash}"
        record = self._index.get(key)
        if not record:
            return None
        return self.get(record["audio_id"], user_id=user_id)

    def clear_user(self, user_id: str) -> None:
        user_dir = self.base_dir / user_id
        if user_dir.exists():
            for path in user_dir.glob("*"):
                if path.is_file():
                    path.unlink()
        to_delete = [
            key
            for key, record in self._index.items()
            if isinstance(record, dict) and record.get("user_id") == user_id
        ]
        for key in to_delete:
            self._index.pop(key, None)
        hash_keys = [k for k in self._index if k.startswith(f"hash:{user_id}:")]
        for key in hash_keys:
            self._index.pop(key, None)
        self._save_index()

    def clear_all(self) -> None:
        for path in self.base_dir.glob("*"):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                for nested in path.glob("*"):
                    if nested.is_file():
                        nested.unlink()
        self._index = {}
        self._save_index()
