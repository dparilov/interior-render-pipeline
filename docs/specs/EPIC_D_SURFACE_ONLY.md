# Epic D: Surface-Only Scene Specification

## Goal

Test surface-only rendering: walls and floor only, all fixtures masked out.
Validate that IPAdapter can reliably transfer surface materials without fixture interference.

## Scene: bathroom_01_surfaces

Derived from `examples/bathroom_01/` with reduced entity set.

### Bundle Name
```
examples/bathroom_01_surfaces/
```

### Source Bundle
```
examples/bathroom_01/
```

---

## Entities

### ✅ Keep (Surfaces)

| Entity | Role | Mask | Reference | Notes |
|--------|------|------|-----------|-------|
| walls | surface.walls | masks/walls.png | references/wall_tiles.png | White Costa Nova tiles |
| floor | surface.floor | masks/floor.png | references/floor_tiles.jpg | Blue Rivoli Bergen pattern |

### ❌ Remove (Fixtures)

| Entity | Role | Reason |
|--------|------|--------|
| bathtub | fixture.bathtub | Not a surface |
| vanity | fixture.vanity | Not a surface |
| shower_screen | fixture.shower_screen | Not a surface |
| rainshower | fixture.rainshower | Not a surface |
| towel_warmer | fixture.towel_warmer | Not a surface |
| window | opening.window | Not a surface |
| basket | fixture.basket | Not a surface |
| mirror | fixture.mirror | Not a surface |

---

## Required Masks

### Surface Masks (from bathroom_01)
- `masks/walls.png` — wall tile area
- `masks/floor.png` — floor tile area

### Composite Masks (to generate)
- `masks/surfaces_combined.png` — union of walls + floor
- `masks/fixtures_all.png` — union of all fixtures (for inpainting/exclusion)

### Derivation
```bash
# Combine surface masks
python3 -c "
from PIL import Image
import numpy as np

walls = np.array(Image.open('masks/walls.png'))
floor = np.array(Image.open('masks/floor.png'))
combined = np.maximum(walls, floor)
Image.fromarray(combined).save('masks/surfaces_combined.png')
"
```

---

## Workflow Candidates

### SF1: Surface Floor Only
- Input: beauty.png, depth.png
- Mask: floor.png only
- IPAdapter: floor_tiles.jpg
- ControlNet: depth
- Output: floor tiles transferred, rest unchanged

### SF2: Surface Walls Only
- Input: beauty.png, depth.png
- Mask: walls.png only
- IPAdapter: wall_tiles.png
- ControlNet: depth
- Output: wall tiles transferred, rest unchanged

### SF3: Surface Both Sequential
- Run SF1 → output1.png
- Run SF2 on output1.png → output2.png
- Test: sequential application

### SF4: Surface Both Parallel
- Input: beauty.png, depth.png
- Mask: surfaces_combined.png
- IPAdapter: both references (multi-adapter or merged)
- ControlNet: depth
- Test: single-pass multi-surface

### SF5: Surface Both with Fixture Preservation
- Same as SF4 but with boundary_mask applied
- Test: surfaces change, fixtures remain pixel-identical

---

## Acceptance Criteria

### SF1: Floor Only
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Floor pattern matches reference | Human visual | Recognizable Rivoli pattern |
| Floor area coverage | Mask overlap | >95% of floor mask affected |
| Non-floor areas unchanged | SSIM on inverse mask | >0.98 |
| No artifacts at mask boundary | Human visual | Clean transitions |

### SF2: Walls Only
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Wall pattern matches reference | Human visual | Recognizable Costa Nova tiles |
| Wall area coverage | Mask overlap | >95% of wall mask affected |
| Non-wall areas unchanged | SSIM on inverse mask | >0.98 |
| No artifacts at mask boundary | Human visual | Clean transitions |

### SF3: Sequential
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Both surfaces match references | Human visual | Both patterns recognizable |
| No degradation from first pass | Visual comparison | Floor still correct after wall pass |
| Processing time | Runtime | <150s total |

### SF4: Parallel
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Both surfaces match references | Human visual | Both patterns recognizable |
| Processing time | Runtime | <100s (faster than sequential) |
| Quality vs sequential | Visual comparison | Equal or better |

### SF5: Fixture Preservation
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Surfaces match references | Human visual | Both patterns recognizable |
| Fixtures unchanged | Pixel diff on fixture masks | <1% changed pixels |
| Boundary mask respected | Visual inspection | No bleeding into fixtures |

---

## Bundle Structure

```
examples/bathroom_01_surfaces/
├── manifest.json          # Reduced entity list
├── beauty.png             # Copy from bathroom_01
├── depth.png              # Copy from bathroom_01
├── boundary_mask.png      # Copy from bathroom_01
├── masks/
│   ├── walls.png          # Copy from bathroom_01
│   ├── floor.png          # Copy from bathroom_01
│   ├── surfaces_combined.png   # Generated: walls ∪ floor
│   └── fixtures_all.png        # Generated: all fixtures combined
├── references/
│   ├── wall_tiles.png     # Copy from bathroom_01
│   └── floor_tiles.jpg    # Copy from bathroom_01
└── technical_spec.md      # Updated for surface-only scope
```

---

## Manifest Changes

### entities (keep only)
```json
{
  "entities": [
    {
      "name": "walls",
      "role": "surface.walls",
      "class": "surface",
      "mask": "masks/walls.png",
      "reference": "references/wall_tiles.png",
      "prompt": "white glossy wavy subway tiles, Equipe Costa Nova White style"
    },
    {
      "name": "floor",
      "role": "surface.floor", 
      "class": "surface",
      "mask": "masks/floor.png",
      "reference": "references/floor_tiles.jpg",
      "prompt": "blue ceramic floor tiles with white geometric pattern, Equipe Rivoli Bergen Azul style"
    }
  ]
}
```

### excluded (add fixtures)
```json
{
  "excluded": [
    {"name": "bathtub", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "vanity", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "shower_screen", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "rainshower", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "towel_warmer", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "window", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "basket", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "mirror", "reason": "Surface-only experiment: fixtures excluded"}
  ]
}
```

---

## Next Steps (not in this commit)

1. Create `examples/bathroom_01_surfaces/` bundle
2. Generate composite masks
3. Create SF1-SF5 workflow files
4. Execute and capture results per governance rules
