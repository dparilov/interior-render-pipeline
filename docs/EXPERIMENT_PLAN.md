# IRP Experiment Plan v2.0

## Compute Platform

| Platform | Type | Hardware | Cost |
|----------|------|----------|------|
| RunPod Pod | Dedicated | RTX 4090 24GB | ~$0.69/hr |

**All experiments run on dedicated RunPod Pod.**

### Pod Setup

Pod ID: `m88nqdtocfd818`
SSH: `ssh root@<ip> -p <port> -i ~/.ssh/id_rsa`

**Installed:**
- ComfyUI 0.18.1
- SDXL Base 1.0
- IPAdapter Plus SDXL + CLIP ViT-H
- ControlNet Canny/Depth (control-lora-rank256)

**Expected per experiment:**
- Time: ~30-35 sec (RTX 4090)
- Cost: ~$0.006

---

## Block 0: Infra Smoke ✅

| ID | Name | Status |
|----|------|--------|
| S0 | pod-smoke | ✅ PASSED |

---

## Block 1: Structural Gate ✅

| ID | Name | Depth | Boundary | IPAdapter | Status |
|----|------|-------|----------|-----------|--------|
| S1 | baseline | SKP 0.9 | ON | ALL (10) | ✅ PASSED |
| S1-neural | neural-depth | Neural 0.7 | ON | ALL | ✅ PASSED |
| S1-no-boundary | no-boundary | SKP 0.9 | OFF | ALL | ✅ PASSED |
| S1-weak | weak-structure | 0.5 | ON | ALL | ✅ PASSED |

---

## Block 2: Single-Entity Calibration

Isolate weight sensitivity per entity class.

### I2: Floor (Surface)

| ID | Entity | Weight | Status |
|----|--------|--------|--------|
| I2-03 | floor | 0.3 | ✅ PASSED |
| I2-04 | floor | 0.4 | ✅ PASSED |
| I2-05 | floor | 0.5 | ✅ PASSED |
| I2-06 | floor | 0.6 | ✅ PASSED |
| I2-07 | floor | 0.7 | ✅ PASSED |

### I4: Vanity (Fixture)

| ID | Entity | Weight | Status |
|----|--------|--------|--------|
| I4-03 | vanity | 0.3 | ✅ PASSED |
| I4-04 | vanity | 0.4 | ✅ PASSED |
| I4-05 | vanity | 0.5 | ✅ PASSED |
| I4-06 | vanity | 0.6 | ✅ PASSED |
| I4-07 | vanity | 0.7 | ✅ PASSED |

**Output:** Best weight for surface, best weight for fixture.

---

## Block 3: Refiner Tests

Test refiner impact before full integration.

**⚠️ REFINER ISSUE:** SDXL Refiner requires separate CLIP encode — direct positive/negative passthrough fails with shape mismatch. Refiner tests (R*b) deferred until workflow is fixed.

### Completed (baseline without refiner)

| ID | Setup | Refiner | Status |
|----|-------|---------|--------|
| R1a | Structural (S1) | OFF | ✅ PASSED |
| R2a | Floor (weight=0.5) | OFF | ✅ PASSED |
| R3a | Vanity (weight=0.5) | OFF | ✅ PASSED |
| R4a | Critical only | OFF | ✅ PASSED |

### Deferred (refiner integration needed)

| ID | Setup | Refiner | Status |
|----|-------|---------|--------|
| R1b | Structural (S1) | ON | ⏸️ Deferred |
| R2b | Floor (weight=0.5) | ON | ⏸️ Deferred |
| R3b | Vanity (weight=0.5) | ON | ⏸️ Deferred |
| R4b | Critical only | ON | ⏸️ Deferred |

**TODO:** Build proper refiner workflow with separate CLIPTextEncode for refiner model.

---

## Block 4: First Integration

Run after Block 2-3 to understand best settings.

| ID | Name | Entities | Refiner | IPAdapter Order |
|----|------|----------|---------|-----------------|
| F1 | critical-only | Critical only | OFF | Default |
| F1-refiner | critical-refiner | Critical only | ON | Default |
| F2 | all-entities | All (10) | OFF | Default |
| F2-refiner | all-refiner | All (10) | ON | Default |
| F2-order2 | reversed-order | All (10) | OFF | Reversed |

**Critical entities:** walls, floor, bathtub, vanity

---

## Block 5: Technical Spec Impact

Run on best integration setup from Block 4.

| ID | Name | Refs | Prompts | Purpose |
|----|------|------|---------|---------|
| T1 | full-tz | ✅ | ТЗ-derived | Full spec compliance |
| T2 | refs-only | ✅ | Simplified | Isolate ref impact |
| T3 | strong-tz | ✅ | Strong ТЗ | Max spec emphasis |

---

## Block 6: Production Candidate

Final candidates for production recipe.

| ID | Name | Config | Seed | Purpose |
|----|------|--------|------|---------|
| P1 | best-critical | Best structural + best weights + critical | 42 | Minimal viable |
| P2 | best-full | Best full integration | 42 | Full scene |
| P2-refiner | best-full-refiner | Best full + refiner | 42 | With refinement |
| P3 | seed-test-1 | Best variant | 123 | Seed stability |
| P4 | seed-test-2 | Best variant | 456 | Seed stability |

---

## Execution Summary

| Block | Experiments | Status |
|-------|-------------|--------|
| 0 - Infra | 1 | ✅ Complete |
| 1 - Structural | 4 | ✅ Complete |
| 2 - Calibration | 10 | ✅ Complete |
| 3 - Refiner | 8 | 🔄 Partial (4/8, refiner deferred) |
| 4 - Integration | 5 | ⏳ TODO |
| 5 - Tech Spec | 3 | ⏳ TODO |
| 6 - Production | 5 | ⏳ TODO |

**Total:** 36 experiments

---

## Decision Points

After each block, decide:

1. **After Block 2:** Best surface weight, best fixture weight
2. **After Block 3:** Refiner ON or OFF for integration
3. **After Block 4:** Best integration config (F1/F2/F2-order2)
4. **After Block 5:** Best ТЗ handling
5. **After Block 6:** Production recipe locked

---

## Failure Criteria

**Automatic FAIL:**
- Objects in wrong position (geometry failure)
- Objects outside room boundary (boundary failure)
- Critical entity completely wrong material/color

**Manual review:**
- Minor color variations
- Texture detail differences
- Edge artifacts
