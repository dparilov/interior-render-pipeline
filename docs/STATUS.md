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
