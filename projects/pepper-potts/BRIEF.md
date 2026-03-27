# Pepper Potts — Project Brief

_Сохранено: 2026-03-24_

## Идея

Продуктизация personal AI-агента с голосовыми возможностями и управлением памятью.

Рабочий прототип:
- Говоришь голосом → агент слышит, отвечает голосом, запоминает
- Живёт в Telegram, управляет памятью, следит за проектами
- Разворачивается на своём сервере

**Цель:** упаковать в продукт, который разворачивается за 5-10 минут через визард. Без ручного хардкода.

## Готовые артефакты

### Voice транспорт
- `telegram_bot.py` — PTT бот (@alena_ai_ptt_bot): голос → STT → LLM (Groq Scout) → TTS → голос в ответ, транскрипты → Telegram топик Interactions
- `jarvis.py` — десктопная версия (микрофон)
- `search.mjs` — умный поиск: Brave API → Playwright fallback → wttr.in / CoinGecko роутинг

**Стек:** Yandex STT (~500ms) + Groq Scout (~230ms) + Yandex TTS Alena (~350ms)
**Итого:** ~1.5с без поиска, ~5с с tool call

### Агент (OpenClaw)
- `workspace-alena/` — SOUL.md, AGENTS.md, IDENTITY.md, USER.md
- `ops/sync-topics.py` — синхронизация топиков в memory/ (full 1000 при старте / since инкремент)
- `ops/watched-topics.json` — конфиг отслеживаемых топиков
- `ops/state.json` — last_message_id для каждого топика
- `memory/` — interactions.md, assistant.md, context.md и др.
- `skills/topic-watcher/` — добавление топиков в мониторинг

**Автозапуск:** alena-ptt-bot.service (systemd user)
**OpenClaw cron:** sync-topics каждые 10 мин, no-deliver

## Что нужно продуктизировать

| # | Параметр | Статус |
|---|----------|--------|
| 1 | TG_BOT_TOKEN | ✅ в .env |
| 2 | YANDEX_API_KEY | ✅ в .env |
| 3 | GROQ_API_KEY | ✅ в .env |
| 4 | BRAVE_API_KEY | ✅ в .env |
| 5 | ID группы Telegram | 🔲 → конфиг/визард |
| 6 | ID топика Interactions (508) | 🔲 → конфиг/визард |
| 7 | ID топика Assistant (391) | 🔲 → конфиг/визард |
| 8 | Имя агента ("Алёна") | 🔲 → конфиг/визард |
| 9 | Userbot сессия Pyrogram | 🔲 → генерируется при настройке |
| 10 | SIP аккаунт (host/user/pass) | 🔲 → конфиг/визард |

Системные топики создаются автоматически визардом.
Проектные топики — пользователь добавляет через skill topic-watcher.

## Открытые задачи перед продуктизацией

- 🔴 Алёна инициирует звонок сама (AGI/AMI) — для напоминаний и проактивных уведомлений
- 🔴 Приветствие при входящем звонке
- 🟡 SIP провайдер с реальным номером (Zadarma / Telnyx)
- 🟡 Улучшить Playwright fallback в search.mjs

## Структура репозитория (предлагаемая)

**Актуальная структура на диске (24.03.2026):**
```
/home/dima/jarvis-voice/
├── alena_core.py       ← общий модуль: STT + LLM + TTS + tool calling
├── telegram_bot.py     ← PTT бот (@alena_ai_ptt_bot), использует alena_core
├── asterisk_agi.py     ← SIP AGI скрипт, использует alena_core
├── jarvis.py           ← десктоп (микрофон), использует alena_core
├── search.mjs          ← умный поиск: Brave → wttr.in/CoinGecko → Playwright fallback
├── .env                ← TG_BOT_TOKEN, YANDEX_API_KEY, GROQ_API_KEY, BRAVE_API_KEY
└── AGENTS.md           ← контекст проекта для агентов

Asterisk:
/etc/asterisk/extensions.conf   ← SIP dialplan → AGI
/etc/asterisk/sip.conf          ← SIP аккаунт для Linphone

Systemd:
~/.config/systemd/user/alena-ptt-bot.service  ← автозапуск PTT бота
```

