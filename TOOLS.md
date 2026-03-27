# TOOLS.md - Local Notes

## Отправка файлов в Telegram

Чтобы отправить файл, добавь в ответ на отдельной строке:
```
MEDIA:/путь/к/файлу.ext
```

Пример:
```
Вот готовая презентация.
MEDIA:/home/dima/.openclaw/media/outbound/file.pptx
```

Gateway автоматически отправит файл как приложение к сообщению. Tool `message` для этого НЕ нужен.

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Web Search (Brave)

- Brave API ключ прописан в `~/.openclaw/openclaw.json` → `tools.web.search.braveApiKey`
- Добавлен 2026-03-22, ключ: `BSAHGNQqcGQt7HiSJrSoJ2DsJSGdoWI`
- Бесплатный план: 2000 запросов/месяц
- Если ключ протух → https://api.search.brave.com → "API Keys"

## Headless Browser (Playwright + Chromium)

- Playwright установлен глобально: `/home/dima/.nvm/versions/node/v22.22.0/lib/node_modules/playwright`
- Chromium: `~/.cache/ms-playwright/chromium-1208/`
- Версия: Playwright v1.58.2
- **Важно:** скрипты вне `ops/` не найдут playwright через обычный import.
  Нужно импортировать явно:
  ```js
  import { chromium } from '/home/dima/.nvm/versions/node/v22.22.0/lib/node_modules/playwright/index.mjs';
  ```
  Или запускать скрипт из директории с `node_modules` (например `~/.openclaw/workspace/ops/`)
- Для JS-сайтов (ВТБ, Сбер и т.д.) — использовать Playwright, они не рендерятся через простой web_fetch

## Яндекс Cloud VM — неприкосновенные IP

**VM ID:** `fhm1n6ch1gkk5eqckb73` (зона ru-central1-a)
**Folder:** `b1gvdqihg3a1691k3qgo`
**Cloud:** `b1g9u0f8djb9dlg4kc1n` (komarovoonline)

⛔ НИКОГДА не удалять и не трогать эти адреса:
- `158.160.119.28` — VM #1 (ru-central1-a)
- `158.160.78.168` — VM #2 (ru-central1-b, найден 2026-03-23)
- `158.160.75.142` — VM #3 (ru-central1-b, найден 2026-03-23)

## Datamint

- Dashboard: https://inv.ondatamint.com/dashboard/
- Searcher: https://inv.ondatamint.com/searcher/
- HTTP Basic Auth: `datamint` / `Datamint-d3m0-v8K9q`
- Watchdog скрипты: `~/.openclaw/workspace/ops/datamint-monitor.mjs` и `searcher-monitor.mjs`
- Логи: `~/.openclaw/workspace/datamint-monitor.log` и `searcher-monitor.log`
- Алерты в Telegram: чат `-1003596522926`, топик `41`
- Инвестор: `parilov2026`

Add whatever helps you do your job. This is your cheat sheet.

## Алёна — голосовой PTT бот

- **Бот:** @alena_ai_ptt_bot
- **Token:** `8770656508:AAHpTuXDADfbn9Kjm6HF0cKzlBs6yuhlD8o`
- **Скрипт:** `/home/dima/jarvis-voice/telegram_bot.py`
- **Запуск:** `cd /home/dima/jarvis-voice && source bin/activate && python3 telegram_bot.py`
- **Логи:** `/tmp/tgbot.log`
- **Транскрипты:** топик 508 в Clearmind_projects (-1003596522926)
- **PTT топик:** 406 (этот чат, Voice AI)
- **Важно:** отдельный токен от OpenClaw gateway — не конфликтует
- **OpenClaw gateway бот:** 8337338082:... (НЕ использовать для Алёны)
