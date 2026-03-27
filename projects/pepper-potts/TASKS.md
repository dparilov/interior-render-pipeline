# Pepper Potts — Список задач
_Обновлено: 2026-03-25 (после мёрджа двух ресёрчей)_

---

## Phase 0: Foundation

- [ ] **0.1** Зафиксировать schema `context.md` (YAML, durable facts: фокус / задачи / факты / preferences)
- [ ] **0.2** Скилл `save-context` — стандартная процедура записи контекста после сессий
- [ ] **0.3** Перевести `interactions.md` → `interactions.jsonl` как canonical source (.md = mirror)

---

## Phase 1: Память между звонками

- [ ] **1.1** Зафиксировать schema `voice-context.md` (YAML: current_focus, open_loops, recent_interactions, pending_actions, style_hints)
- [ ] **1.2** `ops/build-voice-context.py` — compiler: context.md + sessions/*.json + tails → voice-context.md
- [ ] **1.3** Inject `voice-context.md` в `alena_core.py` перед каждым LLM-вызовом
- [ ] **1.4** Тест: позвонить → Алёна помнит предыдущий разговор ✅

---

## Phase 2: Классификация interactions

- [ ] **2.1** Промпт для Opus + расширенная JSON schema:
  ```json
  {
    "session_id", "time_range",
    "dominant_intent", "intents[]",
    "entities": {"people","places","dates","projects","topics"},
    "action_items[]": [{"text","owner","due_date","priority","status"}],
    "memory_updates": {"facts[]","preferences[]","open_loops[]"},
    "session_summary", "daily_note"
  }
  ```
  Тестировать на реальных транскриптах из `logs/`
- [ ] **2.2** `ops/classify-interactions.py`:
  - Вход: инкремент из `interactions.jsonl`
  - Граница сессии: transport boundary (hangup) → primary; 30 мин тишины → secondary
  - Watermark в `ops/classify-state.json`
  - Выход: `sessions/SESS_ID.json`, апдейт `tasks.md`, `ideas.md`, `daily/YYYY-MM-DD.md`
- [ ] **2.3** Cron для classify (каждые 10-30 мин, only if new records, no-deliver)
- [ ] **2.4** Скилл `classify-interactions`

---

## Phase 3: Execution layer

- [ ] **3.1** Schema `pending-actions.json` (state machine: proposed → awaiting_confirmation → approved/denied → executing → done/failed)
- [ ] **3.2** `agent/preferences.md`:
  - **Auto-execute:** запись идей, создание напоминаний, сообщения в Telegram
  - **Require approval:** звонки (до накопления паттернов)
  - **Hard rules:** тихие часы 23:00–08:00
- [ ] **3.3** Обновить AGENTS.md / HEARTBEAT.md Алёны: при heartbeat читать tasks.md + preferences.md → execution loop
- [ ] **3.4** Скилл `execute-task`

---

## Phase 4: Исходящие звонки

- [ ] **4.1** `alena-call.py` (библиотека: **asterisk-ami**, не panoramisk)
  - Pre-render TTS → WAV → AMI Originate → dialplan `[alena-outbound]`
- [ ] **4.2** Dialplan в Asterisk для исходящих
- [ ] **4.3** Тест: `python alena-call.py "текст"` → звонок приходит
- [ ] **4.4** Приветствие при входящем звонке
- [ ] **4.5** Скилл `voice-call`
- [ ] **4.6** _(backlog)_ Рефакторинг: вынести `tts.py`, `stt.py`, `llm.py` из alena_core.py

---

## Phase 4B: Звонки от имени Дмитрия (переговорный агент)

_Use case: "Алёна, позвони в ресторан и забронируй столик на двоих в субботу вечером"_

- [ ] **4B.1** Скилл `outbound-call-brief` — формирует brief перед звонком:
  - Кому звонить и зачем
  - Что обязательно сказать / спросить
  - Как представиться ("Я Алёна, ассистент Дмитрия")
  - Что делать если не взяли / неудобно ("во сколько перезвонить?")
  - Brief инжектируется в `voice-context.md` как секция `outbound_call_brief`

- [ ] **4B.2** Дефолтные паттерны звонка в `preferences.md`:
  - Представиться в начале
  - Спросить "удобно ли сейчас говорить"
  - Если нет — уточнить время для перезвона и сообщить Дмитрию
  - Подтвердить договорённость в конце

- [ ] **4B.3** F&F testing phase:
  - Звонки друзьям/знакомым, разбор записей через `classify-interactions.py`
  - Из реальных разговоров формируем паттерны → дополняем `preferences.md`
  - Цель: к реальным деловым звонкам прийти с проверенными дефолтами

- [ ] **4B.4** Скилл `outbound-negotiation` — расширение `voice-call`:
  - Trigger: "позвони и договорись", "забронируй", "узнай"
  - Агент сам составляет brief → аппрув от Дмитрия → звонок

---

## Phase 5: SIP — реальная телефония

- [ ] **5.1** Выбрать провайдера: Zadarma vs Telnyx (обсудить)
- [ ] **5.2** Зарегистрировать номер, настроить SIP trunk в Asterisk
- [ ] **5.3** Входящие: реальный номер → Asterisk → AGI → Алёна
- [ ] **5.4** Исходящие: `alena-call.py` на реальный номер
- [ ] **5.5** Cloudflare Tunnel для webhook (Telnyx) или SIP registration (Zadarma)
- [ ] **5.6** Убрать зависимость от Tailscale и Linphone

---

## Phase 6: Проактивность

- [ ] **6.1** Триггеры для звонков: urgent task → немедленно; deadline завтра → cron
- [ ] **6.2** Daily/weekly саммари из памяти — голосом или текстом в Assistant

---

## Phase 7: Продуктизация

- [ ] **7.1** Репо `voice-agent-kit`
- [ ] **7.2** `wizard.py` (click + questionary): 10 параметров, автосоздание топиков
- [ ] **7.3** Тест на чистой машине

---

## Ключевые решения (не менять без обсуждения)

| Решение | Выбор |
|---|---|
| Canonical interactions | `interactions.jsonl` |
| voice-context формат | YAML |
| Граница сессии | transport boundary + 30 мин тишины |
| AMI библиотека | asterisk-ami |
| Auto-execute | идеи, напоминания, TG сообщения |
| Звонки | через аппрув (пока) |
| Episodic retention | хранить всё |
| Capture-only mode | не делаем (лишняя сложность) |
| TTS рефакторинг | после MVP, в backlog |
