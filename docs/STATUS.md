# IRP Status

## Current State

| Component | Status |
|-----------|--------|
| Base Pipeline | ✅ Validated |
| Depth ControlNet | ✅ Validated |
| Canny ControlNet | ✅ Validated |
| Boundary Mask | ✅ Validated |
| Single-Entity Calibration | ✅ Validated |
| Refiner Integration | ✅ Validated |
| **Multi-IPAdapter Regional Workflow** | ✅ **VALIDATED** |
| **Blender Fallback Bundle Generation** | ✅ Implemented (partial parity) |

## Experiment Phases

### Phase A — Simplified Workflow Benchmark (COMPLETE)

Experiments S0-S1, I2-*, I4-*, R*, F*, T*, P* were run on simplified single-IPAdapter workflow.

**Important:** These results validate:
- Base structural pipeline
- Single-entity weight calibration
- Refiner capability

**They do NOT validate:**
- True multi-entity regional composition
- Entity ordering effects
- Full manifest-driven rendering

### Phase B — Multi-IPAdapter Validation ✅ COMPLETE

Completed:
1. ✅ workflow_builder.py — generates entity branches from manifest
2. ✅ Validators — manifest + workflow validation
3. ✅ M1-M6 validation tests — all passed
4. ✅ F*-v2, T*-v2, P*-v2 — all passed with true regional IPAdapter

**Multi-IPAdapter Results:**
- F1-v2: 4 regional adapters, 40s
- F2-v2: 9 regional adapters, 46s
- F2-order2-v2: 9 regional adapters (reversed), 50s
- T1-v2, T2-v2, T3-v2: all 9 adapters, ~40s each
- P1-v2 through P4-v2: production validated

## Canonical Path

**Phase B (multi_ipadapter_regional) is canonical for:**
- Block 4 Integration
- Block 5 Tech Spec  
- Block 6 Production

**Historical baseline:**
- Phase A results remain valid as simplified single-IPAdapter benchmark
- NOT canonical for final architecture claims

## Audit Prerequisites

✅ All satisfied:
- workflow_builder.py active
- manifest validator active
- workflow validator active
- per-experiment workflow snapshot saved
- workflow_hash logged
- entity_order logged
- entities_applied logged
- workflow_validation_passed logged
- workflow_validation_summary logged

---

## Candidate Workflows

**Important:** No workflow is declared as benchmark yet. All are candidates for evaluation.

| ID | Workflow | Status | Notes |
|----|----------|--------|-------|
| WF1 | phase_b_multi_ipadapter_regional | ✅ Implemented | Current Phase B |
| WF2 | render_v6_segmentation_regional | ✅ Reference | v6 with UperNet+SAM |
| WF3 | v6_plus_sketchup_masks | 📋 Planned | Hybrid: v6 + SketchUp masks |
| WF4 | phase_b_strong_prompt | 📋 Planned | Phase B + strong global prompts |
| WF5 | hybrid_best | 📋 Planned | Best elements combined |

### Render v6 Reference Parameters

From original v6 workflow:
- ControlNet Canny: strength 0.7, end_at 0.8
- ControlNet Depth: strength 0.5, end_at 0.6
- 9 Regional IP-Adapter with attention masks
- Steps: 50
- Sampler: dpmpp_2m_sde
- Scheduler: karras
- CFG: 7.0

### Phase B Current Parameters

- ControlNet Canny: strength 0.8, end_at 0.9
- ControlNet Depth: strength 0.9, end_at 0.8
- 9 Regional IPAdapterAdvanced with masks
- Steps: 50
- Sampler: euler
- Scheduler: normal
- CFG: 7.0

---

## Upcoming Epics

### Epic D — Surface-Only Validation

Validate rendering strategy for surfaces (floor, walls) separately from fixtures.

| Task | Description | Status |
|------|-------------|--------|
| D1.1 | Create surface-only scene | ⏳ TODO |
| D1.2 | Define surface acceptance criteria | ⏳ TODO |
| D1.3 | Add Block SF experiments | ⏳ TODO |
| D1.4 | Add surface evaluation rubric | ⏳ TODO |
| D1.5 | Compare workflows on surfaces only | ⏳ TODO |

### Epic E — Workflow Candidate Registry

Register and compare candidate workflows.

| Task | Description | Status |
|------|-------------|--------|
| E1.1 | Register v6 as candidate | ⏳ TODO |
| E1.2 | Add hybrid comparison plan (H1-H5) | ⏳ TODO |
