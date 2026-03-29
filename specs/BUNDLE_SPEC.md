# IRP Bundle Specification v1.1

> Единый контракт между extract → role_map → export → render

## Bundle Structure

```
irp_bundle/
├── manifest.json           # REQUIRED: Metadata + entity mapping
├── beauty.png              # REQUIRED: SketchUp render
├── depth.png               # REQUIRED: SketchUp depth map (ground truth)
├── boundary_mask.png       # REQUIRED: Binary room silhouette
├── masks/                  # REQUIRED: Per-entity binary masks
│   └── {entity_name}.png
├── references/             # REQUIRED: Material reference images
│   └── {material}.jpg|png
├── model/                  # OPTIONAL: 3D exports
│   ├── model.dae
│   ├── model.fbx
│   └── model.glb
└── technical_spec.md       # RECOMMENDED: Copy of ТЗ for traceability
```

## manifest.json Schema v1.1

All fields marked REQUIRED must be present. Renderer will fail if missing.

```json
{
  "version": "1.1",
  "scene_id": "bathroom_01_scene_1",
  "created": "2026-03-29T14:30:00Z",
  
  "base_image": "beauty.png",
  "depth_map": "depth.png",
  "boundary_mask": "boundary_mask.png",
  
  "image_size": {
    "width": 1920,
    "height": 1080
  },
  
  "camera": {
    "eye": [0.45, -1.75, 0.77],
    "target": [0.45, 0.25, 0.77],
    "up": [0, 0, 1],
    "fov": 35.0
  },
  
  "technical_spec": {
    "path": "technical_spec.md",
    "hash": "sha256:abc123...",
    "summary": "Bathroom for Masha: Costa Nova tiles, IDDIS vanity, white towel warmer"
  },
  
  "entities": [
    {
      "pid": 36696,
      "name": "walls",
      "role": "surface.walls",
      "class": "surface",
      "surface_kind": "wall_tiles",
      "mask": "masks/walls.png",
      "coverage_pct": 30.5,
      "reference": "references/wall_tiles.png",
      "prompt": "white glossy wavy subway tiles Costa Nova style, vertical orientation",
      "prompt_source": "ТЗ.md section 'Настенная плитка'",
      "critical": true,
      "render_mode": "regional_ipadapter",
      "ipadapter_weight": 0.55
    }
  ],
  
  "excluded": [
    {
      "pid": 27700,
      "name": "Sumele",
      "reason": "Human figure for scale"
    }
  ]
}
```

## Field Definitions

### Root Level (all REQUIRED unless noted)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | ✅ | Schema version, currently "1.1" |
| scene_id | string | ✅ | Unique identifier: {model}_{scene} |
| created | string | ✅ | ISO 8601 timestamp |
| base_image | string | ✅ | Path to beauty render |
| depth_map | string | ✅ | Path to SketchUp depth map |
| boundary_mask | string | ✅ | Path to binary room mask |
| image_size | object | ✅ | {width, height} in pixels |
| camera | object | ✅ | {eye, target, up, fov} |
| technical_spec | object | ✅ | ТЗ traceability info |
| entities | array | ✅ | Mapped entities |
| excluded | array | ❌ | Excluded entities with reasons |

### technical_spec Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | ✅ | Path to ТЗ file in bundle |
| hash | string | ✅ | SHA256 of ТЗ content |
| summary | string | ✅ | One-line summary of requirements |

### Entity Object (all REQUIRED unless noted)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| pid | integer | ✅ | SketchUp persistent ID |
| name | string | ✅ | Short identifier (snake_case) |
| role | string | ✅ | Semantic role (surface.floor, fixture.vanity) |
| class | string | ✅ | Category: surface / fixture / opening |
| surface_kind | string | ❌ | For surfaces: wall_tiles, floor_tiles, etc. |
| mask | string | ✅ | Path to binary mask |
| coverage_pct | float | ✅ | Estimated mask coverage as % of image (validated by validate.py) |
| reference | string | ❌ | Path to reference image (null for openings) |
| prompt | string | ✅ | Material/appearance description |
| prompt_source | string | ✅ | Traceability: where prompt came from |
| critical | boolean | ✅ | Must match ТЗ exactly |
| render_mode | string | ✅ | regional_ipadapter / structural_controlnet |
| ipadapter_weight | float | ✅ | Weight for IPAdapter (0.0 for openings) |

### Render Mode Rules

| Class | render_mode | ipadapter_weight | Notes |
|-------|-------------|------------------|-------|
| surface | regional_ipadapter | 0.55 | Walls, floor - high weight |
| fixture | regional_ipadapter | 0.50 | Vanity, bathtub, etc. |
| opening | structural_controlnet | 0.00 | Windows, doors - no IPAdapter |

## Validation Rules

1. All paths in manifest must exist in bundle
2. All masks must be binary (only 0 and 255 values)
3. depth_map must have gradient values (not binary)
4. boundary_mask must be binary
5. technical_spec.hash must match actual file hash
6. Every critical entity must have reference != null
7. coverage_pct must sum to reasonable total (< 100%)

## Changes from v1.0

- Added `depth_map` and `boundary_mask` as REQUIRED root fields
- Added `technical_spec` object for ТЗ traceability
- Added `pid` as REQUIRED in entity
- Added `prompt_source` for traceability
- Added `coverage_pct` as REQUIRED
- Added `surface_kind` for surface entities
- Added `excluded` array for documenting exclusions
