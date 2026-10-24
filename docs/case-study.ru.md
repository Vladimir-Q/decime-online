# Инженерный case study: проектирование и оценка Decime UY

**От локально-ориентированного перевода к проверяемому и наблюдаемому LLM-приложению**

[English version](case-study.md) · [README](../README.ru.md) · [Индекс документации](README.md)

Документ описывает, как устроен Decime UY, какие компромиссы приняты, как измерялось качество LLM и что остаётся ограниченным. Утверждения ниже опираются на код, тесты или артефакты оценки в этом репозитории.

---

## 1. Проблема и требования

Уругвайский испанский (особенно монтейвидеоский риоплатенсе) не сводится к «общему латиноамериканскому» в бытовом чате. *Voseo*, неформальный регистр и локальные формулировки влияют на то, звучит ли ответ естественно в WhatsApp или лично. Нужны и **семантическая верность**, и **упрощённый A2**-вариант для более слабого уровня языка.

Одного промпта вида «переведи на уругвайский испанский» для продукта недостаточно, потому что:

- входящий и исходящий потоки разные (`understand_incoming` vs `translate_to_esuy`);
- UI ожидает **стабильный JSON** (перевод, тона, кандидаты в training), а не свободный текст;
- речь (STT/TTS) и личный словарь делят те же контракты API;
- при сравнении моделей нужно знать **какая ревизия промпта** дала конкретный выход.

Продуктовый scope: [product_brief.md](product_brief.md), [project_state.md](project_state.md).

---

## 2. Архитектура и решения

### Граница FastAPI

API (`apps/api`) разделяет routers, сервисы, интерфейсы провайдеров и persistence. Text LLM, STT и TTS заменяемы; Fake-реализации позволяют гонять CI без платных вызовов. См. [development_brief.md](development_brief.md), [api_contracts.md](api_contracts.md).

**Компромисс:** тонкий Next.js-клиент держит LLM-границу на сервере (схемы, retry, usage). Цена — единая дисциплина API для web и mobile.

### LangChain без разрастания агентов

Текст идёт через LangChain `ChatOpenAI` при `LLM_ORCHESTRATOR=langchain` — единственный разрешённый orchestrator ([langchain_migration_status.md](langchain_migration_status.md)). Это composable chat + structured output, не multi-agent planner.

**Компромисс:** меньше «магии» фреймворка, понятнее стектрейсы. Сложные tool-calling агенты отложены: продукту важнее детерминированные контракты translate/understand/extract.

### Structured Outputs

Ответы ограничены JSON Schema и `strict=True` в [`structured_chat.py`](../apps/api/src/decime_api/services/ai/lc/structured_chat.py) и [`llm_json_schemas.py`](../apps/api/src/decime_api/services/ai/llm_json_schemas.py).

**Компромисс:** меньше ошибок парсинга; качество перевода схемы **не** гарантируют — нужна human- и judge-оценка.

### Речь отдельно от текста

STT и TTS — независимые провайдеры. Ollama **не** используется для translate/understand. Text-only локальный запуск возможен без голоса ([local_stt_setup.md](local_stt_setup.md), [orpheus_tts_setup.md](orpheus_tts_setup.md)).

### PostgreSQL

В production — auth, история, training, асинхронные jobs словаря. Локально auth можно выключить. См. [database_schema.sql](database_schema.sql), [vm_auth.md](vm_auth.md).

### Deploy

Compose в [`deploy/`](../deploy/): API, web, Postgres, Caddy, речь, опциональный Cloudflare tunnel. Ожидания по безопасности — [security_brief.md](security_brief.md), без заявлений о enterprise HA.

---

## 3. Промпты и версионирование

### Проблема воспроизводимости

Поведение зависит и от markdown system-промптов, и от human-инструкций, собранных в Python (канал, уровень, A2, Spanish-retry). Ранние трейсы не фиксировали неизменяемую ревизию промпта.

### Решение

Четыре приватных LangSmith-промпта как `ChatPromptTemplate`; тег окружения резолвится в **commit hash один раз при старте процесса**. Подробности: [langsmith_prompt_management.md](langsmith_prompt_management.md); код — [`prompt_templates.py`](../apps/api/src/decime_api/services/ai/lc/prompt_templates.py), [`prompt_provider.py`](../apps/api/src/decime_api/services/ai/lc/prompt_provider.py), [`prompt_hub.py`](../apps/api/src/decime_api/services/ai/lc/prompt_hub.py).

