# Known Issues

## 1. Front Wall Clipping (BLOCKING)

**Problem:** SketchUp viewport clipping plane doesn't export to DAE/GLB.

**Symptoms:** 
- Camera positioned outside room, looking through doorway
- Front wall geometry blocks wider interior view
- `IRP_walls` is single mesh, can't hide wall selectively

**Current Workarounds:**
1. **Manual hide in SketchUp** — Hide front wall layer before export
2. **Camera inside room** — Different scene setup (wider FOV needed)
3. **Face deletion in Blender** — Remove faces with Y < threshold

**Proper Solution (TODO):**
- Detect Section Planes in Ruby API
- Export clipping info to manifest
- Apply clipping in Blender before render

## 2. Mirror Reflection

**Problem:** Mirrors render as solid black.

**Cause:** No reflection material setup in Blender.

**Solution:**
```python
# Create glossy BSDF material for mirrors
mat = bpy.data.materials.new("Mirror")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()
glossy = nodes.new('ShaderNodeBsdfGlossy')
glossy.inputs['Roughness'].default_value = 0.0
output = nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(glossy.outputs['BSDF'], output.inputs['Surface'])
```

## 3. DAE vs GLB Geometry Mismatch

**Problem:** DAE import has different bounds than GLB.

**Findings (Phase B):**
- GLB: 200k verts, bounds X=[-0.69, 2.55]
- DAE: 175k verts, bounds X=[-0.66, 1.76]

**Cause:** DAE transforms not fully applied during import.

**Solution:** Use GLB for geometry, DAE only for camera reference.

## 4. Entity Naming in GLB

**Problem:** SketchUp entity names don't always survive GLB export.

**Solution:** `IRP.name_all_for_export` renames entities before export:
- `IRP_{name}` — mapped entities
- `HIDDEN_S_{pid}` — scene-hidden
- `HIDDEN_G_{pid}` — global-hidden
- `EXCLUDED_{name}` — excluded

## 5. Texture Scaling

**Problem:** Floor/wall textures appear wrong scale in render.

**Cause:** UV coordinates from SketchUp need adjustment.

**Status:** Partially solved with manual texture_scale parameter.
