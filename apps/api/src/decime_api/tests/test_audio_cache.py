from decime_api.services.storage.audio_cache import tts_cache_key


def test_tts_cache_key_stable() -> None:
  key_a = tts_cache_key(
      text="Hola",
      locale="es-UY-montevideo",
      model="gpt-4o-mini-tts",
      voice="coral",
      mode="reply",
      speed="normal",
  )
  key_b = tts_cache_key(
      text="Hola",
      locale="es-UY-montevideo",
      model="gpt-4o-mini-tts",
      voice="coral",
      mode="reply",
      speed="normal",
  )
  key_c = tts_cache_key(
      text="Hola!",
      locale="es-UY-montevideo",
      model="gpt-4o-mini-tts",
      voice="coral",
      mode="reply",
      speed="normal",
  )
  assert key_a == key_b
  assert key_a != key_c
