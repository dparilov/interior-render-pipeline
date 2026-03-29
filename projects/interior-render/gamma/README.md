# IRP Gamma — Interior Render Pipeline

> **Статус:** Research MVP — отладка flow, возможен hardcode
> **Спецификация:** [SPEC-v1.0-beta.md](SPEC-v1.0-beta.md)
> **Дата:** 2026-03-29

## Обзор

IRP Gamma — полуавтоматический pipeline для генерации фотореалистичных интерьерных рендеров из SketchUp моделей с точным контролем материалов через референсы.

### Ключевые особенности

- **Authoritative маски** из SketchUp (не сегментация из растра)
- **10-зонный IPAdapter** с attention masks для точных материалов
- **89.4% confidence** (target: 100%)
- **CPU rendering** поддерживается (~2 мин/step)

### Входные данные

| Тип | Описание | Формат |
|-----|----------|--------|
| ТЗ | Описание сцены, объектов, материалов | Markdown |
| Референсы | Фото материалов и товаров | JPG/PNG |
| SKP | SketchUp модель | .skp |
| Рендер | Beauty render из SketchUp | PNG 1920×1080 |

### Выходные данные

| Тип | Описание |
|-----|----------|
| manifest.json | Маппинг PIDs → roles |
| masks/*.png | Бинарные маски объектов |
| render.png | Фотореалистичный рендер |

## Полный Flow

```
┌──────────────────────────────────────────────────────────────┐
│  USER INPUT                                                  │
│  ТЗ.md + references/*.jpg + model.skp                        │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 0: SCENE GRAPH EXTRACTION                             │
│  ────────────────────────────────────────────────────────────│
│  Скрипт: irp_extract.rb                                      │
│  Вход: открытый SKP файл                                     │
│  Выход: scene_graph.json + beauty.png                        │
│                                                              │
│  Данные: PIDs, bounds, face_count, world_transform           │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1: INTELLIGENT MAPPING (Opus Vision)                  │
│  ────────────────────────────────────────────────────────────│
│  Входы: scene_graph.json + beauty.png + ТЗ + референсы       │
│  Выход: role_map.json                                        │
│                                                              │
│  Маппинг: PID 36696 → walls (surface)                        │
│           PID 43754 → bathtub (fixture)                      │
│           PID 27700 → EXCLUDED (Sumele)                      │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 2: MASK & MODEL EXPORT                                │
│  ────────────────────────────────────────────────────────────│
│  Скрипт: irp_export.rb                                       │
│  Вход: role_map.json + открытый SKP                          │
│  Выход:                                                      │
│    • masks/*.png (10 бинарных масок)                         │
│    • manifest.json                                           │
│    • model.dae (камера)                                      │
│    • model.fbx / model.glb (геометрия с IRP_* именами)       │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 3: VISUAL QA & SCORING                                │
│  ────────────────────────────────────────────────────────────│
│  Исполнитель: Claude Opus Vision                             │
│  Метрики: Coverage + Precision + Binary + Alignment          │
│  Выход: Scoring Matrix                                       │
│                                                              │
│  Target: Score ≥ 95 для каждого объекта                      │
│  Текущий: 89.4% avg (window 67, bathtub 75, walls 85)        │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 4: BLENDER VERIFICATION (optional)                    │
│  ────────────────────────────────────────────────────────────│
│  DAE (камера) + GLB (геометрия) → Blender                    │
│  Альтернативный headless pipeline                            │
│                                                              │
│  Статус: 8/10 объектов (walls, floor без mesh в GLB)         │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  PHASE 5: COMFYUI RENDERING                                  │
│  ────────────────────────────────────────────────────────────│
│  Варианты:                                                   │
│    A) Simple: Canny ControlNet + prompt                      │
│    B) 10-Zone: IPAdapterAdvanced × 10 + attn_mask            │
│    C) Layered: Base → Inpaint per zone                       │
│                                                              │
│  + SDXL Refiner (12 steps) опционально                       │
└───────────────────────────┬──────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT                                                      │
│  Фотореалистичный рендер с точными материалами               │
└──────────────────────────────────────────────────────────────┘
```

## Быстрый старт

### Phase 0-2: SketchUp

```ruby
# В Ruby Console:
load 'C:/Users/paril/Downloads/irp_extract.rb'
IRP.extract
# → scene_graph.json + beauty.png

# После получения role_map.json:
load 'C:/Users/paril/Downloads/irp_export.rb'
IRP.load_map('C:/Users/paril/Downloads/irp_bundle/role_map.json')
IRP.export
# → masks/*.png + manifest.json + model.dae/fbx/glb
```

### Phase 5: ComfyUI

```bash
# Простой рендер (без IPAdapter)
curl -X POST http://127.0.0.1:8188/prompt \
  -d @~/ComfyUI/input/irp_gamma/workflow_simple_50steps.json

# 10-зонный рендер (с IPAdapter + masks)
curl -X POST http://127.0.0.1:8188/prompt \
  -d @~/ComfyUI/input/irp_gamma/workflow_10zones.json
```

## Скрипты

| Скрипт | HTTP | Назначение |
|--------|------|------------|
| irp_extract.rb | http://100.96.1.25:9090/irp_extract.rb | Phase 0: extract |
| irp_export.rb | http://100.96.1.25:9090/irp_export.rb | Phase 2: export |
| role_map.json | http://100.96.1.25:9090/role_map.json | PID → role |

## Workflows

| Файл | Описание | Время (CPU) |
|------|----------|-------------|
| workflow_simple_50steps.json | Canny + prompt | ~1.5 часа |
| workflow_10zones.json | 10× IPAdapter + masks | ~2 часа |

## Текущие проблемы

| Объект | Score | Проблема |
|--------|-------|----------|
| window | 67 | Hollow mask (только рамка) |
| bathtub | 75 | Toilet leak, градиенты |
| walls | 85 | Gray tones вместо white |

## Документация

- **Полная спецификация:** [SPEC-v1.0-beta.md](SPEC-v1.0-beta.md)
- **Scoring Matrix:** см. Appendix B в спецификации
- **Hardcoded PIDs:** см. секцию 7 в спецификации

## Скрипты

### SketchUp (Ruby)

- `irp_extract.rb` — Phase 0: экспорт scene_graph.json + beauty
- `irp_export.rb` — Phase 2: экспорт масок по role_map.json

### Linux (Python)

- `vision_mapper.py` — Phase 1: интеллектуальный маппинг через Opus
- `visual_qa.py` — Phase 3: визуальный контроль качества
- `blender_verify.py` — Phase 4: верификация в Blender

## Использование

```ruby
# В SketchUp Ruby Console:
load 'C:/path/to/irp_extract.rb'
IRP.extract   # → scene_graph.json + beauty.png

# Передать файлы мне для Phase 1 (Opus mapping)
# Получить role_map.json

load 'C:/path/to/irp_export.rb'
IRP.load_map('role_map.json')
IRP.export    # → masks/*.png + manifest.json
```

## Структура bundle

```
irp_bundle/
├── manifest.json       # метаданные + маппинг
├── beauty.png          # полный рендер
├── surfaces_only.png   # только surfaces
├── fixtures_only.png   # только fixtures
├── masks/
│   ├── walls.png
│   ├── floor.png
│   ├── bathtub.png
│   └── ...
└── references/         # референсы материалов
    ├── wall_tiles.png
    └── ...
```

## Критерии качества

- Маски бинарные: белый объект на чёрном фоне
- Alignment: маски совпадают с beauty по пикселям
- Coverage: все объекты из ТЗ имеют маски
- Scoring: визуальный контроль Opus ≥ 95%
