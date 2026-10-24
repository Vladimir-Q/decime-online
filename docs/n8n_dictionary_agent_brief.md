# Бриф: интеграция словаря Decime с n8n и Google Sheets

## Задача и границы

Реализовать изменения приложения. Пользователь собирает workflow n8n вручную по отдельной инструкции. Не создавать и не публиковать workflow автоматически. Не менять существующие функции английской версии; кнопки интеграции показывать только в русском интерфейсе. Не вносить секреты в репозиторий.

Экспорт запускается кнопкой из словаря. Одна вкладка Google spreadsheet на пользователя. При повторном запуске добавлять отсутствующие карточки и обновлять статистику всех существующих карточек; не удалять строки из Google Sheets при удалении карточки в Decime.

Импорт запускается второй кнопкой, пользователь выбирает исходную таблицу и вкладку. Одна непустая строка = одна карточка, включая идиомы и выражения. Входные колонки spanish и russian; остальные колонки, включая статистику, игнорируются. Новые карточки начинают с нулевой статистикой. Дубли пропускаются, существующие переводы и статистика сохраняются. Предоставленный русский перевод сохранять; если пустой — генерировать через существующий AI provider. Сохранять испанское выражение целиком, добавляя артикль и соответствующие грамматические сведения.

## Проверенная инфраструктура

- n8n 2.40.7 и Decime на одной ВМ, Docker.
- Внешняя сеть decime_n8n; n8n и decime-postgres-1 подключены; alias базы decime-db, порт 5432.
- Пользователь decime_n8n_reader имеет SELECT на training_lists, training_items, training_attempts. Запись импорта делать через API приложения.
- Google service account хранится в credentials n8n; чтение и запись проверены.
- Spreadsheet ID: 1FkTZ0ShmhuJTru7BmMn3bSpunuEjiDv3ZmmHca4QIwU.
- Тестовая вкладка: user_811766b0-fc39-40e8-9aa4-3caf7b9fa761. 33 карточки, повторная выгрузка проверена пользователем.
- Export webhook: POST /webhook/decime/dictionary/export (production); /webhook-test/decime/dictionary/export (test).
- Header Auth: X-Decime-Automation-Key. Секрет хранится в n8n и в окружении backend, никогда в браузере.
- Тестовый webhook вернул HTTP 200. Пока SQL и вкладка используют фиксированный тестовый словарь; это НЕ готовая многопользовательская интеграция.
- На ВМ Compose Decime работает из /home/telar/decime/deploy, .env находится там же. Сеть вручную добавлена пользователем в Compose; не перезаписывать его настройки.

## Исходный код

Проверить актуальное состояние перед изменениями:

- apps/web/src/features/training/DictionaryPanel.tsx — кнопки и текущий list_id.
- apps/web/src/lib/api.ts — запросы frontend.
- apps/api/src/decime_api/routers/training.py — пользовательские маршруты.
- apps/api/src/decime_api/auth/dependencies.py — CurrentUser, JWT.
- apps/api/src/decime_api/db/postgres_training.py — изоляция по user_id/list_id.
- apps/api/src/decime_api/services/training/training_service.py — извлечение, добавление, дубли.
- apps/api/src/decime_api/services/training/canonical.py — канонические ключи.
- apps/api/src/decime_api/schemas/training.py и services/ai/llm_json_schemas.py — поддерживаемые типы.
- apps/api/src/decime_api/prompts/extract_training_items.md — текущий промпт исключает идиомы.
- apps/api/src/decime_api/services/training/review.py — тренировочные попытки.

Нельзя просто вызывать add-to-vocab для каждой строки: текущий extractor может разбить её на несколько карточек. Добавить отдельный режим нормализации одной карточки, переиспользуя провайдер и грамматические правила. Для идиом и выражений добавить подходящие типы во все необходимые схемы, AI-ответы, UI, canonical key и тренировочную очередь. Обычное извлечение из текстов не должно регрессировать. В базе встречаются существительные, где grammar.article есть, но display_text без артикля; новая нормализация должна формировать текст последовательно, без удвоения артикля. Массовое исправление существующих карточек не входит в задачу.

## Контракт приложения и n8n

Предлагаемые маршруты под /api/v1; согласовать любые изменения контракта перед сборкой рабочих workflow.

1. POST /training/sheets/export, JWT пользователя; body {list_id}. Backend проверяет владельца списка, определяет user_id из сессии и spreadsheet_id из серверной настройки. Клиент не выбирает user_id. Создать persisted job и отправить запрос в n8n.
2. POST /training/sheets/import, JWT; body {list_id, source_spreadsheet_id, source_sheet_name}. Проверить владельца списка и формат источника; создать persisted job.
3. GET /training/sheets/jobs/{job_id}, JWT; только владелец видит статус и отчёт. Статусы queued/running/completed/failed; partial errors отражать в отчёте.
4. GET /integrations/n8n/jobs/{job_id}, Header Auth; возвращает сохранённый контекст job для n8n, включая user_id/list_id. Нельзя доверять произвольному user_id в импортируемой строке.
5. POST /integrations/n8n/jobs/{job_id}/import-row, Header Auth; body {source_row_number, spanish, russian}. Пользователь и список берутся из job. Вернуть {status: created|skipped_duplicate|error, item_id?, message?}. Обрабатывать строки последовательно, повтор одного job+source_row_number не должен создавать карточку повторно. Не доверять canonical_key/item_id из источника; вычислять самостоятельно. Конкурентные дубли обработать с учётом уникального индекса базы.
6. POST /integrations/n8n/jobs/{job_id}/complete, Header Auth; body со статусом и отчётом. Должен поддерживать повтор callback без порчи состояния; терминальные состояния защищать от запоздалых запросов. Не принимать результат импорта без учёта обработанных строк.

