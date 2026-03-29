# Interior Render Pipeline — Backlog

## Strategic Direction

Two major expansion tracks:

1. **Epic A**: Automatic multi-camera / multi-view scene generation
2. **Epic B**: Progressive removal of SketchUp dependency via Blender-first path

**Sequencing:**
- Phase 1: Multi-view support on current SketchUp pipeline
- Phase 2: Blender-first alternative with parity
- Phase 3: Optional full SketchUp removal (only after proven parity)

---

# Epic A — Automatic Camera Placement and Multi-View Rendering

## Goal

Automatically generate multiple useful viewpoints, export masks/depth/beauty for each, optionally combine views for better final render.

## Why This Matters

Current single-camera limitation causes:
- Hidden or partially visible objects
- Weak masks for important entities
- Poor spatial understanding
- Inability to use alternate views as evidence

Multi-view should improve:
- Geometry preservation
- Object completeness
- Better masks and references
- More reliable regional IPAdapter behavior

---

## Epic A1 — Automatic Camera Placement in SketchUp

### Task A1.1 — Define Camera Placement Rules

**Status:** ⏳ TODO

Implement deterministic rules for generating candidate cameras.

**Default camera set:**
- overview_corner_1..4
- doorway_view
- focal_fixture_view
- vanity_closeup
- bathtub_closeup

**Rules:**
- Camera height: 140–170 cm
- FOV: configurable, default 60°
- Avoid clipping through walls
- Maximize visible room area
- Maximize visibility of critical entities

**Acceptance criteria:**
- [ ] Generated cameras are reproducible
- [ ] All critical entities visible in at least one view
- [ ] Camera definitions exported to manifest

---

### Task A1.2 — Camera Scoring and Selection

**Status:** ⏳ TODO

Automatic scoring of candidate views.

**Scoring inputs:**
- Visible floor area
- Visible wall area
- Number of critical entities visible
- Mask coverage for each entity
- Amount of occlusion
- Image balance / framing

**Output:**
- Select top N views
- Save score per camera

**Manifest example:**
```json
{
  "views": [
    {
      "id": "overview_corner_1",
      "score": 0.91,
      "critical_entities_visible": ["walls", "floor", "bathtub"]
    }
  ]
}
```

---

### Task A1.3 — Multi-View Bundle Export

**Status:** ⏳ TODO

**Bundle structure:**
```
bundle/
  views/
    view_01/
      beauty.png
      depth.png
      masks/
    view_02/
      ...
  manifest.json
```

**Manifest includes:**
- View metadata
- Camera transform
- Image resolution
- Entity coverage per view

---

### Task A1.4 — Multi-View Rendering Strategy

**Status:** ⏳ TODO

**Rendering modes:**
1. Best-single-view
2. Render each view independently
3. Multi-view fusion
4. Secondary views only for hidden entities

**Recommended first implementation:**
- Primary render from best view
- Additional views only for hidden/weak entities

---

### Task A1.5 — Add Multi-View Experiment Block

**Status:** ⏳ TODO

| ID | Test | Purpose |
|----|------|---------|
| MV1 | Single best view | Baseline |
| MV2 | Best two views | Coverage improvement |
| MV3 | Best four views | Full coverage |
| MV4 | Critical entity guided | Smart selection |
| MV5 | Multi-view + refiner | Quality test |

**Metrics:**
- Entity preservation
- Geometry consistency
- Visible artifact reduction
- Overall subjective score

---

# Epic B — Blender-First Import and SketchUp Independence

## Goal

Operate without SketchUp by:
- Importing 3D formats directly into Blender
- Generating masks/depth/beauty there
- Extracting semantic roles automatically

## Maturity Levels

| Level | Description | SketchUp Role |
|-------|-------------|---------------|
| 0 | Current | Primary |
| 1 | Hybrid | Role-map fallback only |
| 2 | Blender-first | No dependency in normal path |
| 3 | SketchUp-free | No dependency at all |

**Target:** Level 1 and Level 2 first.

---

## Epic B1 — Evaluate Import Formats and Conversion

### Task B1.1 — Supported Input Format Matrix

**Status:** ⏳ TODO

| Format | Blender Support | Hierarchy | Materials | Notes |
|--------|-----------------|-----------|-----------|-------|
| glTF/GLB | Excellent | Yes | Good | **Preferred** |
| FBX | Good | Usually | Medium | Backup |
| OBJ | Basic | Weak | Weak | Geometry only |
| DAE | Medium | Medium | Medium | Possible |
| IFC | Varies | Strong | Weak | Architectural |
| USD/USDZ | Emerging | Strong | Medium | Future |
| SKP direct | Weak | Unknown | Weak | Avoid |

