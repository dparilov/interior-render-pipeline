# IRP Status v1.1

## Pipeline Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0. Extract | ✅ Ready | Scene-locked extraction |
| 1. Mapping | ✅ Ready | ТЗ-aware AI mapping |
| 2. Export | ✅ Ready | Full bundle with traceability |
| 3. Validate | ✅ Ready | Schema + file validation |
| 4. Render | ✅ Ready | Experiment tracking |

## Contract Status

| Contract | Spec | Exporter | Validator | Renderer |
|----------|------|----------|-----------|----------|
| version | 1.1 | ✅ | ✅ | ✅ |
| scene_id | ✅ | ✅ | ✅ | ✅ |
| depth_map | ✅ | ✅ | ✅ | ✅ |
| boundary_mask | ✅ | ✅ | ✅ | ✅ |
| technical_spec | ✅ | ✅ | ✅ | ✅ |
| entity.pid | ✅ | ✅ | ✅ | — |
| entity.coverage_pct | ✅ | ✅ | ✅ | — |
| entity.prompt_source | ✅ | ✅ | ✅ | — |
| entity.critical | ✅ | ✅ | ✅ | — |

## Recent Changes (v1.1)

### P0 Fixes (Blocking)

1. **Unified manifest contract** — BUNDLE_SPEC v1.1 with all required fields
2. **ТЗ traceability** — technical_spec object with path, hash, summary
3. **Experiment module** — Full logging from actual workflow params
4. **Bundle validator** — Schema and file validation before render
5. **Scene locking** — Extract locks scene, export uses same camera

### P1 Improvements

1. **Binary boundary mask** — paint_entity_solid() for pure white
2. **Coverage calculation** — Stored in manifest per entity
3. **Honest parameter logging** — Extracted from workflow, not hardcoded
4. **prompt_source field** — Traces each prompt to ТЗ section

## Known Limitations

1. Coverage calculation is approximate (file size based)
2. Multi-view export disabled pending API fixes
3. Experiment completion requires manual poll of ComfyUI
4. **SketchUp antialias hardcoded to 2X** — masks require Python binarization (postprocess.py)

## Current Experiment: S1 (Structural Baseline)

**Status:** 🔄 Running

**Prompt ID:** `d3b4e3a1-c581-449e-b615-8d031e1a21c7`
**Started:** 2026-03-29 15:45 UTC+3
**ETA:** ~1.5h (CPU render)

### S1 Parameters

| Parameter | Value |
|-----------|-------|
| Checkpoint | RealVisXL_V4.0 |
| IPAdapter | ip-adapter-plus_sdxl_vit-h |
| CLIP Vision | CLIP-ViT-H-14-laion2B |
| ControlNet Canny | 0.8 (end 0.9) |
| ControlNet Depth | 0.9 (end 0.8) |
| Sampler | dpmpp_2m_sde + karras |
| Steps | 50 |
| CFG | 7.0 |
| Seed | 42 |
| Resolution | 1920×1080 |

### IPAdapter Weights (per class)

| Class | Weight | Mode |
|-------|--------|------|
| surface | 0.55 | regional_ipadapter |
| fixture | 0.50 | regional_ipadapter |
| opening | 0.00 | structural_controlnet |

### Bundle Validation (pre-render)

| Check | Status |
|-------|--------|
| Schema | ✅ Valid |
| Masks binary | ✅ All binarized |
| References | ✅ 9 files |
| Technical spec | ✅ sha256:c312... |
| Visual QA | ✅ 81.8 avg score |

## File Locations

```
irp.rb          — ~/sketchup-share/ or http://100.96.1.25:9090/
render.py       — render/render.py
validate.py     — render/validate.py
experiment.py   — render/experiment.py
workflow.json   — render/workflow.json
BUNDLE_SPEC.md  — specs/BUNDLE_SPEC.md
```
