# B5 Minimal Texture Debug

## Test Results

| Test | Description | Result | Image |
|------|-------------|--------|-------|
| 1 | Cube + texture | ✅ PASS | Blue stripe visible |
| 2 | Plane + Generated UV | ✅ PASS | 2x2 tiled pattern |
| 3 | GLB + all meshes textured | ✅ PASS | Entire bathroom in blue tiles |

## Root Cause Analysis

### What Works:
1. **Texture loading** - `tex.image.load()` works correctly
2. **Node connections** - `tex → bsdf → output` chain works
3. **Object coordinates** - Work for 3D projection without UVs
4. **Primitive meshes** - Cube, Plane texture correctly
5. **Imported GLB** - Textures work when applied to ALL meshes

### What Didn't Work in B1-B4:
1. **Per-face material assignment** - Assigning different materials to different faces doesn't render textures in Cycles (material shows but texture coords don't work per-face)
2. **Vertex color mixing** - Works for solid colors but texture sampling via vertex colors is complex

### The Fix:
For the bathroom scene, textures work when:
- Material is applied to the **entire mesh** (not per-face)
- Using **Object coordinates** for UV mapping
- Scale ~0.5 gives good tile density

### Recommendation:
Instead of per-face material assignment, use **one mixed material per mesh** that switches textures based on world position or normal direction using shader nodes.

## Checklist Results

- [x] Texture file exists and readable
- [x] Image loaded in Blender (tex.image is not None)
- [x] Image has pixels (1726 x 1679)
- [x] Node links correct
- [x] Material assigned to mesh
- [x] Render engine = Cycles
- [x] Light exists in scene

All checklist items pass. The issue was **per-face assignment**, not texture loading.
