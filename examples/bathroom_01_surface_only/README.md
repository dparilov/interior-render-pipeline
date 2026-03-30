# bathroom_01_surface_only

Surface-only bundle for Epic D experiments (SF1–SF5).

## Purpose

Test IPAdapter surface material transfer on walls and floor only, with fixtures excluded and window preserved as structural geometry.

---

## Source Artifacts Used

From `examples/bathroom_01/`:

| File | Type | Notes |
|------|------|-------|
| beauty.png | Core image | Original render |
| depth.png | Core image | Depth map |
| boundary_mask.png | Core image | Scene boundary |
| technical_spec.md | Metadata | Source for technical_spec_surface.md |
| manifest.json | Metadata | Source for entity definitions |
| masks/floor.png | Mask | Copied directly |
| masks/walls.png | Mask | Split into walls_tile + walls_upper |
| masks/window.png | Mask | Copied directly |
| masks/bathtub.png | Mask | Combined into fixtures_all |
| masks/vanity.png | Mask | Combined into fixtures_all |
| masks/mirror.png | Mask | Combined into fixtures_all |
| masks/rainshower.png | Mask | Combined into fixtures_all |
| masks/towel_warmer.png | Mask | Combined into fixtures_all |
| masks/basket.png | Mask | Combined into fixtures_all |
| masks/shower_screen.png | Mask | Combined into fixtures_all |
| references/floor_tiles.jpg | Reference | Copied directly |
| references/wall_tiles.png | Reference | Copied directly |

---

## Generated Artifacts

| File | Type | Generation Method |
|------|------|-------------------|
| masks/walls_tile.png | Derived mask | Split from walls.png by brightness (>210) |
| masks/walls_upper.png | Derived mask | Split from walls.png by brightness (150-210) |
| masks/surfaces_combined.png | Composite mask | Union of floor + walls_tile + walls_upper |
| masks/fixtures_all.png | Composite mask | Union of 7 fixture masks |
| masks/geometry_preserved.png | Composite mask | Copy of window.png |
| manifest.json | Metadata | New manifest for surface-only scene |
| technical_spec_surface.md | Metadata | Extracted from original tech spec |

---

## Entities Included

### Primary Surfaces (to render)

| Entity | Mask | Reference | Critical |
|--------|------|-----------|----------|
| floor | masks/floor.png | references/floor_tiles.jpg | Yes |
| walls_tile | masks/walls_tile.png | references/wall_tiles.png | Yes |
| walls_upper | masks/walls_upper.png | — | Yes |

### Preserved Geometry

| Entity | Mask | Notes |
|--------|------|-------|
| window | masks/window.png | Natural light source, must remain unchanged |

---

## Entities Excluded

| Entity | Reason |
|--------|--------|
| bathtub | Surface-only experiment |
| vanity | Surface-only experiment |
| mirror | Surface-only experiment |
| faucet | Surface-only experiment |
| rainshower | Surface-only experiment |
| towel_warmer | Surface-only experiment |
| basket | Surface-only experiment |
| shower_screen | Surface-only experiment |

---

## Mask Coverage

| Mask | Coverage |
|------|----------|
| floor.png | 1.5% |
| walls_tile.png | 13.8% |
| walls_upper.png | 12.3% |
| surfaces_combined.png | 29.9% |
| fixtures_all.png | 9.4% |
| window.png | 0.2% |

---

## Intended Use

This bundle is prepared for workflows SF1–SF5:

- **SF1**: Floor only
- **SF2**: Walls only (tile + upper)
- **SF3**: Sequential (floor → walls)
- **SF4**: Parallel (single pass)
- **SF5**: With fixture preservation

See `docs/specs/EPIC_D_SURFACE_ONLY.md` for workflow definitions and acceptance criteria.

---

## Important Notes

1. **walls_upper has no image reference** — evaluated by color, consistency, and boundary quality (see technical_spec_surface.md)

2. **walls_tile/walls_upper split** was done by brightness analysis:
   - Bright pixels (>210) → walls_tile
   - Gray pixels (150-210) → walls_upper
   - This approximation may need manual verification

3. **No renders were executed** in creating this bundle — artifact preparation only

4. **Window is preserved geometry** — should remain unchanged in all workflows

---

## Validation Checklist

- [x] Core images present (beauty, depth, boundary_mask)
- [x] All surface masks present (floor, walls_tile, walls_upper)
- [x] All composite masks present (surfaces_combined, fixtures_all, geometry_preserved)
- [x] References present (floor_tiles.jpg, wall_tiles.png)
- [x] manifest.json with 4 entities
- [x] technical_spec_surface.md created
- [ ] Visual verification of walls_tile/walls_upper split (pending)
