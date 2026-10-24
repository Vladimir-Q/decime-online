import hashlib


def tts_cache_key(
    *,
    text: str,
    locale: str,
    model: str,
    voice: str,
    mode: str,
    speed: str,
) -> str:
    payload = f"{text}|{locale}|{model}|{voice}|{mode}|{speed}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
