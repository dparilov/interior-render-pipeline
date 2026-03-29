# Quick Start Guide

## Prerequisites

- SketchUp 2024+
- ComfyUI with models:
  - `RealVisXL_V4.0.safetensors`
  - `controlnet-canny-sdxl.safetensors`
  - `controlnet-depth-sdxl.safetensors`
  - `ip-adapter_sdxl.safetensors`
  - `clip_vision_g.safetensors`

## Phase 0: Extract Scene Graph

In SketchUp Ruby Console:

```ruby
load '/path/to/irp_extract.rb'
IRP.extract
```

**Output:**
- `~/Downloads/irp_extract/scene_graph.json`
- `~/Downloads/irp_extract/beauty.png`

## Phase 1: Create Role Map

Provide to AI:
- `scene_graph.json`
- `beauty.png`
- Your ТЗ (requirements doc)
- Reference images

**Output:** `role_map.json`

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

## Phase 2: Export Bundle

In SketchUp Ruby Console:

```ruby
load '/path/to/irp_export.rb'
IRP.load_map('/path/to/role_map.json')
IRP.export
```

**Output:** `~/Downloads/irp_bundle/`
```
irp_bundle/
├── manifest.json
├── beauty.png
├── masks/
│   ├── walls.png
│   ├── floor.png
│   └── ...
├── model.dae
├── model.fbx
└── model.glb
```

## Phase 3: Visual QA

Check each mask against beauty.png:
- Coverage: Does mask cover entire object?
- Precision: Does mask avoid neighbors?
- Binary: Pure black/white only?

**Target:** Score ≥ 95 for each entity.

## Phase 4: Render

### Option A: ComfyUI GUI

1. Open `http://localhost:8188`
2. Load `render/workflow.json`
3. Set paths to your bundle
4. Queue prompt

### Option B: API

```bash
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d @render/workflow.json
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty mask | Faces not painted | Check recursive painting |
| Mask leaks | Overlapping geometry | Hide neighbors during render |
| Gray tones | Antialiasing | Use flat shading |
| Wrong aspect | Hardcoded size | Match beauty.png dimensions |
