# IRP Experiment Plan v4.0

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

---

## Block B: Blender Flow Validation

**Status:** ⏳ TODO

Validates Blender headless fallback path.

### Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| **Generation** | B0, B1, B2 | Blender produces valid raw bundle |
| **Compatibility** | B3, B4 | Enriched bundle works in main pipeline |

### Generation Tests (Raw Bundle)

| ID | Test | Expected | Validates |
|----|------|----------|-----------|
| B0 | Smoke test | Files generated | Blender script runs |
| B1 | Manifest schema | Required fields present | Contract compliance |
| B2 | Size consistency | All images match resolution | Output integrity |

### Compatibility Tests (Enriched Bundle)

| ID | Test | Expected | Validates |
|----|------|----------|-----------|
| B3 | Integration | Render completes | Pipeline compatibility |
| B4 | Parity | Similar to SketchUp | Quality equivalence |

---

### B0 — Generation Smoke Test

**Category:** Generation

```bash
blender --background --python render/blender_masks.py -- \
  --input model.glb --output masks/ \
  --beauty beauty.png --depth depth.png
```

**Pass criteria:**
- [ ] Exit code 0
- [ ] beauty.png exists
- [ ] depth.png exists
- [ ] masks/*.png for each IRP_ entity
- [ ] manifest.json valid JSON

### B1 — Manifest Validation

**Category:** Generation

Check raw manifest contains:
- [ ] `version`, `generator`, `blender_version`
- [ ] `resolution` array
- [ ] `base_image`, `depth_map` paths
- [ ] `depth_type` = "normalized_inverted"
- [ ] `entities[]` array with name, mask, role, critical
- [ ] `requires_enrichment` field present

### B2 — Size Consistency

**Category:** Generation

All outputs must match `--resolution`:
- [ ] beauty.png size
- [ ] depth.png size
- [ ] Each masks/*.png size

### B3 — Integration Test

**Category:** Compatibility

**Precondition:** Raw bundle enriched with references + tech spec.

Steps:
1. Copy raw bundle
2. Add `references/` with images
3. Update manifest (set reference paths, remove requires_enrichment)
4. Run `workflow_builder.py`
5. Submit to ComfyUI

**Pass criteria:**
- [ ] Workflow validation passed
- [ ] Render completes without error
- [ ] Output image generated

### B4 — Parity Check

**Category:** Compatibility

Compare same scene rendered from both sources:

| Aspect | Check |
|--------|-------|
| Entity count | Same entities detected |
| Mask alignment | Masks cover same geometry |
| Depth range | Similar near/far distribution |
| Beauty quality | Visually comparable |

**Note:** Exact pixel match NOT expected due to different renderers.

---

---

# Epic D — Surface-Only Validation

## Goal

Validate rendering strategy specifically for surfaces (floor, walls) without fixture complexity.
Surfaces have different requirements than fixtures and may need different strategies.

## D1.1 — Create Surface-Only Scene

Prepare simplified scene with only:
- floor
- lower wall tile zone
- upper wall zone (paint)
- window
- room shell

**Artifacts:**
- `examples/bathroom_01_surfaces/` bundle
- masks/*.png (floor, walls, window only)
- beauty.png
- depth.png
- manifest.json (surfaces only, no fixtures)

## D1.2 — Surface-Specific Acceptance Criteria

Add to evaluation:

| Criterion | Description |
|-----------|-------------|
| Floor matches blue patterned reference | Rivoli Bergen Azul pattern visible |
| Wall tile matches white vertical ribbed reference | Costa Nova White texture |
| Upper wall matches gray paint requirement | Smooth gray paint, no texture |
| No material drift | No wood / marble / brass appearing |
| Correct boundaries | Clean transitions between zones |

## D1.3 — Block SF: Surface-Focused Tests

**Status:** ⏳ TODO

| ID | Workflow | Description |
|----|----------|-------------|
| SF1 | phase_b_multi_ipadapter_regional | Current Phase B workflow |
| SF2 | render_v6_segmentation_regional | Original v6 with UperNet+SAM |
| SF3 | v6_plus_sketchup_masks | v6 flow + SketchUp masks |
| SF4 | phase_b_strong_prompt | Phase B + strong global prompt/negative |
| SF5 | best_hybrid_surface | Best hybrid from SF1-SF4 |

### SF1 — Phase B Current

Use current multi-IPAdapter regional workflow on surface-only bundle.

### SF2 — Render v6 Segmentation

**Workflow:** render_v6_segmentation_regional

Parameters from v6:
- ControlNet Canny: 0.7, end_at 0.8
- ControlNet Depth: 0.5, end_at 0.6
- 9 Regional IP-Adapter (only surfaces active)
- Steps: 50
- Sampler: dpmpp_2m_sde
- CFG: 7.0

### SF3 — v6 + SketchUp Masks

Hybrid: v6 ControlNet weights + SketchUp bundle masks.

### SF4 — Phase B + Strong Prompt

Current Phase B with:
- Strong global positive prompt (surface-focused)
- Strong negative prompt: "wood grain, marble veins, brass fixtures, gold accents"

### SF5 — Best Hybrid

Take best elements from SF1-SF4, combine.

## D1.4 — Surface Evaluation Rubric

Score 1-5 for each axis:

| Axis | Description |
|------|-------------|
| Floor fidelity | Blue patterned tile matches reference |
| Wall tile fidelity | White ribbed tile matches reference |
| Upper wall fidelity | Gray paint matches requirement |
| Boundary quality | Clean transitions, no bleeding |
| Geometric consistency | Room shape preserved |
| Overall surface realism | Natural, coherent surfaces |

## D1.5 — Surface-Only Comparison

**Important:** Do NOT evaluate bathtub, vanity, accessories.
Goal: Select best workflow specifically for surfaces.

---

# Epic E — Workflow Candidate Registry

## Goal

Register and compare candidate workflows without premature benchmark claims.

## E1.1 — Candidate Workflows

**Status: None declared as benchmark yet.**

| ID | Name | Description | Status |
|----|------|-------------|--------|
| WF1 | phase_b_multi_ipadapter_regional | Current Phase B | ✅ Implemented |
| WF2 | render_v6_segmentation_regional | v6 with UperNet+SAM | ✅ Reference exists |
| WF3 | v6_plus_sketchup_masks | v6 + SketchUp masks | 📋 Planned |
| WF4 | phase_b_strong_prompt | Phase B + strong prompts | 📋 Planned |
| WF5 | hybrid_best | Best elements combined | 📋 Planned |

## E1.2 — Hybrid Comparison Plan

| ID | Test | Baseline | Variables |
|----|------|----------|-----------|
| H1 | v6 original | - | UperNet+SAM masks, v6 ControlNet weights |
| H2 | v6 + SketchUp masks | H1 | Replace masks with SketchUp bundle |
| H3 | Phase B current | - | Current multi-IPAdapter regional |
| H4 | Phase B + strong prompt | H3 | Add global prompt/negative prompt |
| H5 | Best hybrid | H1-H4 results | Combine best elements |

### Comparison Metrics

| Metric | Description |
|--------|-------------|
| Surface fidelity | Match to reference materials |
| Fixture accuracy | Shape and detail preservation |
| Boundary quality | Clean transitions |
| Overall coherence | Unified visual style |
| Runtime | Seconds per render |

---

## TODOs

### Refiner Prompt Sync
Current `workflow_refiner.json` has hardcoded prompts.
For production: sync refiner positive/negative with base prompts at runtime.
