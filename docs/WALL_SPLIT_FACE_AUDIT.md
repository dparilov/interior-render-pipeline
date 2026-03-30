# Wall Semantic Split: Face-Level Audit

**Date:** 2026-03-30
**Target:** pid=36696 (walls Group)
**Status:** ✅ COMPLETE

---

## Conclusion

**Split EXISTS at face/material level.**

The SketchUp Group pid=36696 contains 38 faces with **4 different materials**:
- **Материал1** → walls_tile (lower portion, Z ≈ 0.9m)
- **0131_Серебристый** → walls_upper (upper portion, Z ≈ 1.95-2.94m)
- **Цвет M00** → trim/edges (transitions, window frame)
- **none** → structural faces (floor, ceiling, outer walls)

**Canonical masks CAN be rebuilt from face-level semantics.**

---

## Evidence

### Face Material Inventory (pid=36696)

| Material | Count | Area (m²) | Z Range (m) | Interpretation |
|----------|-------|-----------|-------------|----------------|
| none | 8 | 24.26 | 0.0 - 3.0 | Structural (floor, ceiling, outer walls) |
| Материал1 | 7 | 11.71 | 0.90 | **WALLS_TILE** (white Costa Nova tiles) |
| 0131_Серебристый | 12 | 7.31 | 1.95 - 2.94 | **WALLS_UPPER** (gray painted wall) |
| Цвет M00 | 11 | 0.84 | 2.03 - 2.97 | Trim/edges (window, transitions) |

### Z-Height Distribution

```
Z = 0.0m:  none (structural floor)
Z = 0.9m:  Материал1 (ALL tile faces at this height)
Z = 1.5m:  none (structural)
Z = 2.0m+: 0131_Серебристый + Цвет M00 (upper wall + trim)
Z = 3.0m:  none + Цвет M00 (ceiling + trim)
```

### Key Finding

**Clear height-based material separation:**
- **Материал1** concentrated at Z ≈ 0.9m (lower wall - TILES)
- **0131_Серебристый** concentrated at Z ≈ 2.0-2.9m (upper wall - GRAY)
- This is exactly the tile/upper split we were looking for!

---

## Does Material-Level Split Exist?

**YES.**

The split exists in the SKP file at the per-face material level:
- 7 faces with "Материал1" = tile area
- 12 faces with "0131_Серебристый" = upper gray wall

---

## Can Canonical Masks Be Rebuilt?

**YES.**

To generate masks from face semantics:

1. For each face with material "Материал1" or "0131_Серебристый":
   - Project face vertices to 2D camera view
   - Fill polygon on mask image

2. Generate separate masks:
   - `walls_tile.png` ← faces with "Материал1"
   - `walls_upper.png` ← faces with "0131_Серебристый"

This would produce **semantically correct** masks without brightness-based heuristics.

---

## Where Is The Split Lost?

### Loss Point: IRP Extract (scene_graph serialization)

The current `collect_entities_recursive()` in `irp.rb` captures:
- Group/Component objects
- Group-level material (which is null for pid=36696)
- Face count

**But does NOT capture:**
- Per-face materials
- Face geometry for projection

### Evidence

scene_graph.json for pid=36696:
```json
{
  "pid": 36696,
  "material": null,
  "face_count": 38
}
```

Face materials exist in SKP but are not serialized.

### Secondary Loss: GLB Export

SketchUp's GLB export also loses per-face materials:
```
Geom3D_IRP_walls: 1 primitive, material=None
```

Materials `[0128_White]` and `[0134_DimGray]` exist in GLB but are not assigned to walls mesh.

---

## Recommended Pipeline Change

### Option 1: Enhance scene_graph.json

Add per-face material capture to `collect_entities_recursive()`:

```ruby
def self.collect_entities_recursive(entities, depth)
  result = []
  entities.each do |e|
    next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
    
    inner = e.is_a?(Sketchup::Group) ? e.entities : e.definition.entities
    
    # NEW: Capture per-face materials
    face_materials = {}
    inner.grep(Sketchup::Face).each do |face|
      mat = face.material || face.back_material || e.material
      mat_name = mat ? mat.display_name : 'none'
      face_materials[mat_name] ||= { count: 0, area: 0, faces: [] }
      face_materials[mat_name][:count] += 1
      face_materials[mat_name][:area] += face.area
      face_materials[mat_name][:faces] << {
        center: face.bounds.center.to_a,
        normal: face.normal.to_a
      }
    end
    
    result << {
      pid: e.persistent_id,
      # ... existing fields ...
      face_materials: face_materials  # NEW
    }
  end
  result
end
```

### Option 2: Auto-Split Groups by Material

When generating masks, detect per-face materials and create sub-entities:

```ruby
def self.maybe_split_by_material(entity, role_info)
  inner = entity.entities
  face_mats = inner.grep(Sketchup::Face).group_by { |f| f.material&.display_name || 'none' }
  
  if face_mats.length > 1 && role_info[:class] == 'surface'
    # Generate separate masks for each material
    face_mats.each do |mat_name, faces|
      generate_mask_for_faces(faces, "#{role_info[:name]}_#{mat_name}")
    end
  end
end
```

### Option 3: Generate Masks from Face Audit

Use `face_audit.rb` output to generate canonical masks:

1. Load `face_audit_36696.json`
2. Group faces by material
3. Project face bounds to camera view
4. Render masks for each material group

---

## Updated Conclusion

| Question | Answer |
|----------|--------|
| Split exists at face/material level? | **YES** |
| Can canonical masks be built? | **YES** (from face geometry + camera projection) |
| Where is split lost? | IRP extract (scene_graph serialization) |
| Why is it lost? | `collect_entities_recursive()` doesn't capture per-face materials |
| Is brightness fallback justified? | **NO** — semantic data exists, should be used |

---

## Action Items

1. ✅ Face-level audit complete
2. 🔲 Update scene_graph.json schema to include face_materials
3. 🔲 Implement mask generation from face geometry
4. 🔲 Regenerate walls_tile.png and walls_upper.png from semantic data
5. 🔲 Update manifest to reflect semantic source

---

## Audit Data Source

```
File: face_audit_36696.json
Date: 2026-03-30T23:50:37+03:00
SKP: bathroom_work.skp
Target: pid=36696 (walls Group)
Total faces: 38
Materials found: 4
```