**Предлагаемая структура репозитория `voice-agent-kit`:**
```
voice-agent-kit/
├── bot/
│   ├── alena_core.py              ← общий модуль STT→LLM→TTS
│   ├── telegram_bot.py
│   ├── asterisk_agi.py
│   ├── jarvis.py
│   └── search.mjs
├── config/
│   ├── .env.template              ← API ключи
│   └── system_prompt.txt          ← промпт агента
├── asterisk/
│   ├── extensions.conf.template
│   └── sip.conf.template
├── agent/
│   ├── SOUL.md.template
│   ├── AGENTS.md.template
│   ├── HEARTBEAT.md.template
│   └── skills/topic-watcher/SKILL.md
├── ops/
│   ├── sync-topics.py
│   └── watched-topics.json.template
├── setup/
│   └── wizard.py
├── systemd/
│   └── alena-ptt-bot.service.template
└── README.md
```

## Решения принятые в ходе разработки

### TTS v3 streaming — закрыто ❌
Протестировано 24.03.2026. v3 медленнее v1 из-за gRPC overhead (~100ms). Для PTT бота бессмысленно (нужен полный файл для sendVoice). Текущий v1 (~300-400ms) оптимален.

### VAD silence threshold — зафиксировано ✅
- `--silence 1.2` секунды — оптимально для Дмитрия (делает паузы в речи)
- `0.8` пробовали — хуже: обрезает фразы, STT промахивается

### web_search триггер — изменено ✅
Раньше: автоматически при любом непонятном слове
Теперь: только при явном указании ("найди", "поищи"). Иначе спрашивает: "Поискать?"

### SYSTEM_PROMPT — вынесен в config/ ✅
`config/system_prompt.txt` — общий для `telegram_bot.py` и `jarvis.py`
Ключи API: `config/.env` (включая TG_BOT_TOKEN)
Логи сессий: `logs/session_YYYY-MM-DD_HH-MM-SS.md` (формат Markdown с таймингами)

### alena_core.py — общий модуль ✅ (24.03.2026)
Ключевой артефакт. Один код для всех транспортов (PTT, SIP, десктоп).

Компоненты:
- STT: Yandex SpeechKit
- LLM: Groq Scout (разговор) / Claude Sonnet (поиск, сложные вопросы)
- TTS: Yandex
- Tool calling: `web_search` (wttr.in / CoinGecko / Brave), `get_datetime`
- Транскрипты → топик 508 с меткой [PTT] или [SIP]
- Логирование модели и задержек

Логика выбора модели:
- **Groq Scout** (~230ms) — обычный разговор
- **Claude Sonnet** — если запрос содержит "найди/поищи/search" ИЛИ `carry=True`
- `carry=True` устанавливается когда предыдущий ответ был от Sonnet (контекст держится)

### Качество поиска — 🟡 в работе
Playwright fallback нужно улучшить.

### Суммаризация — вынесена в отдельный агент
Не задача транспортного уровня. Обсуждается в другом контексте.

## Транспорты (параллельные, оба пишут в Interactions)

### PTT Telegram ✅ — готово
Атомарные задачи, быстрые вопросы. Голосовуха → ответ.

### SIP звонок ✅ — готово (24.03.2026)
Asterisk + Linphone, звонки работают. Транскрипты с меткой [PTT] / [SIP] → топик 508.

**Открытые задачи по SIP** → см. раздел "Открытые задачи перед продуктизацией"

## Каналы взаимодействия

### Interactions (топик 508)
- Пишет только PTT бот (@alena_ai_ptt_bot)
- Содержит: транскрипты голосовых, ответы бота, логи tool calls
- "Сырой" голосовой поток
- Агент читает как источник данных, сам не пишет
- Формат: `[время] Дмитрий: ...` / `[время] Алёна (PTT бот): ...`

### Assistant (топик 391)
- Здесь живёт агент OpenClaw (Алёна)
- Основной канал текстового общения: задачи, вопросы, статусы, стратегия
- Агент читает и пишет сюда
- Сюда приходят cron-репорты, напоминания, алерты
- "Голова" системы — осмысление и принятие решений

