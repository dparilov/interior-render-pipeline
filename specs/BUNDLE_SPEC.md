# IRP Bundle Specification

> Формат bundle для передачи между стадиями pipeline

## Bundle Structure

```
irp_bundle/
├── manifest.json           # Метаданные и маппинг
├── beauty.png              # Рендер сцены из SketchUp
├── surfaces_only.png       # Только surfaces (walls, floor)
├── fixtures_only.png       # Только fixtures (прозрачный фон)
├── masks/
│   ├── walls.png           # Бинарная маска стен
│   ├── floor.png           # Бинарная маска пола
│   ├── bathtub.png         # ...
│   ├── vanity.png
│   ├── shower.png
│   ├── rainshower.png
│   ├── towel_warmer.png
│   ├── window.png
│   ├── basket.png
│   └── mirror.png
├── references/             # Копии референсов материалов
│   ├── floor_tiles.jpg
│   ├── wall_tiles.png
│   └── ...
├── model/                  # Опционально: исходные модели
│   ├── scene_graph.json
│   └── role_map.json
├── model.dae               # Для камеры
├── model.fbx               # Для геометрии
└── model.glb               # Для Blender
```

## manifest.json Schema (v1.0)

```json
{
  "version": "1.0",
  "scene_id": "bathroom_01_front",
  "created": "2026-03-29T11:00:00Z",
  
  "base_image": "beauty.png",
  "image_size": {
    "width": 1920,
    "height": 1080
  },
  
  "camera": {
    "eye": [0.45, -1.75, 0.77],
    "target": [0.45, 0.25, 0.77],
    "up": [0, 0, 1],
    "fov": 35
  },
  
  "entities": [
    {
      "name": "walls",
      "class": "surface",
      "surface_kind": "wall_tiles",
      "mask": "masks/walls.png",
      "coverage_pct": 30.5,
      "reference": "references/wall_tiles.png",
      "prompt": "white glossy wavy subway tiles Costa Nova style...",
      "critical": true,
      "render_mode": "regional_ipadapter",
      "ipadapter_weight": 0.55
    },
    {
      "name": "vanity",
      "class": "fixture",
      "mask": "masks/vanity.png",
      "coverage_pct": 8.2,
      "reference": "references/vanity.jpg",
      "prompt": "dark charcoal gray wall-mounted vanity cabinet...",
      "critical": true,
      "render_mode": "regional_ipadapter",
      "ipadapter_weight": 0.5
    },
    {
      "name": "window",
      "class": "opening",
      "mask": "masks/window.png",
      "coverage_pct": 2.1,
      "reference": null,
      "prompt": "white PVC window frame with frosted glass",
      "critical": false,
      "render_mode": "structural_controlnet",
      "ipadapter_weight": 0.0
    }
  ]
}
```

## Field Descriptions

### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | ✓ | Schema version ("1.0") |
| scene_id | string | ✓ | Unique scene identifier |
| created | string | | ISO 8601 timestamp |
| base_image | string | ✓ | Path to beauty render |
| image_size | object | ✓ | {width, height} in pixels |
| camera | object | | Camera parameters from SketchUp |
| entities | array | ✓ | List of mapped entities |

### Entity Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | ✓ | Semantic name (walls, floor, etc.) |
| class | string | ✓ | surface / fixture / opening |
| surface_kind | string | | For surfaces: floor, wall_tiles, wall_paint |
| mask | string | ✓ | Relative path to mask PNG |
| coverage_pct | number | ✓ | % площади изображения |
| reference | string | | Path to reference image (null if none) |
| prompt | string | ✓ | Material description for SD |
| critical | boolean | ✓ | Priority entity? |
| render_mode | string | ✓ | regional_ipadapter / structural_controlnet / tiling_projection / local_inpaint |
| ipadapter_weight | number | | IP-Adapter weight (0.0-1.0) |

### Entity Classes

| Class | Description | Examples | Default render_mode |
|-------|-------------|----------|---------------------|
| surface | Поверхности, покрытия | walls, floor | regional_ipadapter |
| fixture | Мебель, оборудование | bathtub, vanity | regional_ipadapter |
| opening | Проёмы | window, door | structural_controlnet |

### Render Modes

| Mode | Description | IP-Adapter |
|------|-------------|------------|
| regional_ipadapter | Стандартный с маской | Да |
| structural_controlnet | Только структура | Нет |
| tiling_projection | Проекция паттерна | Future |
| local_inpaint | Послойный inpaint | Future |

## Mask Requirements

### Format
- **Resolution:** Same as beauty (1920×1080)
- **Color depth:** 8-bit grayscale or RGB
- **Object:** Pure white (#FFFFFF)
- **Background:** Pure black (#000000)

### Quality Criteria

| Criterion | Description | Weight |
|-----------|-------------|--------|
| Coverage | Mask covers entire object | 40% |
| Precision | Mask doesn't overlap neighbors | 40% |
| Binary | No gradients, only black/white | 10% |
| Alignment | Matches beauty pixel-perfect | 10% |

### Common Issues

| Issue | Symptom | Cause |
|-------|---------|-------|
| hollow | Only edges visible | Faces not painted |
| leak | Captures neighbor | Overlapping geometry |
| gray | Gradient values | Antialiasing/materials |
| misaligned | Offset from beauty | Different camera/scene |

## Reference Requirements

### Format
- **Resolution:** 512×512 minimum recommended
- **Format:** JPG or PNG
- **Content:** Clear view of material/product
- **Background:** Clean, not cluttered

### Naming Convention

```
{role}.jpg           # Primary reference
{role}_detail.jpg    # Detail shot
{role}_texture.jpg   # Texture close-up
```

## Validation

### Required Files

```
✓ manifest.json
✓ beauty.png
✓ masks/{entity.name}.png for each entity
```

### Optional Files

```
○ surfaces_only.png
○ fixtures_only.png
○ references/{entity.reference}
○ model.dae / model.fbx / model.glb
```

## Example Usage

### Python

```python
import json
from pathlib import Path

def load_bundle(bundle_path: Path):
    manifest = json.loads((bundle_path / "manifest.json").read_text())
    
    for entity in manifest["entities"]:
        mask_path = bundle_path / entity["mask"]
        ref_path = bundle_path / entity.get("reference", "")
        
        print(f"{entity['name']}: {mask_path.exists()=}, {ref_path.exists()=}")
    
    return manifest
```

### ComfyUI

```json
{
  "load_mask": {
    "class_type": "LoadImageMask",
    "inputs": {
      "image": "irp_bundle/masks/floor.png",
      "channel": "red"
    }
  }
}
```
