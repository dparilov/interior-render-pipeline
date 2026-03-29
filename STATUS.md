# Implementation Status

> Honest state of what works, what's stub, what's planned

## Legend

- ✅ **Works** — tested, produces expected output
- 🔧 **Partial** — code exists, needs fixes or testing
- 📄 **Stub** — placeholder, not functional
- 📋 **Planned** — spec exists, no code yet

---

## Pipeline Stages

| Stage | Status | Notes |
|-------|--------|-------|
| **Phase 0: Extract** | ✅ Works | `irp_extract.rb` tested, outputs scene_graph.json + beauty.png |
| **Phase 1: Mapping** | 🔧 Partial | Manual AI-assisted process, no automation |
| **Phase 2: Export** | ✅ Works | `irp_export.rb` tested, outputs masks + models |
| **Phase 3: Visual QA** | 🔧 Partial | Manual review, scoring documented |
| **Phase 4: Render** | 🔧 Partial | workflow.json works, render.py needs testing |

---

## Components

### SketchUp Scripts

| File | Status | Notes |
|------|--------|-------|
| `sketchup/irp.rb` | ✅ Works | Single script: IRP.extract + IRP.export |

**Exports:**
- scene_graph.json, beauty.png (extract)
- depth.png, boundary_mask.png, masks/, models (export)

### Render

| File | Status | Notes |
|------|--------|-------|
| `render/workflow.json` | ✅ Works | Tested with ComfyUI manually |
| `render/render.py` | 📄 Stub | API orchestrator, untested |

### Specs

| File | Status | Notes |
|------|--------|-------|
| `specs/BUNDLE_SPEC.md` | ✅ Stable | v1.0 schema finalized |
| `specs/RENDERING.md` | ✅ Stable | Entity classes documented |

### Examples

| Example | Status | Notes |
|---------|--------|-------|
| `examples/bathroom_01/manifest.json` | ✅ Complete | v1.0 schema with all entities |
| `examples/bathroom_01/beauty.png` | ✅ Complete | 1920×1080 source render |
| `examples/bathroom_01/masks/` | ✅ Complete | 10 binary masks |
| `examples/bathroom_01/references/` | ✅ Complete | 9 reference images |
| `examples/bathroom_01/render.png` | ✅ Complete | Output from workflow.json |

---

## Features

### Implemented

- [x] Single script workflow (IRP.extract + IRP.export)
- [x] Recursive scene graph extraction (20 levels deep)
- [x] PID-based entity mapping
- [x] Binary mask export with occlusion
- [x] **Depth map from SketchUp geometry** (ground truth)
- [x] **Boundary mask** (room silhouette for latent masking)
- [x] IRP_* naming for model export
- [x] Group → Component conversion (with rollback)
- [x] ZIP output next to .skp file
- [x] Dual ControlNet (Canny + SketchUp Depth)
- [x] Regional IPAdapter with attention masks
- [x] Entity class separation (surface/fixture/opening)
- [x] Fixed seed for reproducibility
- [x] Aspect ratio preservation

### Partially Implemented

- [ ] Python render orchestrator (code exists, untested)
- [ ] Bundle validation
- [ ] Progress reporting

### Planned (Not Started)

- [ ] Automated Phase 1 (AI mapping API)
- [ ] Multi-pass rendering
- [ ] Tiling projection for surfaces
- [ ] Local inpaint for details
- [ ] CI/CD pipeline
- [ ] Complete example bundle with real images

---

## Test Coverage

| Test | Status |
|------|--------|
| Unit tests | ❌ None |
| Integration tests | ❌ None |
| Manual E2E test | ✅ Passed (bathroom scene) |

---

## Known Issues

| Issue | Severity | Workaround |
|-------|----------|------------|
| window.png hollow mask | Medium | Fix recursive face painting |
| bathtub.png toilet leak | Medium | Adjust geometry overlap |
| walls.png gray tones | Low | Check material rendering |
| CPU rendering slow | Low | ~2 min/step, use overnight |

---

## Next Steps (Priority Order)

1. ~~**Complete bathroom_01 example**~~ ✅ Done
2. **Test render.py** — verify Python orchestrator works end-to-end
3. **Fix mask issues** — window, bathtub, walls
4. **Add validation** — bundle schema validation script

---

*Last updated: 2026-03-29*
