# IPAdapter Diagnostic — VERDICT

## Test Results Summary

| Test | Setup | Result | Observation |
|------|-------|--------|-------------|
| D1 | IPAdapter only (no ControlNet), weight=1.0 | ✅ PASS | **Blue patterned tiles clearly visible!** IPAdapter works perfectly without ControlNet. |
| D2 | Reference loading check | ✅ PASS | floor_tiles.jpg (424KB, 1726x1679), wall_tiles.png (300KB, 1024x1024) — both exist and load. |
| D3 | Workflow graph audit | ✅ PASS | sampler.model correctly connected to IPAdapter chain output. Connections are correct. |
| D4 | Low Canny (0.3) + IPAdapter (0.7) | ❌ FAIL | Dark textured surface, **no blue tiles**. Canny still overrides IPAdapter. |

## Root Cause Analysis

### Confirmed: IPAdapter WORKS
D1 proves IPAdapter transfers reference textures correctly when used alone:
- Weight 1.0
- No ControlNet interference
- Blue patterned tiles from reference are clearly visible

### Confirmed: ControlNet Conflicts with IPAdapter
D4 shows that even LOW Canny strength (0.3) prevents IPAdapter from applying reference textures:
- The model generates texture based on Canny edges, not reference images
- IPAdapter style influence is suppressed by ControlNet conditioning

### Hypothesis: Conditioning Priority Conflict
ControlNet applies conditioning to the positive/negative CLIP embeddings.
IPAdapter modifies the model's attention to reference images.

When both are active:
1. ControlNet says "follow these edges"
2. IPAdapter says "style like this reference"
3. The model prioritizes ControlNet geometric guidance over IPAdapter style

## Recommendations

### Option A: Sequential Processing (Recommended)
1. First pass: IPAdapter only → generates styled image
2. Second pass: ControlNet refines geometry on styled image

### Option B: IPAdapter-Only for Surface Experiment
- Remove ControlNet entirely for SF (Surface) experiments
- Use masks + IPAdapter regional for material application
- Accept that geometry comes from mask shapes, not Canny edges

### Option C: Extreme Parameter Tuning
- IPAdapter weight: 1.0 (max)
- IPAdapter end_at: 0.3 (early only, let ControlNet take over later)
- Canny strength: 0.1 (minimal)
- May still not work; ControlNet fundamentally overrides style

## Next Steps

1. **Test Option B**: Run SF1 with NO ControlNet, IPAdapter regional only
2. **Compare**: D1 result vs SF1c-v2 (which also had no ControlNet)
3. **Decision**: Choose between geometry precision (ControlNet) vs style transfer (IPAdapter)

## Conclusion

**IPAdapter is NOT broken. The conflict is architectural.**

ControlNet and IPAdapter compete for control over generation. For surface material rendering, we need to choose:
- **ControlNet**: Precise geometry, generic textures
- **IPAdapter**: Reference textures, approximate geometry

Cannot have both at full strength simultaneously.
