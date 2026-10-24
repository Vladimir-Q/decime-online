# Локальный TTS: sematre/orpheus (испанский) через Orpheus-FastAPI

## Схема

Orpheus — это **не** обычный `ollama chat`. Цепочка такая:

```text
Decime API  →  Orpheus-FastAPI (:5005)  →  Ollama sematre/orpheus:it_es  →  WAV
```

| Компонент | Роль |
|-----------|------|
| **Ollama** `sematre/orpheus:it_es` | генерирует аудио-токены (~3.5 GB) |
| **Orpheus-FastAPI** | декодирует в WAV, OpenAI-совместимый `/v1/audio/speech` |
| **Decime** | `TTS_PROVIDER=orpheus`, вызывает `:5005` только по **Play audio** |

### Голоса для испанского

| Voice | Описание |
|-------|----------|
| `javi` | мужской, тёплый (рекомендуется для обучения) |
| `sergio` | мужской, деловой |
| `maria` | женский, дружелюбный |

В `.env`: `ORPHEUS_TTS_VOICE=javi`

---

## Установка (Windows)

### 0. Предусловия

| Что | Зачем |
|-----|-------|
| **Python 3.11** | Orpheus-FastAPI **не работает** на 3.12+ |
| **Ollama** + `sematre/orpheus:it_es` | генерация аудио-токенов |
| **Git** | клонирование репозитория |

В Git Bash команда `python` часто ведёт в Microsoft Store (ошибка «Python was not found»). Используйте **`py -3.11`** или полный путь к `.venv\Scripts\python.exe`.

Установка Python 3.11 (один раз):

```powershell
winget install --id Python.Python.3.11 -e
```

### 1. Модель в Ollama

```bash
ollama pull sematre/orpheus:it_es
```

### 2. Orpheus-FastAPI (отдельный сервис)

Требуется **Python 3.10 или 3.11** (не 3.12+). Папку нужно **сначала склонировать** — её нет в репозитории Decime.

**PowerShell:**

```powershell
cd $HOME\src   # or any directory you prefer
git clone https://github.com/Lex-au/Orpheus-FastAPI.git
cd Orpheus-FastAPI
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

**Git Bash** (те же шаги, другой синтаксис activate):

```bash
cd ~/src   # or any directory you prefer
git clone https://github.com/Lex-au/Orpheus-FastAPI.git
cd Orpheus-FastAPI
py -3.11 -m venv .venv
source .venv/Scripts/activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Создайте `.env` в папке Orpheus-FastAPI:

```env
ORPHEUS_API_URL=http://localhost:11434/v1/completions
ORPHEUS_MODEL_NAME=sematre/orpheus:it_es
ORPHEUS_PORT=5005
ORPHEUS_HOST=0.0.0.0
# Required with Ollama: without raw generate, Orpheus gets chat text → empty WAV
ORPHEUS_OLLAMA_RAW=true
```

Запуск (терминал отдельный от Decime):

```bash
cd "$ORPHEUS_DIR"   # path to your Orpheus-FastAPI clone
source .venv/Scripts/activate
python app.py
```

Или без activate (Windows):

```bash
"$ORPHEUS_DIR/.venv/Scripts/python.exe" "$ORPHEUS_DIR/app.py"
```

Проверка:

```powershell
curl.exe -X POST http://127.0.0.1:5005/v1/audio/speech `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"orpheus\",\"input\":\"Hola, quería consultar.\",\"voice\":\"javi\",\"response_format\":\"wav\"}" `
  --output test.wav
```

### 3. Decime `.env`

```env
TTS_PROVIDER=orpheus
ORPHEUS_TTS_BASE_URL=http://localhost:5005
ORPHEUS_TTS_VOICE=javi
ORPHEUS_TTS_MODEL=orpheus
ORPHEUS_OLLAMA_MODEL=sematre/orpheus:it_es
```

Перезапустите uvicorn Decime. `GET /health` → `tts_provider: orpheus`.

---

## Итоговая локальная схема

| Задача | Провайдер |
|--------|-----------|
| STT | `faster_whisper` |
| Compose + training extract | Ollama `llama3.2:3b` |
| TTS (озвучка) | Orpheus `javi` / `sergio` / `maria` |

OpenAI ключ **не нужен** для TTS, если Orpheus запущен.

---

## Если Orpheus-FastAPI не стартует

- Убедитесь, что Ollama работает: `ollama list` показывает `sematre/orpheus:it_es`
- Orpheus-FastAPI и Decime API — **разные процессы** на портах **5005** и **8000**
- На CPU генерация медленнее; первый запрос может занять 30–60 с
