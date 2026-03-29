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

## File Locations

```
irp.rb          — ~/sketchup-share/ or http://100.96.1.25:9090/
render.py       — render/render.py
validate.py     — render/validate.py
experiment.py   — render/experiment.py
workflow.json   — render/workflow.json
BUNDLE_SPEC.md  — specs/BUNDLE_SPEC.md
```