| Механизм | Роль |
|----------|------|
| Prompt commit (`commit_hash`) | Неизменяемый id ревизии |
| Теги `staging`, `v1-0-0` | Указатели окружения / semver (дефисы: точки в тегах LangSmith запрещены) |
| Local snapshots | JSON в [`prompts/snapshots/`](../apps/api/src/decime_api/prompts/snapshots/) — fallback только при совпадении hash |
| `schema_sha256` | Хэш JSON-схемы в Python, отдельно от текста промпта |
| Code revision | `git rev-parse HEAD` или `DECIME_CODE_REVISION` |

Промпт **не** тянется на каждый запрос пользователя: резолв тега привязан к lifetime процесса.

### Статус активации в production (явно)

Инфраструктура Prompt Management есть в репозитории; приватные промпты с `staging` / `v1-0-0` на baseline-коммитах существуют. **Runtime по умолчанию: `DECIME_PROMPT_SOURCE=local`.** Тег `production` не создавался. Переключение на VM — только явное решение владельца и рестарт ([project_state.md](project_state.md)).

---

## 4. Методология LLM evaluation

Пилот октября 2026: два комплементарных **реальных** эксперимента и отдельные **симуляции**. Спека: [llm_eval_pilot_spec.md](llm_eval_pilot_spec.md), отчёты [1](llm_eval_report1.md)–[4](llm_eval_report4.md).

### Зачем два метода

| Метод | Зачем | Ограничения |
|-------|-------|-------------|
| **Human pairwise** | Субъективный стиль / разговорность | Дорого; один аннотатор → нет IAA |
| **LLM-as-a-Judge** | Масштабируемые числовые критерии | Bias судьи; коррелированные ошибки |

Изначально рассматривалась четырёхкритериальная human-рубрика. **Завершённый** human-эксперимент зафиксирован на **одном критерии: style preservation** ([report1_human.json](../apps/api/evals/reports/pilot-2026-10/report1_human/report1_human.json), поле `criteria_note`).

### Конфигурация (реально)

**Эксперимент 1 — Human:** suite `esuy_ru_human_v1`, es-UY → RU; A=`gpt-5.6-luna`, B=`gpt-6-luna`; N=30; аннотатор — владелец проекта.

**Эксперимент 2 — Judge:** suite `ru_esuy_judge_v1`, RU → es-UY; те же кандидаты; judge=`gpt-5-mini`; 30 кейсов / 60 переводов; критерии 1–5; structured judge + usage/cost в Stage 5.

Общие практики: выровненные case id, pair integrity ([`pair_integrity.py`](../apps/api/src/decime_api/evals/pair_integrity.py)), LangSmith Datasets/Experiments и PAQ.

---

## 5. Результаты и выбор модели

### Human preference по стилю (реально)

| Исход | Число |
|-------|------:|
| A better (`gpt-5.6-luna`) | 9 |
| B better (`gpt-6-luna`) | 18 |
| Equal | 3 |

Источник: [`report1_human.json`](../apps/api/evals/reports/pilot-2026-10/report1_human/report1_human.json). Агрегаты: Equal = 3, `equal_rate = 0.1`. Ранее summary показывал Equal = 0 из‑за несовпадения ключей `Equal` / `equal` — дефект отчётности, пересборка из сохранённых кейсов без новых аннотаций.

**Интерпретация:** в этой выборке B чаще предпочитали по стилю. Это **предпочтение в выборке**, не крупномасштабное доказательство превосходства.

### Средние Judge (реально)

Из [`report2_judge.json`](../apps/api/evals/reports/pilot-2026-10/report2_judge/report2_judge.json):

| Метрика | A | B |
|---------|--:|--:|
| Semantic fidelity | 4.800 | 4.833 |
| UY naturalness | 4.433 | 4.467 |
| Style preservation | 4.700 | 4.933 |
| No additions/omissions | 4.800 | 4.867 |

Пары по semantic fidelity: **3 A / 4 B / 23 equal**. Critical errors: 0/0. Оценка стоимости judge в артефакте: около **$0.11** (`judge_estimated_cost_usd`) — не модель стоимости production-трафика.

### Default в production

Вывод пилота (Report 4): текстовый default → **`gpt-6-luna`**, в первую очередь по human style, с осторожной трактовкой judge. Полной таблицы **latency** кандидатов в артефактах пилота нет — здесь цифры не выдумываются. N=30 явно underpowered для сильных заявлений.

---

## 6. Статистика и неопределённость

Report 3 ([llm_eval_report3.md](llm_eval_report3.md)): **симулированные** 400 human-like и 400 judge-like пар для мощности и type-I. Для small-effect сценария мощность sign-test при N=30 ≈ **0.05**; даже N=400 ниже целевых 80% в том сценарии.

