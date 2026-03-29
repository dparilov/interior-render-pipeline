# IRP Experiment Plan v3.0

## Experiment Phases

### Phase A — Simplified Workflow Benchmark ✅ COMPLETE

Results from simplified single-IPAdapter workflow.
Valid for: base pipeline, single-entity calibration, refiner capability.
**NOT valid for:** true multi-entity regional composition.

### Phase B — Multi-IPAdapter Validation ⏳ PENDING

True multi-entity regional IPAdapter pipeline validation.
Required: workflow_builder.py, validators, M1-M6 tests.

---

## Compute Platform

| Platform | Type | Hardware | Cost |
|----------|------|----------|------|
| RunPod Pod | Dedicated | RTX 4090 24GB | ~$0.69/hr |

**Pod ID:** `m88nqdtocfd818`

---

## Summary

| Block | Experiments | Phase A | Phase B |
|-------|-------------|---------|---------|
| 0 - Infra | 1 | ✅ | - |
| 1 - Structural | 4 | ✅ | - |
| 2 - Calibration | 10 | ✅ | - |
| 3 - Refiner | 8 | ✅ | - |
| 3.5 - Multi-IPAdapter | 6 | - | ✅ |
| 4 - Integration | 5 | ✅ (provisional) | ✅ -v2 |
| 5 - Tech Spec | 3 | ✅ (provisional) | ✅ -v2 |
| 6 - Production | 5 | ✅ (provisional) | ✅ -v2 |

---

# Phase A Results (Simplified Workflow)

## Block 0: Infrastructure ✅

| ID | Purpose | Status |
|----|---------|--------|
| S0 | Environment validation | ✅ PASSED |

## Block 1: Structural Variants ✅

| ID | Config | Status |
|----|--------|--------|
| S1 | Full structural | ✅ PASSED |
| S1-neural | Neural canny | ✅ PASSED |
| S1-no-boundary | No boundary mask | ✅ PASSED |
| S1-weak | Weak ControlNet | ✅ PASSED |

## Block 2: Single-Entity Calibration ✅

### I2 — Floor Entity

| ID | Weight | Status |
|----|--------|--------|
| I2-03 | 0.3 | ✅ PASSED |
| I2-04 | 0.4 | ✅ PASSED |
| I2-05 | 0.5 | ✅ PASSED |
| I2-06 | 0.6 | ✅ PASSED |
| I2-07 | 0.7 | ✅ PASSED |

### I4 — Vanity Entity

| ID | Weight | Status |
|----|--------|--------|
| I4-03 | 0.3 | ✅ PASSED |
| I4-04 | 0.4 | ✅ PASSED |
| I4-05 | 0.5 | ✅ PASSED |
| I4-06 | 0.6 | ✅ PASSED |
| I4-07 | 0.7 | ✅ PASSED |

## Block 3: Refiner Tests ✅

| ID | Setup | Refiner | Status |
|----|-------|---------|--------|
| R1a | Structural | OFF | ✅ PASSED |
| R1b | Structural | ON | ✅ PASSED |
| R2a | Floor | OFF | ✅ PASSED |
| R2b | Floor | ON | ✅ PASSED |
| R3a | Vanity | OFF | ✅ PASSED |
| R3b | Vanity | ON | ✅ PASSED |
| R4a | Critical | OFF | ✅ PASSED |
| R4b | Critical | ON | ✅ PASSED |

## Block 4: Integration ✅ (PROVISIONAL)

⚠️ **Provisional:** Run on simplified workflow, not true multi-entity.

| ID | Config | Status | Phase B |
|----|--------|--------|---------|
| F1 | Critical only | ✅ | → F1-v2 |
| F1-refiner | Critical + refiner | ✅ | → F1-refiner-v2 |
| F2 | All entities | ✅ | → F2-v2 |
| F2-refiner | All + refiner | ✅ | → F2-refiner-v2 |
| F2-order2 | Reversed order | ✅ | → F2-order2-v2 |

## Block 5: Tech Spec ✅ (PROVISIONAL)

⚠️ **Provisional:** Run on simplified workflow.

| ID | Prompts | Status | Phase B |
|----|---------|--------|---------|
| T1 | Full ТЗ | ✅ | → T1-v2 |
| T2 | Refs only | ✅ | → T2-v2 |
| T3 | Strong ТЗ | ✅ | → T3-v2 |

