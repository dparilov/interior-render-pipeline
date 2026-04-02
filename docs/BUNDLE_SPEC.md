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
  ],
  
  "visibility": {
    "global": {
      "hidden_pids": [12345],
      "count": 1
    },
    "scene": {
      "name": "Сцена №1",
      "hidden_pids": [67890],
      "hidden_layers": ["Front Wall"],
      "count": 1
    }
  }
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
| visibility | object | ❌ | Hidden entities (global + scene-specific) |
| section_planes | array | ❌ | Active section planes for clipping |

### visibility Object

Contains both global and scene-specific hidden entities:

```json
"visibility": {
  "global": {
    "hidden_pids": [12345],
    "count": 1
  },
  "scene": {
    "name": "Сцена №1",
    "hidden_pids": [67890, 11111],
    "hidden_layers": ["Front Wall", "Section Cut"],
    "count": 2
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| global.hidden_pids | array | PIDs of entities with `entity.hidden? = true` (always hidden) |
| global.count | integer | Count of global hidden |
| scene.name | string | Name of the active SketchUp scene |
| scene.hidden_pids | array | PIDs of entities on hidden layers for this scene |
| scene.hidden_layers | array | Layer names that are OFF for this scene |
| scene.count | integer | Count of scene-specific hidden |

**Entity Naming Convention in GLB:**
- `IRP_{name}` — mapped entities from role_map
- `HIDDEN_S_{pid}` — scene-hidden entities (layer OFF)
- `HIDDEN_G_{pid}` — global-hidden entities (entity.hidden?)
- `EXCLUDED_{name}` — excluded entities

This allows renderers to hide entities by name pattern matching.

### coordinate_transform Object

```json
"coordinate_transform": {
  "dae_unit_meters": 0.0254,
  "axis_swap": "Z-up → Y-up: (x,y,z) → (x,z,-y)",
  "glb_offset": [0.0, 0.0, 0.0]
}
```

| Field | Type | Description |
|-------|------|-------------|
| dae_unit_meters | float | DAE unit in meters (0.0254 for inches) |
| axis_swap | string | Axis transformation description |
| glb_offset | array | [x, y, z] offset to apply after axis swap |

**Camera Transform Formula (DAE to GLB):**
```python
INCH = 0.0254
# Position: inches Z-up → meters Y-up + offset
glb_pos = [
    dae_pos[0] * INCH + offset[0],
    dae_pos[2] * INCH + offset[1],  # Z → Y
    -dae_pos[1] * INCH + offset[2]  # -Y → Z
]
```

### entity_mapping Object

Maps entity names to PIDs and GLB names for lookup:

```json
"entity_mapping": {
  "walls": {"pid": 36696, "glb_name": "IRP_walls", "role": "surface.walls"},
  "floor": {"pid": 36828, "glb_name": "IRP_floor", "role": "surface.floor"},
  "hidden_global_0": {"pid": 27700, "glb_name": "HIDDEN_G_27700", "type": "global_hidden"}
}
```

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
| render_mode | string | ✅ | regional_ipadapter / structural_controlnet / preserve |
| ipadapter_weight | float | ✅ | Weight for IPAdapter (0.0 for openings) |

### Render Mode Rules

| Class | render_mode | ipadapter_weight | Notes |
|-------|-------------|------------------|-------|
| surface | regional_ipadapter | 0.55 | Walls, floor - high weight |
| fixture | regional_ipadapter | 0.50 | Vanity, bathtub, etc. |
| opening | structural_controlnet | 0.00 | Windows, doors - no IPAdapter |
| preserved | preserve | 0.00 | Keep unchanged, no generation |

**Render mode descriptions:**

- `regional_ipadapter` — Generate surface/fixture appearance using IPAdapter with reference image
- `structural_controlnet` — Preserve structural geometry via ControlNet, no appearance generation
- `preserve` — Entity excluded from generation entirely, geometry preserved as-is (e.g., window as light source)

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

### section_planes Array

Active section planes from SketchUp for viewport clipping:

```json
"section_planes": [
  {
    "normal": [0, 1, 0],
    "distance_inches": -51.19,
    "distance_meters": -1.3,
    "equation": "0x + 1y + 0z + -51.19 = 0"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| normal | array | Plane normal vector [a, b, c] |
| distance_inches | float | Distance from origin (inches) |
| distance_meters | float | Distance from origin (meters) |
| equation | string | Human-readable plane equation |

**Usage in Blender:**
- If normal.y ≈ 1, plane clips in Y direction
- Set camera.clip_start = distance from camera to plane
- This hides geometry between camera and section plane