### Связь между ними
```
PTT бот → Interactions → sync-topics.py (каждые 10 мин) → memory/interactions.md → агент в Assistant видит в памяти → реагирует
```

При продуктизации: оба топика создаются автоматически визардом.

## Скиллы агента

### ✅ Реализован

**skills/topic-watcher/SKILL.md**
- Добавить/удалить топик в мониторинг
- Найти ID топика через userbot
- Первичная загрузка 1000 сообщений при подписке
- Ручная синхронизация: limit N / since-date
- Триггер: "следи за тредом X", "добавь топик", "подпишись на..."

### ⚠️ Нужно восстановить

**skills/save-context/SKILL.md**
- Стандартная процедура сохранения контекста после рабочей сессии
- Что куда писать: context.md / project-*.md / YYYY-MM-DD.md
- Правило: никогда не говорить "запомню" без записи в файл
- Как создавать cron-напоминания
- Триггер: "запомни", "сохрани", "зафиксируй", конец рабочей сессии
- Статус: создавался Алёной в ходе сессии, но не выжил после сброса

### 📋 Добавить при продуктизации

- **summarize-interactions** — обработка транскриптов из Interactions: классификация → задача / идея / саммари
- **remind** — стандартная процедура постановки напоминаний (cron vs HEARTBEAT)
- **project-status** — генерация статус-репорта по проекту из memory файлов

## Детальная архитектура смыслового слоя (24.03.2026)

```
[Voice/PTT/SIP]
    → interactions.md (транскрипты, каждые 10 мин)

[classify-interactions.py] (Claude Opus, каждые 10-30 мин)
    → tasks.md, ideas.md, daily/*.md

[Алёна в Assistant] (heartbeat 10-30 мин)
    ← читает tasks.md, context.md
    → решает что делать
    → exec: cron, alena-call, message, file write

[alena_core.py] (при каждом звонке)
    ← читает context.md, interactions.md (tail)
    → контекстный промпт для LLM
```

### 1. Контекст между звонками

`alena_core.py` перед вызовом LLM читает файлы из `memory/` и формирует system prompt:

```
(system)
Ты Алёна, AI-помощник Дмитрия.

ТЕКУЩИЙ КОНТЕКСТ:
- Последние взаимодействия: {из interactions.md, tail 10-20}
- Открытые задачи: {из context.md}
- Сегодняшний день: {из calendar / today.md, опционально}

[user]
{транскрипт STT}
```

+500-1000 токенов, Groq справится. Транспорт не меняется — только инжект контекста.

### 2. Классификация interactions

**Батчинг по сессии** (не реагировать на каждую фразу — осмысленное саммари после поездки).

Выходной JSON:
```json
[
  {"type": "task", "text": "...", "entities": {"person": "...", "timeframe": "..."}, "action": "create_task"},
  {"type": "idea", "text": "...", "action": "save_to_ideas"},
  {"type": "conversation", "summary": "...", "action": "none"}
]
```

→ пишет в: `tasks.md`, `ideas.md`, `daily/YYYY-MM-DD.md`

### 3. Двунаправленность (Алёна звонит)

`alena-call.py` — output канал, не автономный модуль. Агент решает → вызывает скрипт.

Триггеры:
- Cron-напоминание → `alena-call.py message "..."`
- Urgent task → агент видит при heartbeat → `exec alena-call.py`

### 4. Структурированный вывод (промпт для Opus)

```
Разбери транскрипт. Верни JSON:
{
  "intents": [...],
  "entities": {"people": [...], "places": [...], "dates": [...], "topics": [...]},
  "action_items": [...]
}
```

Из "надо встретиться с Сашей на следующей неделе обсудить контракт" → event + task + контакт. CRM-функция.

### 5. Execution layer

**Выбран Вариант A: Агент OpenClaw (Алёна в Assistant)**
- classify-interactions кладёт структуру в файлы
- Агент видит новые `tasks.md` при heartbeat
- Агент решает: сделать сейчас / напомнить / отложить
- Агент вызывает: cron, alena-call, message

Вариант B (отдельный daemon) — отклонён, добавляет сложность без пользы.

**Алёна = мозг. classify-interactions = глаза/уши. alena-call = рот.**
LLM не экономим — Opus для классификации (Max тариф).