## Block 6: Production ✅ (PROVISIONAL)

⚠️ **Provisional:** Run on simplified workflow.

| ID | Config | Status | Phase B |
|----|--------|--------|---------|
| P1 | Critical | ✅ | → P1-v2 |
| P2 | Full | ✅ | → P2-v2 |
| P2-refiner | Full + refiner | ✅ | → P2-refiner-v2 |
| P3 | Seed 165 | ✅ | → P3-v2 |
| P4 | Seed 498 | ✅ | → P4-v2 |

---

# Phase B Plan (Multi-IPAdapter)

## Block 3.5: Multi-IPAdapter Validation

**Purpose:** Validate workflow_builder.py generates correct multi-entity regional branches.

| ID | Test | Expected |
|----|------|----------|
| M1 | Single entity mode | 1 regional branch |
| M2 | Critical only (4) | 4 regional branches |
| M3 | All entities | N branches (all active) |
| M4 | Reverse order | Same as M3, reversed |
| M5 | Missing entity guard | Validator fails |
| M6 | Workflow validation report | Correct metadata |

### M1 — One Entity Branch

- Mode: `single`
- Verify: workflow contains exactly 1 `entity_*_apply` node
- Verify: node has mask binding
- Verify: node has reference binding

### M2 — Four Critical Entities

- Mode: `critical`
- Entities: walls, floor, bathtub, vanity
- Verify: 4 `entity_*_apply` nodes
- Verify: each has correct mask/ref

### M3 — All Entities

- Mode: `all`
- Verify: N branches for N active entities
- Verify: order follows DEFAULT_ORDER

### M4 — Reverse Order

- Mode: `all`, Order: `reverse`
- Verify: order is reversed vs M3

### M5 — Missing Entity Guard

- Remove mask from one entity
- Verify: manifest validator fails
- Verify: entity marked as skipped

### M6 — Workflow Validation Report

- Run full build
- Verify: metadata contains correct:
  - `entities_requested`
  - `entities_applied`
  - `entity_order`
  - `regional_ipadapter_count`
  - `workflow_validation_passed`

---

## Block 4-v2: Integration (Multi-IPAdapter)

Re-run after M1-M6 pass.

| ID | Config | Entities | Order |
|----|--------|----------|-------|
| F1-v2 | Critical | 4 | default |
| F1-refiner-v2 | Critical + refiner | 4 | default |
| F2-v2 | All | all | default |
| F2-refiner-v2 | All + refiner | all | default |
| F2-order2-v2 | All | all | reverse |

## Block 5-v2: Tech Spec (Multi-IPAdapter)

| ID | Prompts | Entities |
|----|---------|----------|
| T1-v2 | Full ТЗ | all |
| T2-v2 | Refs only | all |
| T3-v2 | Strong ТЗ | all |

## Block 6-v2: Production (Multi-IPAdapter)

| ID | Config | Seed |
|----|--------|------|
| P1-v2 | Critical | 42 |
| P2-v2 | Full | 42 |
| P2-refiner-v2 | Full + refiner | 42 |
| P3-v2 | Stability | 123 |
| P4-v2 | Stability | 456 |

---

## Execution Order

### Phase B Sequence

1. M1 → validate single entity branch
2. M2 → validate critical entities
3. M3 → validate all entities
4. M4 → validate reverse order
5. M5 → validate error handling
6. M6 → validate logging
7. F1-v2 → F2-order2-v2
8. T1-v2 → T3-v2
9. P1-v2 → P4-v2

---

## Audit Checklist (Post Phase B)

- [ ] All active entities → separate runtime branches?
- [ ] Branch count matches `regional_ipadapter_count`?
- [ ] Entity order matches `entity_order` in logs?
- [ ] F2-order2-v2 actually reverses branch order?
- [ ] T* tests validate ТЗ on multi-entity composition?
- [ ] P2-refiner-v2 applies refiner over multi-IPAdapter?
- [ ] No spec/docs/runtime/logs discrepancies?

---

## TODOs

### Refiner Prompt Sync
Current `workflow_refiner.json` has hardcoded prompts.
For production: sync refiner positive/negative with base prompts at runtime.
