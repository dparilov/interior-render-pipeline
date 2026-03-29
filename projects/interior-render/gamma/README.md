# IRP Gamma — Interior Render Pipeline

> Research MVP для генерации фотореалистичных интерьерных рендеров из SketchUp моделей

## Зачем

Превратить SketchUp модель + ТЗ с референсами материалов в фотореалистичный рендер с точным контролем над каждой зоной.

**Ключевая идея:** SketchUp как source of truth для масок, а не сегментация из растра.

## Quick Start

### 1. Подготовка

```
Входные данные:
├── model.skp          # SketchUp модель
├── ТЗ.md              # Описание объектов и материалов
└── references/        # Фото материалов
    ├── floor_tiles.jpg
    ├── wall_tiles.png
    └── ...
```

### 2. Extract (SketchUp)

```ruby
load 'http://100.96.1.25:9090/irp_extract.rb'
IRP.extract
# → scene_graph.json + beauty.png
```

### 3. Map (AI)

Передать AI: `scene_graph.json + beauty.png + ТЗ.md`
Получить: `role_map.json`

### 4. Export (SketchUp)

```ruby
load 'http://100.96.1.25:9090/irp_export.rb'
IRP.load_map('path/to/role_map.json')
IRP.export
# → irp_bundle/ с масками и моделями
```

### 5. QA (AI)

Передать AI: `masks/*.png + beauty.png`
Получить: scoring matrix (target: ≥95 для каждого)

### 6. Render (ComfyUI)

```bash
curl -X POST http://127.0.0.1:8188/prompt \
  -d @workflow_10zones.json
# → render.png
```

## Документация

| Файл | Описание |
|------|----------|
| [SPEC-v1.0-beta.md](SPEC-v1.0-beta.md) | Полная спецификация |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Контракты между стадиями |
| [BUNDLE_SPEC.md](BUNDLE_SPEC.md) | Формат bundle |

## Rendering Pipeline

```
beauty.png
    │
    ├─► Canny ControlNet (0.65) ──► контуры
    │
    ├─► Depth ControlNet (0.5) ──► перспектива
    │
    └─► IPAdapter × N + attn_mask ──► материалы по зонам
                                          │
                                          ▼
                                    KSampler 50 steps
                                          │
                                          ▼
                                    Refiner 12 steps (opt)
                                          │
                                          ▼
                                      render.png
```

## Скрипты

| Скрипт | HTTP | Назначение |
|--------|------|------------|
| irp_extract.rb | [link](http://100.96.1.25:9090/irp_extract.rb) | Scene graph extraction |
| irp_export.rb | [link](http://100.96.1.25:9090/irp_export.rb) | Mask & model export |

## Текущий статус

**Version:** v1.0-beta (Research MVP)

| Метрика | Значение |
|---------|----------|
| Маски SketchUp | 10/10 |
| Avg Score | 89.4% |
| Target Score | ≥95% |
| Rendering | Canny + Depth + IPAdapter |

**Известные проблемы:**
- window.png: hollow mask (67%)
- bathtub.png: toilet leak (75%)
- walls.png: gray tones (85%)

## Ограничения MVP

- Hardcoded PIDs для текущего bundle
- Ручной Phase 1 (маппинг через AI chat)
- CPU rendering (~2 мин/step)