**Симуляции не повышают точность реальных N=30 экспериментов.** Они показывают, насколько мала мощность маленького pairwise-пилота. См. методологию в `apps/api/evals/reports/pilot-2026-10/report4_methodology/`.

---

## 7. Инженерные вызовы и решения

### 7.1 Загрязнение языка ответа LLM

**Проблема.** `translate_to_esuy` иногда возвращал текст на языке UI.  
**Причина.** Несоблюдение локали при смешанном контексте.  
**Решение.** Детект (`reply_language.py`) и один retry с Spanish reinforcement (`openai_llm.py`).  
**Проверка.** `test_reply_language.py`.  
**Остаток.** Эвристика; редкие краевые случаи возможны.

### 7.2 Состояния асинхронных n8n / Sheets jobs

**Проблема.** Гонки callback/timeout выводили jobs из terminal `completed`/`failed`.  
**Причина.** Неатомарные обновления статуса.  
**Решение.** Липкие terminal-переходы `UPDATE … WHERE status = ANY(...)` в [`sheets_jobs.py`](../apps/api/src/decime_api/db/sheets_jobs.py).  
**Проверка.** [`test_sheets_job_transitions.py`](../apps/api/src/decime_api/tests/test_sheets_job_transitions.py).  
**Остаток.** Полный E2E workflow n8n — у оператора.

### 7.3 Учёт стоимости моделей

**Проблема.** Тихий fallback pricing скрывал неизвестные model id.  
**Решение.** Версионированный каталог [`llm_pricing.py`](../apps/api/src/decime_api/services/analytics/llm_pricing.py); unknown → `unknown_price`.  
**Проверка.** `test_llm_pricing.py`.  
**Остаток.** Каталог нужно обновлять при новых id.

### 7.4 Воспроизводимость промптов и CI

**Проблема.** Дрейф текста промптов и версий lint (`ruff` без pin).  
**Решение.** Commit hashes + snapshots; pin `ruff==0.17.1`.  
**Проверка.** `test_prompt_provider.py`; [`.github/workflows/api-tests.yml`](../.github/workflows/api-tests.yml).  
**Остаток.** После prompt-management платные comparative evals намеренно не перезапускались.

---

## 8. Надёжность, приватность и эксплуатация

JWT и изоляция данных пользователей при `AUTH_ENABLED=true` ([vm_auth.md](vm_auth.md)), секреты в env (не в git), опциональный LangSmith tracing, snapshot fallback с проверкой hash, бэкапы Postgres в deploy-скриптах, Fake LLM для бесплатного CI.

Это **не** сертификат безопасности и не multi-region HA. Production — VM одного оператора с задокументированным hardening ([security_brief.md](security_brief.md)).

Трейсы и eval-загрузки могут содержать текст пользователя — ключи и проекты LangSmith нужно считать чувствительными.

---

## 9. Выводы и дальнейшая работа

1. Оценивайте тот путь продукта, который реально отдаёте пользователю.
2. Без версий промпта честные before/after-сравнения невозможны.
3. Structured Outputs стабилизируют интеграцию, а не качество испанского.
4. Сбои надёжности часто вне LLM — state machine jobs, pin CI, каталог цен.
5. Явно формулируйте неопределённость: N=30, много ничьих у judge, один аннотатор.
6. Простая наблюдаемая композиция предпочтительнее лишних agent-фреймворков, пока нет нужды в tools/planning.

Реалистичные следующие шаги: device QA WhatsApp share, опциональный promote тега LangSmith `production`, автоматизация prompt-regression на замороженных датасетах, UX сессий/онбординга, более крупные multi-annotator eval при росте претензий к качеству.

---

## Индекс доказательств

| Тема | Основные источники |
|------|--------------------|
| Архитектура / статус | [project_state.md](project_state.md), [langchain_migration_status.md](langchain_migration_status.md) |
| Промпты | [langsmith_prompt_management.md](langsmith_prompt_management.md), `services/ai/lc/prompt_*.py` |
| Human | `apps/api/evals/reports/pilot-2026-10/report1_human/` |
| Judge | `apps/api/evals/reports/pilot-2026-10/report2_judge/` |
| Симуляции | `apps/api/evals/reports/pilot-2026-10/report3_synthetic/` |
| Методология | [llm_eval_report4.md](llm_eval_report4.md) |
| CI | `.github/workflows/api-tests.yml`, `web-ci.yml` |
| Deploy | `deploy/README.md`, [security_brief.md](security_brief.md) |
