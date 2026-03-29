# Interior Render Pipeline (IRP) v1.1

> SketchUp → AI-assisted material mapping → Stable Diffusion render

## Status: Research MVP

Controlled experiment framework for interior rendering with regional material control.

## Quick Start

```ruby
# In SketchUp Ruby Console:
load 'http://100.96.1.25:9090/irp.rb'

# 1. Select correct Scene, then extract
IRP.extract   # → irp_extract.zip (scene-locked)

# 2. Send zip + ТЗ.md to AI → role_map.json

# 3. Export bundle
IRP.export    # → irp_bundle.zip

# 4. Post-process (binarize masks)
python render/postprocess.py <bundle> --refs <refs_dir> --spec <tz_path>

# 5. Validate and render
python render/validate.py <bundle>
python render/render.py <bundle>
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

## Pipeline Overview

```
Phase 0: Extract     → scene_graph.json + beauty.png (scene-locked)
Phase 1: AI Mapping  → role_map.json (requires ТЗ.md)
Phase 2: Export      → irp_bundle.zip (masks + depth + boundary + models)
Phase 3: Validate    → python validate.py (schema + files + hashes)
Phase 4: Render      → python render.py (full experiment tracking)
```

## Repository Structure

```
interior-render-pipeline/
├── sketchup/
│   └── irp.rb              # Single script: extract + export (v1.1)
├── render/
│   ├── render.py           # Python orchestrator with experiment tracking
│   ├── validate.py         # Bundle validator (schema + files)
│   ├── experiment.py       # Experiment logging module
│   └── workflow.json       # ComfyUI workflow template
├── specs/
│   ├── BUNDLE_SPEC.md      # Bundle schema v1.1
│   └── EXPERIMENTS.md      # Experiment logging spec
├── docs/
│   ├── ARCHITECTURE.md     # System design
│   ├── QUICKSTART.md       # Usage guide
│   └── AUDIT.md            # Quality checklist
└── examples/
    └── bathroom_01/        # Reference (ТЗ.md + references only)
```

## Key Features

- **Ground truth depth** from SketchUp geometry (not neural estimation)
- **Boundary mask** prevents generation outside room (binary)
- **Regional IPAdapter** with per-entity attention masks
- **ТЗ traceability** from requirements to render (hash + summary)
- **Scene locking** ensures consistent camera across pipeline
- **Experiment tracking** with honest parameter logging from workflow

## Components

| Component | Status | Description |
|-----------|--------|-------------|
| irp.rb | ✅ v1.1 | SketchUp extract + export with scene lock |
| workflow.json | ✅ v1.1 | ComfyUI dual ControlNet (Canny 0.8, Depth 0.9) |
| render.py | ✅ v1.1 | Python orchestrator with validation |
| validate.py | ✅ v1.1 | Bundle schema + file validator |
| experiment.py | ✅ v1.1 | Full experiment logging |
| BUNDLE_SPEC | ✅ v1.1 | Unified bundle contract |

## ControlNet Parameters

| ControlNet | Strength | End |
|------------|----------|-----|
| Canny | 0.8 | 0.9 |
| Depth (SketchUp) | 0.9 | 0.8 |

## Requirements

- SketchUp 2026
- ComfyUI with IPAdapter nodes
- Python 3.10+ with PIL, numpy, requests