**Canonical format:** GLB + optional sidecar JSON

---

### Task B1.2 — SKP → Blender Conversion Options

**Status:** ⏳ TODO

Evaluate:
1. SketchUp native export to GLB
2. SketchUp native export to FBX
3. SketchUp native export to DAE
4. Blender SKP import plugins
5. Third-party conversion tools
6. Headless conversion path

**For each evaluate:**
- Geometry fidelity
- Hierarchy fidelity
- Material names preserved
- Object names preserved
- Layer/tag names preserved
- Speed
- Licensing / automation suitability

**Deliverable:** Comparison table and recommendation

**Hypothesis:** SKP → GLB will be preferred path.

---

### Task B1.3 — Headless Conversion Pipeline

**Status:** ⏳ TODO

**Pipeline:**
```
SKP → converter → GLB → Blender bundle generator
```

**Requirements:**
- Fully scriptable
- No GUI
- Reproducible
- Works on server / cloud

---

## Epic B2 — Automatic Role Extraction in Blender

### Task B2.1 — Recursive Scene Analysis

**Status:** ⏳ TODO

Traverse Blender scene and collect:
- Object name
- Collection hierarchy
- Material names
- Mesh size
- Bounding box
- Location in room
- Parent-child relationships

**Output:**
```json
{
  "object": "Bathtub_001",
  "collection": "Bathroom/Fixtures",
  "materials": ["WhiteCeramic"],
  "bbox": [1.7, 0.8, 0.6]
}
```

---

### Task B2.2 — Heuristic Role Classification

**Status:** ⏳ TODO

**Infer roles:** surface, fixture, decor, opening, appliance

**Using:**
- Object name
- Collection path
- Material names
- Dimensions
- Room position

**Examples:**
- Name contains "wall" → role=surface
- Large horizontal plane → floor
- Ceramic object near wall → bathtub/sink

---

### Task B2.3 — Confidence and Human Review

**Status:** ⏳ TODO

Role extraction should include confidence:

```json
{
  "name": "Bathtub_001",
  "predicted_role": "fixture",
  "confidence": 0.84,
  "reason": "material contains ceramic; size matches bathtub"
}
```

Low-confidence items flagged for manual review.

---

### Task B2.4 — Auto-Generated roles_map.json

**Status:** ⏳ TODO

**Produce:**
- roles_map.json
- requires_review list
- unresolved objects list

Replaces SketchUp role-map export.

---

## Epic B3 — Multi-Format Canonical Bundle

**Status:** ⏳ TODO

Bundle independent of source application.

**Always contains:**
- base_image
- depth_map
- entities[]
- views[]
- camera metadata
- roles_map
- references
- technical_spec

**No downstream step should know source:**
- SketchUp
- Blender
- GLB / FBX
- Converted SKP

---

## Blender Independence Experiments

| ID | Test | Purpose |
|----|------|---------|
| BX1 | GLB import parity vs SketchUp | Format comparison |
| BX2 | FBX import parity vs SketchUp | Format comparison |
| BX3 | Auto role extraction accuracy | Classification test |
| BX4 | Full Blender-first render | End-to-end test |
| BX5 | Multi-view Blender-first | Coverage test |
| BX6 | SketchUp-free SKP conversion | Independence test |

**Metrics:**
- Entity detection accuracy
- Role classification accuracy
- Mask overlap / IoU
- Render quality
- Bundle completeness
- Required manual corrections

---

# Priority

## Immediate (Next Sprint)

1. A1.1 — Camera placement rules
2. A1.2 — Camera scoring
3. A1.3 — Multi-view bundle format
4. B1.2 — SKP → GLB conversion benchmark
5. B2.1 — Recursive scene analysis
6. B2.2 — Heuristic role classification

## Later

- Full multi-view fusion
- Direct SKP-free path
- Advanced semantic classification (ML)

---

# Key Risks

| Risk | Mitigation |
|------|------------|
| Too many views → slow runtime | Limit to top N views |
| Poor auto camera placement | Manual override option |
| Blender import loses naming | Strict naming convention |
| Role extraction accuracy weak | Human review fallback |
| Full SketchUp removal premature | Keep until parity proven |

---

# Policy

**Keep SketchUp path canonical until Blender-first path reaches measurable parity.**

Only then consider deprecating SketchUp.
