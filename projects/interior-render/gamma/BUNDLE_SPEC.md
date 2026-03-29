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

## manifest.json Schema

```json
{
  "$schema": "irp-bundle-v1",
  
  "version": 1,
  "created": "2026-03-29T11:00:00Z",
  "scene_name": "Сцена №1",
  
  "resolution": [1920, 1080],
  
  "images": {
    "beauty": "beauty.png",
    "surfaces_only": "surfaces_only.png",
    "fixtures_only": "fixtures_only.png"
  },
  
  "camera": {
    "eye": [0.45, -1.75, 0.77],
    "target": [0.45, 0.25, 0.77],
    "up": [0, 0, 1],
    "fov": 35
  },
  
  "entities": [
    {
      "pid": 36696,
      "name": "walls",
      "role": "walls",
      "class": "surface",
      "mask": "masks/walls.png",
      "reference": "references/wall_tiles.png",
      "prompt": "white glossy wavy subway tiles Costa Nova style with 3D relief texture arranged vertically, visible grout lines, 50x200mm"
    }
  ]
}
```

## Field Descriptions

### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | number | ✓ | Schema version (currently 1) |
| created | string | | ISO 8601 timestamp |
| scene_name | string | ✓ | SketchUp Scene name |
| resolution | [w, h] | ✓ | Image resolution in pixels |
| images | object | ✓ | Paths to base images |
| camera | object | | Camera parameters from SketchUp |
| entities | array | ✓ | List of mapped entities |

### Entity Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| pid | number | ✓ | SketchUp persistent_id |
| name | string | ✓ | Semantic name (IRP export name) |
| role | string | ✓ | Functional role (walls, floor, etc.) |
| class | string | ✓ | surface / fixture / opening |
| mask | string | ✓ | Relative path to mask PNG |
| reference | string | | Relative path to reference image |
| prompt | string | | Detailed material description for SD |

### Entity Classes

| Class | Description | Examples |
|-------|-------------|----------|
| surface | Поверхности, покрытия | walls, floor, ceiling |
| fixture | Мебель, оборудование | bathtub, vanity, mirror |
| opening | Проёмы | window, door |

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
