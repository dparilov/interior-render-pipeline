# Blender Headless Flow

## Status

**FALLBACK / RESERVE PATH** — не canonical production path.

Используется когда:
- SketchUp недоступен
- Нужен headless CI/CD pipeline
- Работа на Linux server без GUI

## Назначение

Генерация bundle артефактов (beauty, depth, masks) из 3D модели без SketchUp.

## CLI

```bash
blender --background --python render/blender_masks.py -- \
  --input model.glb \
  --output masks/ \
  --beauty beauty.png \
  --depth depth.png \
  --resolution 1024x1024 \
  --camera auto \
  --manifest manifest.json
```

## Входной контракт

### Поддерживаемые форматы

| Format | Status | Notes |
|--------|--------|-------|
| .glb / .gltf | ✅ Recommended | Best compatibility |
| .fbx | ✅ Supported | May lose some naming |
| .dae | ✅ Supported | Collada import |
| .blend | ✅ Native | Direct open |

### Entity naming convention

Объекты должны содержать `IRP_<entity>` в имени:

```
IRP_walls           → walls.png
IRP_floor           → floor.png  
Bathtub_IRP_bathtub → bathtub.png
Mirror_IRP_mirror   → mirror.png
```

**Правило:** последняя часть после `IRP_` до `_` или `.` = имя entity.

### Camera requirements

| Mode | Description |
|------|-------------|
| `auto` | Использует первую найденную камеру или создаёт новую |
| `<name>` | Использует камеру с указанным именем |

**Ограничение:** одна камера = один view. Multi-view требует отдельных запусков.

## Выходной контракт

### Структура output

```
output/
├── beauty.png       # RGBA, прозрачный фон
├── depth.png        # BW 16-bit, normalized
├── masks/
│   ├── walls.png    # Binary mask (black on white)
│   ├── floor.png
│   └── ...
└── manifest.json
```

### Beauty pass

| Property | Value |
|----------|-------|
| Engine | BLENDER_EEVEE |
| Samples | 64 TAA |
| Background | Transparent |
| Format | PNG RGBA |
| Lighting | Auto-added if missing (SUN + AREA) |

### Depth pass

| Property | Value |
|----------|-------|
| Engine | BLENDER_EEVEE |
| Method | Z-pass → Normalize → Invert |
| Format | PNG BW 16-bit |
| Range | Scene-relative (NOT metric) |

**⚠️ Ограничение:** depth нормализован относительно сцены, не в реальных единицах.

### Mask semantics

| Property | Value |
|----------|-------|
| Foreground | Black (0, 0, 0) |
| Background | White (255, 255, 255) |
| Type | Binary |
| One entity | One PNG |
| Overlapping | Last rendered wins |

## Manifest schema

```json
{
  "source": "model.glb",
  "resolution": [1024, 1024],
  "generator": "blender_masks.py",
  "blender_version": "4.0.2",
  "entities": {
    "walls": {
      "mask": "masks/walls.png",
      "mesh_count": 4
    },
    "floor": {
      "mask": "masks/floor.png", 
      "mesh_count": 1
    }
  }
}
```

## Gaps vs SketchUp flow

| Feature | SketchUp | Blender | Gap |
|---------|----------|---------|-----|
| Entity naming | Manual tags | IRP_ convention | Different |
| Camera scenes | Multiple | Single | **Missing** |
| Depth type | Metric? | Normalized | **Different** |
| References | Linked | Not included | **Missing** |
| Technical spec | Exported | Not included | **Missing** |
| Role mapping | Manual | Auto from name | Different |

## Bundle contract parity

Для совместимости с main pipeline, Blender bundle ДОЛЖЕН дополняться:

1. `references/` — вручную добавить reference images
2. `technical_spec.md` — вручную добавить ТЗ
3. Manifest enrichment — добавить недостающие поля

### Минимально совместимый manifest

```json
{
  "version": "1.0",
  "scene": "bathroom_01",
  "base_image": "beauty.png",
  "depth_map": "depth.png",
  "entities": [
    {
      "name": "walls",
      "mask": "masks/walls.png",
      "reference": "references/wall_tiles.png",
      "ipadapter_weight": 0.5,
      "role": "surface",
      "critical": true
    }
  ]
}
```

## Validation

После генерации проверить:

- [ ] Все masks существуют
- [ ] beauty.png существует
- [ ] depth.png существует
- [ ] Размеры всех изображений совпадают
- [ ] Каждая entity в manifest имеет mask файл
- [ ] Manifest парсится без ошибок

## Known limitations

1. **Single camera** — один ракурс за запуск
2. **Normalized depth** — не метрическая глубина
3. **No references** — не экспортирует reference images
4. **No tech spec** — не экспортирует ТЗ
5. **Auto lighting** — может отличаться от SketchUp render
6. **EEVEE only** — Cycles требует GPU/долгий рендер
