# Interior Render Pipeline

> SketchUp → Bundle → Photorealistic Render

## Overview

Generate photorealistic interior renders from SketchUp models with precise material control via reference images.

**Key idea:** SketchUp geometry as source of truth for masks (no segmentation guessing).

## Quick Start

```ruby
# In SketchUp Ruby Console:
load 'http://100.96.1.25:9090/irp.rb'

# 1. Extract scene graph
IRP.extract   # → irp_extract.zip (next to .skp)

# 2. Send zip to AI, get role_map.json, place next to .skp

# 3. Export bundle
IRP.export    # → irp_bundle.zip (masks, depth, boundary, models)

# 4. Render with ComfyUI
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

## Project Structure

```
├── sketchup/
│   └── irp.rb          # Single script: IRP.extract + IRP.export
├── render/
│   ├── workflow.json   # Canonical ComfyUI workflow
│   └── render.py       # Python orchestrator
├── specs/
│   ├── BUNDLE_SPEC.md  # Bundle JSON schema v1.0
│   └── RENDERING.md    # Render strategies by entity class
├── docs/
│   ├── ARCHITECTURE.md # Pipeline contracts
│   └── QUICKSTART.md   # Step-by-step guide
└── examples/
    └── bathroom_01/    # Complete test bundle
```

## Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  SketchUp   │────▶│   Bundle    │────▶│   Render    │
│  model.skp  │     │  manifest   │     │  output.png │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
 scene_graph.json    masks/*.png      Canny ControlNet (0.8)
 role_map.json       depth.png        SketchUp Depth (0.9)
                     boundary_mask    IPAdapter × N
```

**Key:** Depth map exported from SketchUp geometry (not neural estimation) ensures pixel-perfect object placement. Boundary mask prevents generation outside room.

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
| Example bundle | ✅ Complete |

**Current focus:** Strict geometry control via SketchUp depth map.

## License

MIT
