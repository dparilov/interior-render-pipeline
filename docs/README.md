# Interior Render Pipeline — Documentation

## Quick Start

### SketchUp Export
```ruby
# Load plugin
load '/path/to/irp.rb'

# Export bundle
IRP.export
# Creates: irp_bundle.zip
```

### Blender Render
```bash
blender --background --python scripts/render_canonical.py -- \
    --bundle examples/bathroom_04/ \
    --output render.png
```

## Documents

| Document | Description |
|----------|-------------|
| [CAMERA.md](CAMERA.md) | Camera transform formula (SketchUp → Blender) |
| [WORKFLOW.md](WORKFLOW.md) | End-to-end pipeline |
| [PREFLIGHT.md](PREFLIGHT.md) | SketchUp export checklist |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Blocking issues and workarounds |
| [BUNDLE_SPEC.md](BUNDLE_SPEC.md) | Bundle format specification |

## Key Findings from Phase B

1. **Camera Transform**: Use DAE position as-is + 90° X rotation
   - DAE: `(1.147, -4.442, 1.948)` meters
   - Blender: same position, rotation `(90°, 0, 0)`

2. **Visibility**: Hidden entities named `HIDDEN_S_*` or `HIDDEN_G_*`

3. **Front Wall Issue**: SketchUp clipping plane not exported — need manual hiding

## Scripts

| Script | Purpose |
|--------|---------|
| `render_canonical.py` | Canonical Blender render with DAE camera |
| `blender_material_render.py` | Material-based render (floor/wall textures) |
| `compare_dae_glb.py` | Compare DAE vs GLB imports |
| `dae_to_blender.py` | Import DAE via pycollada |