Backend -> n8n export body:

```json
{"job_id":"UUID","user_id":"UUID","list_id":"UUID","spreadsheet_id":"configured ID","sheet_name":"user_USER_UUID"}
```

Backend -> n8n import body:

```json
{"job_id":"UUID","source_spreadsheet_id":"ID","source_sheet_name":"name"}
```

n8n импорт получает контекст из job; экспорт использует параметры backend и SQL placeholders. Никогда не пересылать пользовательский JWT в n8n. Header Auth проверять constant-time. Входные server-to-server маршруты доступны только с отдельным секретом; если он не задан, закрыты. Публичные кнопки требуют реального авторизованного пользователя даже при AUTH_ENABLED=false.

Для обеих операций вернуть frontend HTTP 202 с job_id после подтверждённого принятия n8n. Webhook должен быстро подтверждать принятие; текущий режим When Last Node Finishes использован только в тесте. Ошибку связи записывать в job и показывать пользователю. Не выполнять длительный импорт внутри frontend HTTP-запроса. Не использовать недолговечные фоновые задачи как единственное хранилище прогресса. Защитить повторное нажатие/одновременный экспорт одного пользователя; пустой словарь также должен завершать job. Предусмотреть таймаут потерянного workflow, отчёт ошибок по строкам, разумные лимиты и retry без дублей.

## Настройки окружения и сеть

Добавить документированные серверные настройки: N8N_EXPORT_WEBHOOK_URL, N8N_IMPORT_WEBHOOK_URL, N8N_AUTOMATION_KEY, GOOGLE_DICTIONARY_SPREADSHEET_ID. URL задаётся администратором, не клиентом. Для callback определить внутренний URL API, например http://decime-api:8000/api/v1; alias decime-api потребуется добавить API в сеть decime_n8n. n8n доступен API по http://n8n:5678, если API подключён к этой сети. Подготовить изменение Compose и .env.production.example, не публиковать PostgreSQL наружу. Секрет не логировать, ошибки n8n не должны раскрывать credentials.

## Формат экспортной вкладки

Заголовки: item_id, canonical_key, spanish, russian, item_type, grammar, attempts, again, hard, good, easy, success_percent, hints, last_review_at, review_stage, next_review_at.

spanish = display_text; russian = translations_ru, соединённые через '; '; grammar = JSON. attempts = все попытки; распределение по again/hard/good/easy; успешной считается только easy. success_percent = easy / attempts * 100 с округлением до одного знака, пусто при нуле попыток; hints = количество used_hint; last_review_at = максимальный created_at попытки; даты ISO UTC. В SQL соединять по item_id И user_id. Все строки только указанного владельца и списка.

Сопоставление Google Sheets по item_id. Вкладка user_<полный UUID пользователя>, автоматически создавать при отсутствии с заголовками. У пользователя может быть несколько списков: экспорт выбранного списка дополняет его общую вкладку; не удаляет строки остальных списков. Одновременные экспорты в одну вкладку сериализовать. Значения писать как текст/RAW там, где возможно, чтобы выражения и переводы не превращались в формулы Google Sheets.

## Приёмка

- Изоляция пользователей: чужие list_id/job_id отклоняются, user_id берётся из JWT.
- Два экспорта не создают дубли, новые карточки добавляются, статистика обновляется, пустой словарь завершает job.
- Кнопки и понятный прогресс только в русской версии; состояния ошибки/частичного импорта, счётчики created/skipped/errors.
- Импорт noun с/без артикля, verb form, adjective, идиомы: строго одна карточка из строки; supplied russian сохраняется; пустой перевод генерируется.
- Статистика источника не переносится; существующие карточки не изменяются; повторы и конкурирующие импорты не создают дублей.
- Проверить unsupported/empty rows, AI/network errors, retries, invalid secret, отсутствие настроек, timeout.
- Использовать fake AI и mock n8n для тестов; не обращаться к реальной Google-таблице в автотестах. Выполнить релевантные backend/frontend проверки проекта.
- Обновить docs/n8n_workflows.md: текущая фраза «runtime does not call n8n» после реализации станет неверной. Документировать окончательный контракт и ручную настройку workflow, сообщить отличия от этого брифа.

Доставить изменения приложения, миграции, инструкции развёртывания и итоговый проверенный контракт. Google и n8n пользователь настраивает вручную; не заявлять сквозную готовность до проверки рабочих workflow.
