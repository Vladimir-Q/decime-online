# Decime UY — Продуктовый отчёт о состоянии разработки

**Дата:** 2026-10-17 (обновление согласованности с кодом; исходный отчёт 2026-06-24)  
**Версия продукта:** MVP 0.2 / app ~2.5.x (production + pre-beta polish)  
**Аудитория:** владелец продукта, стейкхолдеры

---

## 1. Что такое Decime UY

**Decime UY** — копилот для уругвайского испанского (Монтевидео): понять входящее сообщение, сформулировать ответ на es-UY, озвучить, выучить отдельные слова и формы через spaced repetition.

Обещание продукта:

> **Ответь сейчас. Учись на каждом ответе. Говори быстрее в следующий раз.**

Целевой пользователь MVP: иммигрант в Уругвае (RU/EN → es-UY), WhatsApp и бытовое общение, уровень ~A2.

---

## 2. Статус фаз MVP

| Фаза | Название | Статус | Комментарий |
|------|----------|--------|-------------|
| 0 | Skeleton, документация | ✅ | Репозиторий, briefs, схема БД |
| 1 | Текстовый composer | ✅ | Один ответ es-UY + тон, история |
| 2 | Аудио STT/TTS | ✅ | Загрузка, транскрипция, синтез, кэш |
| 3 | Add to training | ✅ | Извлечение, одобрение, списки |
| 4 | Review + SRS | ✅ | Очередь, режимы, оценки |
| 5 | WhatsApp / Quick Reply | ✅ | Web + APK; **device QA** открыт |
| 6 | Auth + VM | ✅ | JWT, Postgres, `decime.online` |
| 7 | Persistence | ✅ | Training, history, event_log per user |
| 8 | Pre-beta polish | 🚧 | Live Chat, UI EN, prod fixes |
| — | Twilio / Palabra | ⛔ | [out_of_scope.md](../out_of_scope.md) |

---

## 3. Экраны и пользовательские сценарии

### 3.1 Веб (production: `https://decime.online`)

| Маршрут | Назначение | Ключевые действия |
|---------|------------|-------------------|
| `/login/` | Вход | Email/пароль |
| `/app/` | Dashboard | Обзор модулей |
| `/app/quick-reply/` | **WhatsApp-сценарий** | Входящее → перевод → ответ es-UY → copy / audio / training |
| `/app/live/` | **Live Chat** | Микрофон или текст; ES↔RU/EN; выбор микрофона (web) |
| `/app/training/` | Список фраз | Items, Due count, Review now |
| `/app/training/review/` | Повторение | SRS-сессия |
| `/app/history/` | История | Compose history, clear |
| `/app/settings/` | Язык UI + logout | Без поля API URL |
| `/app/diagnostics/` | Диагностика | Health, probes; на dev APK — Scan/manual API URL |
| `/app/admin/users/` | Admin | CRUD пользователей |
| `/app/compose`, `/app/audio` | Legacy | Redirect → Live Chat |

**Навигация (web):** Dashboard · Quick Reply · Live Chat · History · Training · Diagnostics · Settings

**Мобильная сборка (APK):** Quick Reply · Live Chat · Training · History · Settings (parity с web; API URL — Diagnostics на `-Dev` сборках)

### 3.2 Android (Capacitor APK)

| Возможность | Статус |
|-------------|--------|
| Установка APK | ✅ |
| Share текста из WhatsApp → Quick Reply | ✅ |
| Share аудио → STT | ✅ (зависит от устройства) |
| Share ответа в WhatsApp | ✅ |
| HTTPS API (`api.decime.online`) | ✅ |
| JWT auth | ✅ |

### 3.3 Сквозной сценарий приёмки MVP

| Шаг | Реализовано |
|-----|-------------|
| 1. Вставить/загрузить сообщение | ✅ |
| 2. Увидеть перевод/транскрипт | ✅ |
| 3. Сгенерировать один ответ es-UY (тон) | ✅ |
| 4. Прослушать ответ | ✅ (JWT; Play для сохранённого аудио) |
| 5. Скопировать в WhatsApp | ✅ |
| 6. Add to training | ✅ |
| 7. Кандидаты (noun, adj, verb) | ✅ |
| 8. Одобрить выбранные | ✅ |
| 9. Review с аудио | ✅ |

**Пробел:** официальный QA на физическом телефоне не закрыт.

---

## 4. Production

- **Web:** `https://decime.online`
- **API:** `https://api.decime.online`
- **LLM:** OpenAI `gpt-6-luna`
- **STT:** faster-whisper (local on VM)
- **TTS:** Orpheus (local on VM)
- **E2E:** 14/14 checks pass (`scripts/vm_internal_e2e.py`)

---

## 5. Что сознательно не в продукте

- Бот WhatsApp (Twilio, Meta API)
- Palabra.ai
- Отправка сообщений от имени пользователя
- Мультирегион (только es-UY-montevideo)
- PWA offline

---

## 6. Риски и открытые вопросы

| Риск | Митигация |
|------|-----------|
| Качество UY vs LATAM | Промпты + dialect stamp |
| WhatsApp не шарит голосовые | Upload audio, paste |
| Device QA не закрыт | [android_setup.md](../android_setup.md) |
| Beta UX не готов | Phase 8: onboarding, Assistant refactor |

---

## 7. Следующие шаги

1. Device QA на телефоне против HTTPS VM
2. Product task: unified Assistant, sessions, onboarding
3. Скрыть diagnostics/LAN в prod mobile
4. Beta: 5–10 пользователей

---

## 8. Связанные документы

- [project_state.md](../project_state.md) — snapshot для агентов
- [mvp_tasks.md](../mvp_tasks.md) — чеклист фаз
- [technical_status_report.md](technical_status_report.md) — технический отчёт
- [deploy/README.md](../../deploy/README.md) — деплой на VM