## Roadmap (переработан 24.03.2026)

---

### Phase 0: Фундамент — убедиться что данные вообще есть

Прежде чем грузить контекст в LLM — проверить что он формируется.

**0.1 Аудит memory/ файлов**
- Проверить что `interactions.md` реально наполняется после звонков
- Проверить наличие и содержимое `context.md` — если нет, создать вручную с правильной структурой
- `today.md` — решить нужен ли отдельный файл или достаточно `daily/YYYY-MM-DD.md`
- Выход: чёткое понимание что есть, в каком формате, и что нужно доделать

**0.2 Определить формат context.md**
- Структура: открытые задачи, текущий фокус, важные факты о пользователе
- Кто обновляет: Алёна (агент в Assistant) после рабочих сессий
- Файл: `memory/context.md`

---

### Phase 1: Контекст между звонками (после Phase 0)

**1.1 Контекстный промпт в alena_core.py**
- Перед вызовом LLM читать: `interactions.md` (tail 10-20) + `context.md`
- Формировать system prompt с этим контекстом
- Тест: позвонить и проверить что Алёна помнит предыдущий разговор
- Файл: `alena_core.py`

---

### Phase 2: alena-call.py — исходящие звонки (атомарная, раньше в пайплайне)

**2.1 Реализация alena-call.py**
- AMI интеграция с Asterisk
- Инициирует звонок, говорит текст через TTS
- Файл: `jarvis-voice/alena-call.py`

**2.2 Тест исходящего звонка**
- Запустить вручную: `python alena-call.py "Дмитрий, напоминание: встреча с Сашей"`
- Убедиться что звонок приходит и текст озвучивается

---

### Phase 3: Классификация interactions

Требует итеративной отладки промпта (как и PTT сегодня — потребовалось много тестов).

**3.1 Use cases для тестирования** (определить до написания кода)
Примеры реальных транскриптов → ожидаемый вывод:
- "Напомни купить молоко завтра" → `task`, deadline tomorrow
- "Надо встретиться с Сашей на следующей неделе обсудить контракт" → `task` + entities: person=Саша, topic=контракт
- "Подумать про новый формат отчётов" → `idea`
- Разговор о погоде → `conversation`, action=none

**3.2 Промпт для Opus + структура JSON** (объединено с бывшим п.4)
```json
{
  "intents": ["task|idea|question|conversation"],
  "entities": {"people": [], "places": [], "dates": [], "topics": []},
  "action_items": []
}
```
Промпт обкатывать итеративно на реальных транскриптах из `logs/`.

**3.3 classify-interactions.py**
- Вход: инкремент из `interactions.md`
- Батчинг по сессии (не каждая фраза — саммари после поездки)
- Вызов Opus, запись в `tasks.md`, `ideas.md`, `daily/YYYY-MM-DD.md`
- Файл: `ops/classify-interactions.py`

**3.4 Cron для классификации**
- После sync-topics, `*/10` или `*/30`, только если есть новые записи
- `no-deliver`, тихая работа

---

### Phase 4: Execution layer — "Агент решает"

"Агент решает" — не магия LLM, а набор правил + preferences.

**4.1 Preferences файл агента**
- `agent/preferences.md` — явные правила: что делать с task, idea, urgent
- Пример: "urgent task → позвони немедленно", "idea → сохрани, не беспокой"
- Разграничить: что в безусловную конфигурацию, что в визард при продуктизации

**4.2 Обновить AGENTS.md Алёны**
- При heartbeat: читать `tasks.md` + `preferences.md`
- Логика: task + urgent → `alena-call.py`; task + deadline → cron; idea → в файл
- Скилл: `skills/execute-task/SKILL.md`

**4.3 Триггеры для звонков**
- Urgent task → немедленный звонок
- Напоминание по времени → cron → `alena-call.py`
- Daily brief утром → опционально

---

### Phase 5: Продуктизация (после стабилизации всего выше)

- Вынести в репо `voice-agent-kit`
- Написать `wizard.py`
- Тест на чистой машине

---

## Порядок выполнения

**Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5**

Завтра начинаем с Phase 0 (аудит данных) — без этого всё остальное на песке.
