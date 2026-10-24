# Локальный STT + OpenAI для текста и озвучки

## Схема (текущая)

| Задача | Провайдер | Переменные `.env` |
|--------|-----------|-------------------|
| Речь → текст (STT) | **Локальный Whisper** (`faster-whisper`) | `STT_PROVIDER=faster_whisper`, `WHISPER_MODEL_SIZE=base` |
| Ответы / перевод + извлечение слов (LLM) | **OpenAI** `gpt-6-luna` | `LLM_PROVIDER=openai`, `OPENAI_API_KEY` |
| Озвучка es-UY (TTS) | **OpenAI** | `TTS_PROVIDER=openai`, `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE` |

Аудио на транскрипцию ограничено **ru / en / es** (см. `stt_languages.py`).

## Про `karanchopda333/whisper:latest` в Ollama

Тег в каталоге Ollama **не является** моделью распознавания речи. По факту это **Llama 3.2 3B** (ввод только текст, capabilities: `completion`, `tools`). Примеры на странице модели — обычный `ollama chat`, без загрузки аудио.

Для Decime локальный STT реализован через **OpenAI Whisper** (библиотека `faster-whisper`, веса ~`base`, ~150–200 MB скачивания, сопоставимо по размеру с «2 GB» тегом в Ollama).

Если вы уже сделали `ollama pull karanchopda333/whisper:latest` и не используете её для чата, можно освободить место:

```bash
ollama rm karanchopda333/whisper:latest
```

Ollama для STT в этом проекте **не требуется**.

## Установка локального STT (Windows)

1. **ffmpeg** (для webm, mp3, m4a и т.д.):

   ```powershell
   winget install Gyan.FFmpeg
   ```

2. Скрипт настройки из корня репозитория:

   ```powershell
   .\scripts\setup_local_stt.ps1
   ```

   Или в Git Bash:

   ```bash
   bash scripts/setup_local_stt.sh
   ```

3. В корневом `.env`:

   ```env
   STT_PROVIDER=faster_whisper
   WHISPER_MODEL_SIZE=base
   LLM_PROVIDER=openai
   TTS_PROVIDER=openai
   ```

4. Запуск API:

   ```bash
   cd apps/api
   source .venv/Scripts/activate   # Git Bash
   uvicorn decime_api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
   ```

5. Проверка:

   ```bash
   curl -s http://127.0.0.1:8000/health
   ```

   Ожидается `"stt_provider": "faster_whisper"`, `"stt_model": "base"`.

6. UI: [http://localhost:3000/app/audio](http://localhost:3000/app/audio) — загрузить голосовое, язык Auto или ru/en/es.

## Первый запрос

Первая транскрипция может занять 10–30 с: загрузка весов и прогрев на CPU. Дальше быстрее.

## Если нужен именно Ollama

`STT_PROVIDER=ollama` пробует OpenAI-совместимый endpoint Ollama; для `karanchopda333/whisper` он **не работает**. Используйте `faster_whisper`.
