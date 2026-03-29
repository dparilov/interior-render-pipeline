# IRP Quick Start Guide v1.1

## Prerequisites

1. SketchUp 2026 with model open
2. ComfyUI running on port 8188
3. Python 3.10+ with PIL, numpy, requests

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 0: EXTRACT                                               │
│  SketchUp → scene_graph.json + beauty.png                       │
│  Output: irp_extract.zip                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: MAPPING (AI)                                          │
│  Input: irp_extract.zip + ТЗ.md + references/                   │
│  Output: role_map.json                                          │
│  ⚠️ ТЗ.md is REQUIRED for correct material assignment           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: EXPORT                                                │
│  SketchUp + role_map.json → irp_bundle.zip                      │
│  Contains: beauty, depth, boundary, masks, manifest, models     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: VALIDATE                                              │
│  python render/validate.py <bundle_path>                        │
│  Checks: schema, files, binary masks, hashes                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Phase 4: RENDER                                                │
│  python render/render.py <bundle_path>                          │
│  Creates: experiment/ with full traceability                    │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Extract

In SketchUp Ruby Console:

```ruby
require 'open-uri'
eval(URI.open('http://100.96.1.25:9090/irp.rb').read)

# IMPORTANT: Select the correct Scene first!
# The script will lock to current scene for all exports

IRP.extract
```

**Output:** `irp_extract.zip` (next to your .skp file)

Contents:
- `scene_graph.json` — all entities with PIDs + all scenes
- `beauty.png` — render from current Scene

**⚠️ Scene is locked** — all subsequent operations use the same camera.

## Step 2: Create Role Map

Send to AI:
- `irp_extract.zip`
- **ТЗ.md** (requirements document) — **REQUIRED**
- `references/` folder (material photos)

AI analyzes ТЗ first, then matches objects to PIDs.

AI returns `role_map.json`:

```json
{
  "version": "1.0",
  "entities": [
    {
      "pid": 36696,
      "name": "walls",
      "role": "surface.walls",
      "class": "surface",
      "surface_kind": "wall_tiles",
      "prompt": "white glossy wavy subway tiles Costa Nova style",
      "prompt_source": "ТЗ.md section 'Настенная плитка'",
      "reference": "references/wall_tiles.png",
      "critical": true
    }
  ],
  "excluded": [
    {"pid": 27700, "name": "Sumele", "reason": "Human figure"}
  ]
}
```

## Step 3: Export Bundle

Place `role_map.json` next to .skp file, then:

```ruby
IRP.export
```

**Output:** `irp_bundle.zip`

## Step 3.5: Post-Process Bundle (REQUIRED)

SketchUp's `write_image` has hardcoded 2X antialiasing ([Issue #545](https://github.com/SketchUp/api-issue-tracker/issues/545)).
Masks must be binarized in Python before validation:

```bash
python render/postprocess.py <bundle_path>
```

This script:
1. Binarizes all masks (threshold 128 → 0/255)
2. Adds `references/` from source folder
3. Adds `technical_spec.md` (ТЗ) and updates manifest hash

Contents:
- `beauty.png` — SketchUp render
- `depth.png` — ground truth depth from geometry
- `boundary_mask.png` — binary room silhouette
- `masks/*.png` — per-entity binary masks
- `manifest.json` — full metadata v1.1
- `technical_spec.md` — copy of ТЗ (if found)
- `model.dae/fbx/glb` — 3D exports

## Step 4: Validate (Schema)

```bash
python render/validate.py <bundle_path>
```

Checks schema, files, binary masks.

## Step 4.5: Validate (Visual) — REQUIRED

```bash
python render/validate_visual.py <bundle_path>
```

Uses Vision AI to verify:
- Each mask covers the correct object
- PIDs are correctly mapped
- Critical entities match ТЗ

**DO NOT proceed to render if visual validation fails.**

Checks:
- All required fields present in manifest
- All referenced files exist
- Masks are binary (only 0 and 255)
- Depth has gradient values
- Technical spec hash matches
- Coverage percentages valid

## Step 5: Render

```bash
python render.py /path/to/irp_bundle/
```

Options:
- `--dry-run` — build workflow without submitting
- `--no-validate` — skip validation

Creates `experiments/<name>_<timestamp>/`:
- `experiment.json` — full parameters extracted from workflow
- `workflow.json` — actual workflow submitted
- `bundle_manifest.json` — copy of manifest
- `render.png` — output image (when complete)

## ControlNet Parameters (v1.1)

| ControlNet | Strength | Start | End |
|------------|----------|-------|-----|
| Canny | 0.8 | 0.0 | 0.9 |
| Depth (SketchUp) | 0.9 | 0.0 | 0.8 |

## IPAdapter Weights

| Class | Weight | Mode |
|-------|--------|------|
| surface | 0.55 | regional_ipadapter |
| fixture | 0.50 | regional_ipadapter |
| opening | 0.00 | structural_controlnet |

## Troubleshooting

### "Scene changed" warning
The script detected scene switch during export. It auto-switches back.

### Boundary mask not binary
Check that no gray materials are applied. Use `paint_entity_solid()`.

### Missing reference files
Ensure `references/` folder contains all files from role_map.

### Validation errors
Run `python validate.py` to get detailed error list.
