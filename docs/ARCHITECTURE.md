# IRP — Architecture

> Контракты между стадиями pipeline

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INPUT                                  │
│  model.skp + ТЗ.md + references/*.jpg                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 0: SCENE GRAPH EXTRACTION                                    │
│  ─────────────────────────────────────────────────────────────────  │
│  Script: irp_extract.rb                                             │
│  Input:  model.skp (открыт в SketchUp)                              │
│  Output: scene_graph.json + beauty.png                              │
│                                                                     │
│  Contract:                                                          │
│  - scene_graph.json содержит ВСЕ entities с PIDs                    │
│  - Рекурсивный обход до 20 уровней вложенности                      │
│  - Каждый entity: pid, type, name, bounds, face_count, position     │
│  - beauty.png = рендер активной Scene (1920×1080)                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: INTELLIGENT MAPPING                                       │
│  ─────────────────────────────────────────────────────────────────  │
│  Executor: Claude Opus с vision                                     │
│  Input:  scene_graph.json + beauty.png + ТЗ.md + references/        │
│  Output: role_map.json                                              │
│                                                                     │
│  Contract:                                                          │
│  - Каждый объект из ТЗ сопоставлен с PID из scene_graph             │
│  - Confidence 0.0-1.0 для каждого маппинга                          │
│  - Excluded[] содержит PIDs служебных объектов                      │
│  - Нет "угадывания" — только явные сопоставления                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: MASK & MODEL EXPORT                                       │
│  ─────────────────────────────────────────────────────────────────  │
│  Script: irp_export.rb                                              │
│  Input:  role_map.json + model.skp (открыт в SketchUp)              │
│  Output: irp_bundle/                                                │
│          ├── manifest.json                                          │
│          ├── beauty.png                                             │
│          ├── masks/*.png (10 бинарных масок)                        │
│          ├── model.dae (камера)                                     │
│          ├── model.fbx (геометрия с именами)                        │
│          └── model.glb (Blender)                                    │
│                                                                     │
│  Contract:                                                          │
│  - Маски = белый объект на чёрном фоне, 1920×1080                   │
│  - Маски учитывают окклюзию (объекты впереди вырезают дырки)        │
│  - manifest.json содержит все PIDs, roles, references, prompts      │
│  - DAE содержит камеру с правильной позицией                        │
│  - FBX/GLB содержат объекты с именами IRP_*                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: VISUAL QA                                                 │
│  ─────────────────────────────────────────────────────────────────  │
│  Executor: Claude Opus с vision                                     │
│  Input:  masks/*.png + beauty.png + ТЗ.md                           │
│  Output: scoring_matrix.json                                        │
│                                                                     │
│  Contract:                                                          │
│  - Каждая маска получает Score 0-100                                │
│  - Score = Coverage×0.4 + Precision×0.4 + Binary×0.1 + Align×0.1    │
│  - Проблемы документируются (hollow, leak, gray, misaligned)        │
│  - Порог прохождения: Score ≥ 95 для всех объектов                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: BLENDER VERIFICATION (optional)                           │
│  ─────────────────────────────────────────────────────────────────  │
│  Script: blender_gamma_export.py                                    │
│  Input:  model.dae (камера) + model.glb (геометрия)                 │
│  Output: blender_masks/*.png                                        │
│                                                                     │
│  Contract:                                                          │
│  - Альтернативный headless pipeline                                 │
│  - Сравнение с SketchUp масками                                     │
│  - Ограничение: Groups → EMPTY (walls, floor теряют mesh)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 5: COMFYUI RENDERING                                         │
│  ─────────────────────────────────────────────────────────────────  │
│  Script: workflow_10zones.json / comfyui-render-bundle.py           │
│  Input:  irp_bundle/ + references/                                  │
│  Output: render.png                                                 │
│                                                                     │
│  Contract:                                                          │
│  - ControlNet Canny (0.65) + Depth (0.5) — структура                │
│  - IPAdapterAdvanced × N с attn_mask — материалы                    │
│  - 50 steps base + 12 steps refiner (optional)                      │
│  - Выход: фотореалистичный рендер 1920×1080                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                      │
│  render.png — фотореалистичный интерьер с точными материалами       │
└─────────────────────────────────────────────────────────────────────┘
```

## File Contracts

### scene_graph.json

```json
{
  "version": "gamma",
  "model_name": "string",
  "camera": {
    "eye": [x, y, z],
    "target": [x, y, z],
    "up": [x, y, z],
    "fov": number
  },
  "resolution": [width, height],
  "entities": [
    {
      "pid": number,
      "type": "Group" | "ComponentInstance",
      "name": "string",
      "depth": number,
      "face_count": number,
      "child_count": number,
      "bounds": { "width": mm, "height": mm, "depth": mm },
      "position": [x, y, z],
      "volume": number,
      "world_transform": [[4x4 matrix]]
    }
  ]
}
```

### role_map.json

```json
{
  "version": "gamma",
  "entities": [
    {
      "pid": number,
      "name": "string",
      "role": "walls" | "floor" | "bathtub" | ...,
      "class": "surface" | "fixture" | "opening",
      "confidence": 0.0-1.0,
      "reference": "path/to/ref.jpg",
      "prompt": "detailed material description"
    }
  ],
  "excluded": [
    { "pid": number, "reason": "string" }
  ]
}
```

### manifest.json (bundle)

```json
{
  "version": 1,
  "scene_name": "string",
  "resolution": [width, height],
  "images": {
    "beauty": "beauty.png",
    "surfaces_only": "surfaces_only.png",
    "fixtures_only": "fixtures_only.png"
  },
  "entities": [
    {
      "pid": number,
      "name": "string",
      "role": "string",
      "class": "surface" | "fixture",
      "mask": "masks/name.png",
      "reference": "references/name.jpg",
      "prompt": "string"
    }
  ]
}
```

## Key Architectural Decisions

### 1. SketchUp as Source of Truth

**Проблема:** Сегментация из растра (UperNet/SAM) даёт ~76% confidence.

**Решение:** Маски экспортируются напрямую из SketchUp геометрии → 100% accuracy.

### 2. PID-based Mapping

**Проблема:** Имена объектов в SketchUp часто пустые.

**Решение:** Используем persistent_id (PID) — уникальный и стабильный.

### 3. Dual ControlNet (Canny + Depth)

**Проблема:** Только Canny теряет глубину/перспективу.

**Решение:** Canny (контуры) + Depth (пространство) = лучшая структура.

### 4. Regional IP-Adapter

**Проблема:** Глобальный IP-Adapter смешивает все материалы.

**Решение:** IPAdapterAdvanced с attn_mask для каждой зоны.

### 5. Groups → Components Conversion

**Проблема:** Groups теряют mesh при экспорте в GLB.

**Решение:** Временная конвертация перед экспортом + откат после.

---

## Phase 5B — Multi-Entity Regional IPAdapter Composition

### Key Distinction

- **Shared IPAdapter Model Loader** — single `IPAdapterModelLoader` node loads the model once
- **Multiple Entity Applications** — each entity gets its own `IPAdapterApply` branch

One shared loader ≠ one adapter application.

### Target Architecture

```
[Shared IPAdapter Model Loader]
           │
           ├── [Entity 1: walls]
           │      ├── LoadImage(walls_ref.png)
           │      ├── LoadImage(walls_mask.png)
           │      └── IPAdapterApply(weight=0.5)
           │
           ├── [Entity 2: floor]
           │      ├── LoadImage(floor_ref.png)
           │      ├── LoadImage(floor_mask.png)
           │      └── IPAdapterApply(weight=0.5)
           │
           ├── [Entity 3: bathtub]
           │      └── ...
           │
           └── [Entity N: ...]
                  └── ...
```

### Graph Layers

1. **Base Layer**
   - Checkpoint, prompts, canny, depth, boundary, base sampler

2. **Entity Composition Layer**
   - Per-entity: reference, mask, regional IPAdapter, weight, chaining

3. **Refinement Layer** (optional)
   - Refiner checkpoint, CLIP encode, refiner sampler, VAE decode

### Entity Ordering Policy

Default order (large → small):
1. Large surfaces (walls, floor, ceiling)
2. Large fixtures (bathtub, shower)
3. Medium fixtures (vanity, toilet)
4. Small fixtures/decor (towel_warmer, basket, mirror)

Configurable via `order_policy`: default | reverse | custom
