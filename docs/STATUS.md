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
| **Multi-IPAdapter Regional Workflow** | ⏳ **PENDING** |

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

### Phase B — Multi-IPAdapter Validation (PENDING)

Required before production:
1. Implement workflow_builder.py
2. Add workflow validator
3. Run M1-M6 validation tests
4. Re-run F*-v2, T*-v2, P*-v2

## Provisional Results Warning

⚠️ Integration results (F1, F2, T1-T3, P1-P4) are provisional under simplified workflow.
Full validation requires Phase B completion.
