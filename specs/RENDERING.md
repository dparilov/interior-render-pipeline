# IRP Gamma — Rendering Decisions

> Какие объекты как рендерятся и почему

## Entity Classes и Render Modes

### Классификация

| Class | Примеры | Характеристика |
|-------|---------|----------------|
| **surface** | walls, floor, ceiling | Большие плоскости, повторяющиеся паттерны |
| **fixture** | bathtub, vanity, mirror | Отдельные объекты, уникальная форма |
| **opening** | window, door | Проёмы, источники света |

### Render Modes

| Mode | Применение | IP-Adapter Weight | Примечание |
|------|------------|-------------------|------------|
| `regional_ipadapter` | fixture, small surface | 0.4-0.6 | Стандартный mode |
| `structural_controlnet` | opening | — | Только ControlNet, без IP-Adapter |
| `tiling_projection` | floor, wall_tiles | 0.3-0.4 | Future: проекция тайлов |
| `local_inpaint` | faucet, detail | 0.5-0.7 | Future: послойный inpaint |

## Стратегия по классам

### Surfaces (walls, floor)

**Проблема:** Большие площади с повторяющимся паттерном. IP-Adapter склонен к "размазыванию" текстуры.

**Текущий подход (MVP):**
- IP-Adapter weight: **0.55**
- ControlNet Canny: **0.65** (сохраняет edges)
- ControlNet Depth: **0.5** (сохраняет перспективу)

**Будущий подход:**
- Tiling projection для точного повторения паттерна
- Меньше style transfer, больше structure preservation

```json
{
  "name": "floor",
  "class": "surface",
  "surface_kind": "floor",
  "render_mode": "regional_ipadapter",
  "ipadapter_weight": 0.55,
  "critical": true
}
```

### Fixtures (bathtub, vanity, mirror)

**Проблема:** Уникальные объекты, важна точность формы и материала.

**Текущий подход (MVP):**
- IP-Adapter weight: **0.45-0.5**
- Локально сильнее reference influence
- attn_mask строго по контуру объекта

**Стратегия:**
- Critical fixtures: weight 0.5
- Secondary fixtures: weight 0.4
- Small fixtures (faucet): weight 0.35

```json
{
  "name": "vanity",
  "class": "fixture",
  "render_mode": "regional_ipadapter",
  "ipadapter_weight": 0.5,
  "critical": true
}
```

### Openings (window, door)

**Проблема:** Источники света, геометрия важнее текстуры.

**Текущий подход (MVP):**
- Только ControlNet (структура)
- IP-Adapter отключен или минимальный (0.2)
- Frosted glass через prompt

```json
{
  "name": "window",
  "class": "opening",
  "render_mode": "structural_controlnet",
  "ipadapter_weight": 0.0,
  "critical": false
}
```

## Приоритизация (Critical vs Secondary)

### Critical Entities

Получают более сильный контроль:

| Entity | Class | Weight | Обоснование |
|--------|-------|--------|-------------|
| floor | surface | 0.55 | Основа композиции |
| walls | surface | 0.55 | Большая площадь |
| vanity | fixture | 0.5 | Фокусная точка |
| mirror | fixture | 0.5 | Фокусная точка |
| bathtub | fixture | 0.5 | Крупный объект |

### Secondary Entities

Могут быть ослаблены или отключены:

| Entity | Class | Weight | Обоснование |
|--------|-------|--------|-------------|
| shower | fixture | 0.45 | Фоновый объект |
| rainshower | fixture | 0.35 | Мелкая деталь |
| towel_warmer | fixture | 0.4 | Периферия |
| basket | fixture | 0.4 | Декор |
| window | opening | 0.0 | Только структура |

## Multi-Pass Rendering (Future)

### Pass 1: Structure + Critical Surfaces

```
Input: beauty.png
ControlNet: Canny (0.7) + Depth (0.5)
IPAdapter: floor (0.6), walls (0.6)
Steps: 30
Output: pass1_structure.png
```

### Pass 2: Critical Fixtures

```
Input: pass1_structure.png
Mode: Inpaint
IPAdapter: vanity, mirror, bathtub
Steps: 20
Output: pass2_fixtures.png
```

### Pass 3: Secondary + Details

```
Input: pass2_fixtures.png
Mode: Inpaint
IPAdapter: shower, basket, towel_warmer
Steps: 15
Output: pass3_final.png
```

**Преимущества:**
- Снижает "конкуренцию" между IP-Adapters
- Каждый pass выгружает модели → RAM не накапливается
- Можно итерировать отдельные passes

## Deterministic Rendering

### Фиксированные параметры

```json
{
  "seed": 42,
  "steps": 50,
  "cfg": 7.5,
  "sampler": "dpmpp_2m_sde",
  "scheduler": "karras"
}
```

### Versioned Output

```
output/
├── irp_gamma_v1_seed42_20260329_1200.png
├── irp_gamma_v1_seed42_20260329_1200_meta.json
└── irp_gamma_v1_seed42_20260329_1200_workflow.json
```

### Meta JSON

```json
{
  "version": "1.0",
  "timestamp": "2026-03-29T12:00:00Z",
  "seed": 42,
  "steps": 50,
  "bundle": "irp_bundle_v1",
  "entities_enabled": ["floor", "walls", "vanity", "mirror", "bathtub"],
  "render_time_sec": 3600
}
```

## Aspect Ratio

### Требование

Сохранять aspect ratio исходного beauty.png:
- 1920×1080 → 16:9
- НЕ приводить к квадрату

### Реализация

```python
# В workflow
width, height = Image.open(beauty_path).size
# НЕ: size = max(width, height); width = height = size
```

### Важность

Квадратный рендер для 16:9 сцены:
- Искажает пропорции
- Меняет композицию
- Перераспределяет внимание модели

## Текущие ограничения MVP

| Ограничение | Влияние | Workaround |
|-------------|---------|------------|
| Все IP-Adapters в одном pass | Конкуренция, размытие | Низкие weights |
| Нет tiling projection | Неточные паттерны | Детальные prompts |
| Нет multi-pass | Сложность отладки | Итерации seed |
| Квадратный латент | Искажение AR | TODO: fix |
