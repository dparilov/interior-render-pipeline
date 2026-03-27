# Interior Render Pipeline

Система преобразования архитектурных скетчей в фотореалистичные рендеры интерьеров.

## Документация

- [SPEC.md](SPEC.md) — Полная техническая спецификация v1.0-beta
- [skill/](skill/) — OpenClaw skill для ComfyUI

## Архитектура

```
Скетч + ТЗ + Референсы
        ↓
   UperNet + SAM (сегментация)
        ↓
   Opus Vision (верификация масок)
        ↓
   SDXL + Canny + Depth + Regional IP-Adapter
        ↓
   Фотореалистичный рендер
```

## Статус

**v1.0-beta** — в разработке

