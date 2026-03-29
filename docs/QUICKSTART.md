# Quick Start Guide

## Prerequisites

- SketchUp 2024+
- ComfyUI with models:
  - `RealVisXL_V4.0.safetensors`
  - `controlnet-canny-sdxl.safetensors`
  - `controlnet-depth-sdxl.safetensors`
  - `ip-adapter_sdxl.safetensors`
  - `clip_vision_g.safetensors`

## Workflow

### Step 1: Extract Scene Graph

In SketchUp Ruby Console:

```ruby
load 'http://100.96.1.25:9090/irp.rb'
IRP.extract
```

**Output:** `irp_extract.zip` (next to your .skp file)

Contents:
- `scene_graph.json` — all entities with PIDs + all scenes/cameras
- `views/*.png` — render from each Scene (camera angle)

### Step 2: Create Role Map

Send to AI:
- `irp_extract.zip` (scene_graph + views from all cameras)
- `ТЗ.md` (requirements document with materials) — **REQUIRED**
- `references/` folder (material photos)

AI analyzes ТЗ first, then matches objects to PIDs.

AI returns `role_map.json`:

```json
{
  "version": "1.0",
  "entities": [
    {"pid": 36696, "name": "walls", "role": "walls", "class": "surface"},
    {"pid": 43754, "name": "bathtub", "role": "bathtub", "class": "fixture"}
  ],
  "excluded": [
    {"pid": 27700, "reason": "Human figure (Sumele)"}
  ]
}
```

Place `role_map.json` next to your .skp file.

### Step 3: Export Bundle

```ruby
IRP.export
```

**Output:** `irp_bundle.zip` (next to your .skp file)

Contents:
- `beauty.png` — source render
- `depth.png` — ground truth depth from geometry
- `boundary_mask.png` — room silhouette (white = room, black = outside)
- `masks/*.png` — binary mask per entity
- `manifest.json` — bundle metadata
- `model.dae/fbx/glb` — 3D models for Blender

### Step 4: Visual QA

Check masks against beauty.png:

| Criterion | Target |
|-----------|--------|
| Coverage | Mask covers entire object |
| Precision | No overlap with neighbors |
| Binary | Pure black/white only |
| Score | ≥ 95 for each entity |

### Step 5: Render

#### Option A: ComfyUI GUI

1. Open `http://localhost:8188`
2. Load `render/workflow.json`
3. Set paths to your bundle
4. Queue prompt

#### Option B: Python Script

```bash
python render/render.py /path/to/irp_bundle
```

## Bundle Structure

```
irp_bundle/
├── manifest.json
├── beauty.png
├── depth.png           # Ground truth from SketchUp
├── boundary_mask.png   # Room silhouette
├── masks/
│   ├── walls.png
│   ├── floor.png
│   └── ...
├── model.dae
├── model.fbx
└── model.glb
```

## ControlNet Settings

| ControlNet | Source | Strength | End At |
|------------|--------|----------|--------|
| Canny | beauty.png | 0.8 | 0.9 |
| Depth | depth.png (SketchUp) | 0.9 | 0.8 |

**Important:** Use `depth.png` from bundle, NOT neural depth estimation. This ensures pixel-perfect geometry.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Objects in wrong place | Using neural depth | Use SketchUp depth.png |
| Generation outside room | No boundary mask | Add boundary_mask as latent_mask |
| Extra objects appear | Weak ControlNet | Increase Canny to 0.8+ |
| Empty mask | Faces not painted | Check recursive painting |
