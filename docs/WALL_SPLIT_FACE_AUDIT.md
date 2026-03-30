# Wall Semantic Split: Face-Level Audit

**Date:** 2026-03-30
**Target:** pid=36696 (walls Group)
**Status:** ⚠️ INCOMPLETE — requires SketchUp execution

---

## Conclusion

**Evidence incomplete.**

GLB export has lost per-face material assignments. Face-level audit requires
running `face_audit.rb` script in SketchUp with access to the original SKP file.

Cannot determine if per-face material split exists without direct SKP inspection.

---

## Evidence

### 1. GLB Analysis

**Source:** `examples/bathroom_01/model/model.glb`

```
Node 'Geom3D_IRP_walls': mesh index = 71

Mesh:
  Primitives count: 1
  Primitive 0:
    Material: None
    Vertices: 55
    Attributes: ['NORMAL', 'POSITION']
```

**Finding:** GLB mesh has:
- Single primitive (no material-based split)
- Material = None (not assigned)
- No vertex colors
- 55 vertices for 38 faces (shared vertices)

### 2. Materials in GLB

Relevant materials that exist in GLB:
- `[0128_White]` — white (no color factor, likely texture-based)
- `[0128_White]1` — white variant
- `[0134_DimGray]` — gray RGB(0.41, 0.41, 0.41)

**Finding:** Gray and white materials exist but are **not assigned** to walls mesh.
This suggests per-face materials were lost during SKP → GLB export.

### 3. scene_graph.json

```json
{
  "pid": 36696,
  "material": null,
  "face_count": 38
}
```

**Finding:** Group-level material is null. scene_graph does not capture per-face materials.

### 4. SKP File Status

- **Location:** `/home/dima/sketchup-share/bathroom_work.skp`
- **Size:** 14,280,289 bytes
- **Access:** Available on filesystem

---

## What Is Known

| Level | Has Material Data | Split Visible |
|-------|-------------------|---------------|
| SKP file | Unknown (not inspected) | Unknown |
| scene_graph.json | Group-level only | No |
| GLB mesh | None assigned | No |
| Rendered image | Yes (visual) | Yes (brightness) |

---

## What Is NOT Known

1. **Do faces inside pid=36696 have different materials in SKP?**
   - Cannot determine from downstream artifacts
   - Requires SketchUp Ruby API inspection

2. **If materials exist, how are they distributed?**
   - By Z height (upper vs lower)?
   - By face orientation?
   - By connected regions?

3. **At what exact point are per-face materials lost?**
   - During IRP extract (scene_graph serialization)?
   - During GLB export from SketchUp?
   - Both?

---

## Required Action

### Run face_audit.rb in SketchUp

Script location: `sketchup/face_audit.rb`

```ruby
# In SketchUp Ruby Console:
load '/path/to/interior-render-pipeline/sketchup/face_audit.rb'
FaceAudit.run
```

Output will be saved to: `~/sketchup-share/face_audit_36696.json`

### Expected Output

```json
{
  "target_pid": 36696,
  "total_faces": 38,
  "material_summary": {
    "material_name": { "count": N, "area_m2": X.XX }
  },
  "z_material_distribution": {
    "Z_height": { "material_name": count }
  },
  "faces": [
    {
      "index": 0,
      "front_material": "...",
      "back_material": "...",
      "effective_material": "...",
      "center": [x, y, z],
      "area_m2": X.XX
    }
  ]
}
```

---

## Questions To Answer After Audit

1. **Are there faces with different materials inside pid=36696?**
   - If YES: split exists at face/material level
   - If NO: split does not exist even at face level

2. **If split exists, can canonical masks be built?**
   - Group faces by material
   - Project face centroids to 2D camera view
   - Generate separate masks for each material region

3. **Where is the split lost?**
   - If SKP has materials but scene_graph doesn't → lost in extract
   - If scene_graph has materials but GLB doesn't → lost in GLB export
   - If SKP doesn't have materials → never existed

---

## Interim Status

Until face_audit.rb is executed:

- **Cannot claim** "split absent in source model"
- **Cannot claim** "brightness fallback justified"
- **Status:** evidence incomplete

The current brightness-derived masks remain as **provisional fallback**,
not as architecturally justified solution.

---

## Updated Audit Chain

```
SKP file (bathroom_work.skp)
    │
    ├── [UNKNOWN] Per-face materials inside pid=36696?
    │
    ▼
scene_graph.json
    │
    └── [CONFIRMED] Group-level material: null
    │              Face-level materials: NOT captured
    │
    ▼
GLB export
    │
    └── [CONFIRMED] Single primitive, material: None
                    Per-face materials: LOST
    ▼
manifest.json
    │
    └── [CONFIRMED] Single entity "walls"
    ▼
Current bundle
    │
    └── [FALLBACK] Brightness-derived walls_tile/walls_upper
```

---

## Recommended Pipeline Enhancement

Regardless of audit outcome, IRP extract should be enhanced to capture per-face materials:

```ruby
def self.collect_face_materials(group)
  materials = {}
  group.entities.grep(Sketchup::Face).each do |face|
    mat = face.material || face.back_material || group.material
    mat_name = mat ? mat.display_name : 'none'
    materials[mat_name] ||= { count: 0, area: 0 }
    materials[mat_name][:count] += 1
    materials[mat_name][:area] += face.area
  end
  materials
end
```

This would allow detecting material-based splits without manual inspection.
