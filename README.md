# Interior Render Pipeline

> SketchUp → Bundle → Photorealistic Render

## Overview

Generate photorealistic interior renders from SketchUp models with precise material control via reference images.

**Key idea:** SketchUp geometry as source of truth for masks (no segmentation guessing).

## Quick Start

```bash
# 1. Extract scene graph from SketchUp
#    → scene_graph.json + beauty.png

# 2. Map PIDs to semantic roles (AI-assisted)
#    → role_map.json

# 3. Export bundle from SketchUp
#    → irp_bundle/ (masks, models, manifest)

# 4. Render with ComfyUI
#    → render.png
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

## Project Structure

```
├── sketchup/           # SketchUp Ruby scripts
│   ├── irp_extract.rb  # Phase 0: Scene graph extraction
│   └── irp_export.rb   # Phase 2: Mask & model export
├── render/             # ComfyUI rendering
│   ├── workflow.json   # Canonical workflow
│   └── render.py       # Python orchestrator
├── specs/              # Specifications
│   ├── BUNDLE_SPEC.md  # Bundle JSON schema
│   └── RENDERING.md    # Render strategies
├── docs/               # Documentation
│   ├── ARCHITECTURE.md # Pipeline contracts
│   └── QUICKSTART.md   # Step-by-step guide
└── examples/           # Example bundles
    └── bathroom_01/    # Test scene
```

## Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SketchUp   │────▶│   Bundle    │────▶│   Render    │
│  model.skp  │     │  manifest   │     │  output.png │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
 scene_graph.json    masks/*.png      Canny + Depth
 role_map.json       references/      IPAdapter × N
```

## Requirements

- SketchUp 2024+ (for Ruby scripts)
- ComfyUI with:
  - RealVisXL V4.0
  - ControlNet (Canny, Depth)
  - IPAdapter Plus

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data flow contracts |
| [BUNDLE_SPEC.md](specs/BUNDLE_SPEC.md) | Bundle JSON schema v1.0 |
| [RENDERING.md](specs/RENDERING.md) | Entity classes & render modes |
| [QUICKSTART.md](docs/QUICKSTART.md) | Step-by-step guide |

## Status

**Version:** v1.0-beta (MVP)

See [STATUS.md](STATUS.md) for detailed implementation status.

| Component | Status |
|-----------|--------|
| SketchUp scripts | ✅ Works |
| Bundle schema | ✅ Stable |
| ComfyUI workflow | ✅ Works |
| Python orchestrator | 📄 Stub |
| Example bundle | 📄 Stub (schema only) |

**Next:** Complete bathroom_01 example with real images.

## License

MIT
