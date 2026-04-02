# Texture & Tile Rendering

## Overview

IRP supports automatic texture application to floor and wall surfaces using reference images from the bundle.

## Usage

```bash
blender --background --python scripts/blender_material_render.py -- \
    --model examples/bathroom_04/model.glb \
    --floor-texture examples/bathroom_04/references/floor_tiles.jpg \
    --wall-texture examples/bathroom_04/references/wall_tiles.png \
    --floor-tile-size 200x200 \
    --wall-tile-size 50x200 \
    --output render.png
```

## Tile Size Format

Specify tile dimensions in millimeters: `WIDTHxHEIGHT`

| Format | Example | Use Case |
|--------|---------|----------|
| Square | `200x200` | Floor tiles (20cm x 20cm) |
| Rectangular | `50x200` | Wall subway tiles (5cm x 20cm) |
| Large format | `600x600` | Modern floor tiles |

## Texture Scale Calculation

The script automatically calculates UV scale based on tile size:

```python
def tile_scale(size_mm):
    """Calculate texture scale based on tile size.
    
    For 200mm tiles: scale = 0.3 (good density)
    For 50x200mm tiles: scale = 0.5
    """
    w, h = map(int, size_mm.split('x'))
    avg = (w + h) / 2
    return 200 / avg * 0.3
```

## Surface Separation

The script automatically separates geometry into:

1. **IRP_Floor** — Faces with `normal.z > 0.9` AND `center.z < 0.15`
2. **IRP_Walls** — Faces with `normal.x² + normal.y² > 0.8` AND `abs(normal.z) < 0.3`
3. **IRP_Other** — All remaining faces

## Material Setup

Materials use **Object Coordinates** for proper tiling:

```
Texture Coordinate (Object) → Mapping (Scale) → Image Texture → Principled BSDF
```

This ensures tiles repeat correctly regardless of UV unwrapping.

## Known Issues

### 1. Texture Scale Mismatch

**Problem:** Tiles appear too large or too small.

**Solution:** Adjust `--floor-tile-size` / `--wall-tile-size` parameters.

### 2. Quatrefoil Pattern Not Visible

**Problem:** Floor pattern doesn't render correctly.

**Cause:** Pattern in reference image needs specific scale.

**Solution:** Try different tile sizes or reference images with clearer pattern.

### 3. Texture Seams

**Problem:** Visible seams at surface boundaries.

**Solution:** Use seamless/tileable reference textures.

## Reference Images

Reference images should be:
- High resolution (at least 1024x1024)
- Tileable/seamless preferred
- True color (no filters)
- Single tile or repeating pattern

## Example Results

B15 render with floor texture:
- Floor: quatrefoil pattern visible
- Walls: Costa Nova white tiles (needs material setup)
- Tile size: 200x200mm floor, 50x200mm walls
