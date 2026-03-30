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

### 🎯 Primary Surfaces (to render)

| Entity | Role | Mask | Reference | Notes |
|--------|------|------|-----------|-------|
| walls_tile | surface.walls_tile | masks/walls_tile.png | references/wall_tiles.png | White Costa Nova tiles (lower portion) |
| walls_upper | surface.walls_upper | masks/walls_upper.png | — | Gray painted wall (upper portion, no reference) |
| floor | surface.floor | masks/floor.png | references/floor_tiles.jpg | Blue Rivoli Bergen pattern |

> **Note on walls_upper (no image reference):**
> 
> `walls_upper` intentionally has no image reference. This is a plain painted surface
> without distinct pattern or texture to match. Evaluation criteria for surfaces
> without image reference:
> 
> 1. **Technical spec compliance** — matches color/finish described in technical_spec.md
> 2. **Color accuracy** — uniform gray, consistent with original render
> 3. **Clean boundary** — sharp transition to walls_tile without bleeding or artifacts
> 4. **No drift** — stable appearance across multiple renders (no random texture injection)
> 
> This methodology applies to any surface where the goal is preservation/consistency
> rather than material transfer from a reference image.

### 🔒 Preserved Geometry (keep unchanged)

| Entity | Role | Mask | Notes |
|--------|------|------|-------|
| window | opening.window | masks/window.png | Natural light source, structural element |

### ❌ Remove (Fixtures)

| Entity | Role | Reason |
|--------|------|--------|
| bathtub | fixture.bathtub | Not a surface |
| vanity | fixture.vanity | Not a surface |
| shower_screen | fixture.shower_screen | Not a surface |
| rainshower | fixture.rainshower | Not a surface |
| towel_warmer | fixture.towel_warmer | Not a surface |
| basket | fixture.basket | Not a surface |
| mirror | fixture.mirror | Not a surface |

---

## Required Masks

### Primary Surface Masks
- `masks/walls_tile.png` — lower wall area with Costa Nova tiles
- `masks/walls_upper.png` — upper wall area with gray paint
- `masks/floor.png` — floor tile area (from bathroom_01)

### Composite Masks (to generate)
- `masks/surfaces_combined.png` — union of walls_tile + walls_upper + floor
- `masks/fixtures_all.png` — union of all fixtures (for inpainting/exclusion)

### Optional Masks
- `masks/geometry_preserved.png` — window + other structural elements to keep unchanged

### Derivation
```bash
# Split walls.png into walls_tile and walls_upper
# (manual or threshold-based, depends on original mask structure)

# Combine surface masks
python3 -c "
from PIL import Image
import numpy as np

walls_tile = np.array(Image.open('masks/walls_tile.png'))
walls_upper = np.array(Image.open('masks/walls_upper.png'))
floor = np.array(Image.open('masks/floor.png'))
combined = np.maximum(walls_tile, np.maximum(walls_upper, floor))
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

### Per-Surface Criteria

#### Floor
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Pattern matches reference | Human visual | Recognizable Rivoli Bergen pattern |
| Color accuracy | Visual | Blue with white geometric pattern |
| Area coverage | Mask overlap | >95% of floor mask affected |
| Grout lines visible | Human visual | Pattern structure maintained |

#### Wall Tile (lower)
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Pattern matches reference | Human visual | Recognizable Costa Nova wavy tiles |
| Color accuracy | Visual | White glossy appearance |
| 3D texture visible | Human visual | Ribbed/wave texture apparent |
| Area coverage | Mask overlap | >95% of walls_tile mask affected |

#### Wall Upper (gray)
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Color consistency | Visual | Uniform gray, no pattern |
| Texture appropriate | Human visual | Matte paint appearance |
| Area coverage | Mask overlap | >95% of walls_upper mask affected |

### Boundary Criteria

#### Tile → Upper Boundary
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Clean horizontal transition | Human visual | No bleeding between zones |
| Edge alignment | Visual | Follows original boundary |
| No artifacts | Human visual | No halos, smearing, or color mixing |

#### Window Boundary
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Window unchanged | Pixel diff | <1% changed pixels in window mask |
| Wall-to-window transition | Human visual | Clean edge, no bleeding |
| Light quality preserved | Visual | Natural daylight appearance maintained |

### Workflow-Level Criteria

### SF1: Floor Only
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Floor criteria above | — | All pass |
| Non-floor areas unchanged | SSIM on inverse mask | >0.98 |

### SF2: Walls Only
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Wall tile criteria above | — | All pass |
| Wall upper criteria above | — | All pass |
| Tile→upper boundary | — | Pass |
| Non-wall areas unchanged | SSIM on inverse mask | >0.98 |

### SF3: Sequential
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| All surface criteria | — | All pass |
| No degradation from first pass | Visual comparison | Floor still correct after wall pass |
| Processing time | Runtime | <150s total |

### SF4: Parallel
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| All surface criteria | — | All pass |
| Processing time | Runtime | <100s (faster than sequential) |
| Quality vs sequential | Visual comparison | Equal or better |

### SF5: Fixture Preservation
| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| All surface criteria | — | All pass |
| Window boundary criteria | — | Pass |
| Other fixtures unchanged | Pixel diff on fixture masks | <1% changed pixels |
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
│   ├── walls_tile.png          # Lower wall tiles (split from walls.png)
│   ├── walls_upper.png         # Upper gray wall (split from walls.png)
│   ├── floor.png               # Copy from bathroom_01
│   ├── window.png              # Copy from bathroom_01 (preserved geometry)
│   ├── surfaces_combined.png   # Generated: walls_tile ∪ walls_upper ∪ floor
│   ├── fixtures_all.png        # Generated: all fixtures combined
│   └── geometry_preserved.png  # Optional: window + structural elements
├── references/
│   ├── wall_tiles.png     # Copy from bathroom_01
│   └── floor_tiles.jpg    # Copy from bathroom_01
└── technical_spec.md      # Updated for surface-only scope
```

---

## Manifest Changes

### entities
```json
{
  "entities": [
    {
      "name": "walls_tile",
      "role": "surface.walls_tile",
      "class": "surface",
      "mask": "masks/walls_tile.png",
      "reference": "references/wall_tiles.png",
      "prompt": "white glossy wavy subway tiles, Equipe Costa Nova White style"
    },
    {
      "name": "walls_upper",
      "role": "surface.walls_upper",
      "class": "surface",
      "mask": "masks/walls_upper.png",
      "reference": null,
      "prompt": "smooth gray painted wall, matte finish"
    },
    {
      "name": "floor",
      "role": "surface.floor", 
      "class": "surface",
      "mask": "masks/floor.png",
      "reference": "references/floor_tiles.jpg",
      "prompt": "blue ceramic floor tiles with white geometric pattern, Equipe Rivoli Bergen Azul style"
    }
  ],
  "preserved": [
    {
      "name": "window",
      "role": "opening.window",
      "class": "opening",
      "mask": "masks/window.png",
      "reason": "Preserved geometry: natural light source, structural element"
    }
  ]
}
```

### excluded (fixtures only)
```json
{
  "excluded": [
    {"name": "bathtub", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "vanity", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "shower_screen", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "rainshower", "reason": "Surface-only experiment: fixtures excluded"},
    {"name": "towel_warmer", "reason": "Surface-only experiment: fixtures excluded"},
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
