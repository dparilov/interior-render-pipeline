# Interior Render Pipeline

AI-powered interior design rendering from SketchUp models.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUTS                                   │
├─────────────────────────────────────────────────────────────────┤
│  ТЗ.md (spec)          │  SKP Model           │  References     │
│  - Room type           │  - 3D geometry       │  - floor.jpg    │
│  - Materials list      │  - Named groups      │  - wall.png     │
│  - Constraints         │  - Scenes/cameras    │  - vanity.jpg   │
└───────────┬────────────┴──────────┬───────────┴────────┬────────┘
            │                       │                    │
            ▼                       ▼                    │
┌───────────────────────────────────────────────────────┐│
│              SCENE BUNDLE EXPORT                      ││
│  ┌─────────────────┐  ┌─────────────────┐            ││
│  │ scene_extractor │  │ scene_mask_     │            ││
│  │ .rb (v2)        │  │ exporter.rb     │            ││
│  │                 │  │                 │            ││
│  │ → scene_graph   │  │ → mask_floor    │            ││
│  │   .json         │  │ → mask_vanity   │            ││
│  │                 │  │ → mask_wall_*   │            ││
│  └─────────────────┘  └─────────────────┘            ││
└───────────────────────────┬───────────────────────────┘│
                            │                            │
                            ▼                            │
┌───────────────────────────────────────────────────────┐│
│                    BUNDLE MANIFEST                    ││
│  {                                                    │◄┘
│    "floor": {mask: "...", reference: "floor.jpg"},   │
│    "wall_tiles": {mask: "...", reference: "wall.png"}│
│    ...                                                │
│  }                                                    │
└───────────────────────────┬───────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      COMFYUI RENDER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Canny        │  │ Depth        │  │ Regional IP-Adapter    │ │
│  │ ControlNet   │  │ ControlNet   │  │ (per mask + reference) │ │
│  │ (structure)  │  │ (perspective)│  │                        │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│                    SDXL RealVisXL V4.0                          │
│                            │                                     │
│                            ▼                                     │
│                      Final Render                                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### SketchUp Ruby Plugins (`projects/interior-render/sketchup/`)

| Script | Purpose |
|--------|---------|
| `scene_extractor.rb` | Extract scene graph (entities, materials, cameras) |
| `scene_extractor_v2.rb` | Recursive extraction (finds nested components) |
| `scene_augmenter.rb` | Rename groups, hide objects for render |
| `scene_mask_exporter.rb` | Export binary masks per entity |

### Python Scripts (`ops/`)

| Script | Purpose |
|--------|---------|
| `comfyui-render.py` | Main render script with `--bundle` support |
| `generate_bundle_manifest.py` | Map entities → references from ТЗ |

## Usage

### 1. Prepare SketchUp Model

```ruby
# In SketchUp Ruby Console:
load 'scene_extractor_v2.rb'
SceneExtractor.extract_to_file('scene_graph.json')

load 'scene_mask_exporter.rb'
SceneMaskExporter.export_all  # → masks/*.png
```

### 2. Generate Bundle Manifest

```bash
python3 generate_bundle_manifest.py \
  --masks /path/to/masks \
  --references /path/to/tz/images \
  --output bundle_manifest.json
```

### 3. Render with Bundle

```bash
python3 comfyui-render.py \
  --tz /path/to/ТЗ.md \
  --bundle /path/to/bundle/ \
  --steps 50
```

The `--bundle` flag:
- **Skips** UperNet/SAM segmentation (no guessing)
- **Uses** authoritative masks from SketchUp (100% accurate)

## Why Bundle > Segmentation?

| Approach | Accuracy | Source |
|----------|----------|--------|
| UperNet/SAM | ~76% avg | Guessing from raster |
| **Scene Bundle** | **100%** | Ground truth from 3D model |

Masks exported from SketchUp are **pixel-perfect** — each pixel belongs to exactly one entity.

## ТЗ Format

See `skills/comfyui-render/SKILL.md` for full specification.

Required sections:
- `## Напольное покрытие` — floor materials
- `## Настенное покрытие` — wall materials  
- `## Мебель и сантехника` — fixtures with references

## Models Required

- SDXL: `realvisxlV40_v40Bakedvae.safetensors`
- ControlNet: `diffusers_xl_canny_full.safetensors`
- ControlNet: `diffusers_xl_depth_full.safetensors`
- IP-Adapter: `ip-adapter-plus_sdxl_vit-h.safetensors`
- CLIP: `CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors`

## License

MIT
