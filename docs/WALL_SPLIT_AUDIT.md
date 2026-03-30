# Wall Semantic Split Audit

**Date:** 2026-03-30
**Scene:** bathroom_01
**Question:** Why is walls_tile / walls_upper split unavailable as semantic data?

---

## Conclusion

**Split truly absent in source extract.**

The SketchUp scene contains walls as a **single flat Group with no internal structure**.
There is no semantic separation between tile area and upper gray wall at any point
in the pipeline — the split does not exist in the source model.

---

## Evidence Chain

### 1. Upstream Extract (scene_graph.json)

**Source:** `/home/dima/sketchup-share/gamma_extract/irp_extract/scene_graph.json`

Entity `pid=36696` (walls):
```json
{
  "pid": 36696,
  "type": "Group",
  "name": null,
  "child_count": 0,
  "face_count": 38,
  "material": null
}
```

**Findings:**
- `child_count: 0` — no nested components
- `face_count: 38` — all faces belong to single Group
- `material: null` — no material assignment at Group level
- No other entities in scene_graph represent wall sub-components

### 2. Role Map (role_map.json)

**Source:** `/home/dima/sketchup-share/gamma_extract/role_map.json`

```json
{
  "pid": 36696,
  "name": "walls",
  "role": "surface.walls",
  "class": "surface"
}
```

**Findings:**
- Single role assignment for entire walls Group
- No separate entries for tile/upper
- role_map reflects scene_graph structure accurately

### 3. GLB Export (model.glb)

**Source:** `examples/bathroom_01/model/model.glb`

```
Node [141]: Geom3D_IRP_walls
  mesh: 71
  Mesh primitives: 1
  Primitive 0: material=None
```

Materials in GLB:
- `[0128_White]` — exists but not assigned to walls
- `[0134_DimGray]` — exists but not assigned to walls

**Findings:**
- Walls mesh has single primitive
- Material not assigned (None)
- Gray/white materials exist but are not linked to walls geometry
- Export did not preserve per-face material assignments

### 4. Manifest (manifest.json)

**Source:** `examples/bathroom_01/manifest.json`

```json
{
  "pid": 36696,
  "name": "walls",
  "role": "surface.walls",
  "surface_kind": "wall_tiles"
}
```

**Findings:**
- Single entity for walls
- `surface_kind: wall_tiles` — assumes entire mask is tiles
- No representation of upper gray wall

---

## Last Artifact Where Split Could Exist

**None found.**

The original SketchUp model appears to have walls modeled as a single Group.
The 38 faces likely include both tile area and upper wall, but they are not
separated into different Groups or Components.

## First Artifact Where Split is Lost

**N/A — split never existed.**

The scene_graph.json (direct extract from SKP) already shows walls as
a single entity with no children.

---

## Cause of Loss

**Not a pipeline loss — source model lacks semantic structure.**

The SketchUp model was created with walls as a unified Group. The distinction
between tile area and upper painted wall exists only visually (through materials/
textures applied to faces), not structurally (as separate objects).

### Why materials don't help

SketchUp allows per-face material assignment within a Group. However:
1. IRP extract collects **objects** (Groups/Components), not faces
2. Material assignments on individual faces are not captured in scene_graph
3. GLB export flattens per-face materials or loses them entirely

---

## Can Split Be Recovered?

### Without modifying source model: NO

The current pipeline cannot recover tile/upper split because:
- scene_graph operates on object level, not face level
- Material assignments are not captured per-face
- GLB export does not preserve face-level semantics

### With source model modification: YES

If the SketchUp model were restructured:
1. Create separate Group for tile area
2. Create separate Group for upper wall
3. Re-run IRP.extract

This would produce two entities in scene_graph with distinct PIDs.

### Alternative: Pipeline enhancement

Modify IRP extract to:
1. Detect per-face material assignments within Groups
2. Auto-split Groups by material into sub-entities
3. Assign separate PIDs to material-defined regions

This would require significant changes to `irp.rb`.

---

## Canonical Recommendation

1. **For bathroom_01:** Accept brightness-derived fallback as interim solution.
   Document that source model lacks structural split.

2. **For future scenes:** Model wall tile area and upper wall as separate
   Groups/Components in SketchUp before running IRP extract.

3. **For pipeline:** Consider adding face-level material detection to
   `collect_entities_recursive()` in `irp.rb` to auto-generate sub-entities.

---

## Artifacts Inspected

| Artifact | Location | Split Present |
|----------|----------|---------------|
| scene_graph.json | ~/sketchup-share/gamma_extract/irp_extract/ | ❌ No |
| role_map.json | ~/sketchup-share/gamma_extract/ | ❌ No |
| model.glb | examples/bathroom_01/model/ | ❌ No |
| manifest.json | examples/bathroom_01/ | ❌ No |
| SKP file | Not in repository | ❓ Not inspected |

**Note:** Original SKP file was not directly inspected, but scene_graph.json
is a faithful representation of the SKP object hierarchy. The absence of
split in scene_graph confirms absence in SKP (at object level).

---

## Status

✅ Audit complete.
- Split truly absent in source model (at object level)
- Not a pipeline loss
- Brightness-derived fallback is justified for this scene
- Future scenes should use separate Groups for distinct wall surfaces
