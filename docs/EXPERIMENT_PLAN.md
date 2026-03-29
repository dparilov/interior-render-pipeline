# IRP Experiment Plan v1.1

## Overview

Controlled experiment series to validate pipeline components and find optimal parameters.
All experiments use **fixed seed=42** for reproducibility.

**Baseline configuration** (from workflow.json v1.1):
- Canny: strength=0.8, end=0.9
- Depth: strength=0.9, end=0.8 (SketchUp ground truth)
- IPAdapter: surface=0.55, fixture=0.50, opening=0.0
- Boundary mask: ON (SetLatentNoiseMask)

---

## Compute Platform

| Platform | Hardware | PyTorch | Cost |
|----------|----------|---------|------|
| RUNPOD | RTX 4090/3090/L4 24GB, serverless | torch 2.x CUDA | ~$0.0004/sec |

**All experiments run on RunPod GPU.** Local CPU too slow (OOM at 10 IPAdapter).

Expected time per experiment: ~60-90 sec (vs ~2h CPU).
Expected cost per experiment: ~$0.03-0.04.

---

## Hypotheses

| ID | Hypothesis | Test | Success Criteria |
|----|------------|------|------------------|
| H1 | SketchUp Depth > Neural Depth | S1 vs S1-neural | Objects in correct positions |
| H2 | Boundary Mask prevents hallucination | S1 vs S1-no-boundary | No objects outside room |
| H3 | Surfaces need higher weight than fixtures | I2 vs I4 sweeps | Optimal weight differs by class |
| H4 | Canny 0.8 + Depth 0.9 is optimal | Baseline vs sweep | Best structure preservation |
| H5 | IPAdapter order affects result | F2 vs F2-order2 | Visible difference in output |
| H6 | ТЗ-derived prompts improve accuracy | T1 vs T2 | Better material/color match |

---

## Block 1: Structural Gate (REQUIRED FIRST)

These must pass before any material experiments.

| ID | Name | Depth | Boundary | IPAdapter | Purpose |
|----|------|-------|----------|-----------|---------|
| S1 | baseline | SKP 0.9 | ON | ALL (10) | Golden structural reference |
| S1-neural | neural-depth | Neural 0.7 | ON | ALL | Compare depth sources |
| S1-no-boundary | no-boundary | SKP 0.9 | OFF | ALL | Verify boundary effect |
| S1-weak | weak-structure | SKP 0.5, Canny 0.5 | ON | ALL | Minimum viable structure |

**Pass criteria:**
- S1: All objects in correct positions, room boundaries respected
- S1-neural vs S1: SKP depth should have fewer position errors
- S1-no-boundary vs S1: Should show hallucinated objects outside room
- S1-weak: Should show structural drift

---

## Block 2: Single-Entity Calibration

Isolate weight sensitivity per entity class.

### I2: Floor (Surface)

| ID | Entity | Weight | All others |
|----|--------|--------|------------|
| I2-03 | floor | 0.3 | OFF |
| I2-04 | floor | 0.4 | OFF |
| I2-05 | floor | 0.5 | OFF |
| I2-06 | floor | 0.6 | OFF |
| I2-07 | floor | 0.7 | OFF |

### I4: Vanity (Fixture)

| ID | Entity | Weight | All others |
|----|--------|--------|------------|
| I4-03 | vanity | 0.3 | OFF |
| I4-04 | vanity | 0.4 | OFF |
| I4-05 | vanity | 0.5 | OFF |
| I4-06 | vanity | 0.6 | OFF |
| I4-07 | vanity | 0.7 | OFF |

**Output:** Optimal weight per class for integration tests.

---

## Block 3: First Integration

| ID | Name | Entities | Order | Purpose |
|----|------|----------|-------|---------|
| F1 | critical-only | walls, floor, vanity, towel_warmer, mirror | Standard | First integration gate |
| F2 | all-entities | All 10 | Standard (surface→fixture→opening) | Full scene |
| F2-order2 | reversed-order | All 10 | Reversed (opening→fixture→surface) | Test H5 |

**F1 is the primary integration gate** — run before F2.

---

## Block 4: ТЗ Impact

Test whether ТЗ-derived prompts improve render accuracy.

| ID | Name | Prompts | References | Purpose |
|----|------|---------|------------|---------|
| T1 | full-tz | From ТЗ (detailed) | All refs | Baseline with full ТЗ |
| T2 | minimal-prompts | Simplified (e.g., "white tiles") | All refs | Refs-only comparison |
| T3 | no-refs-critical | From ТЗ (detailed) | Critical only | ТЗ without all refs |

**Expected result:** T1 should match ТЗ requirements better than T2.

**Verification method:**
- Compare towel_warmer color (ТЗ says WHITE)
- Compare floor pattern (ТЗ says blue geometric)
- Count material mismatches vs ТЗ checklist

---

## Block 5: Production Candidates

After all blocks pass:

| ID | Name | Config | Entities | Seed | Purpose |
|----|------|--------|----------|------|---------|
| P1 | prod-critical | Best structural + weights | Critical only | 42 | Minimal production |
| P2 | prod-all | Same as P1 | All entities | 42 | Full production |
| P3 | prod-all-seed2 | Same as P2 | All entities | 123 | Seed independence |

**P1 config derived from:**
- Structural: S1 baseline (SKP depth 0.9, boundary ON)
- Weights: Best from I2/I4 sweeps
- Prompts: Full ТЗ (if T1 > T2)

---

## Experiment Output Requirements

Each experiment must produce:

```
experiments/<id>_<timestamp>/
├── experiment.json      # Full params from workflow (not hardcoded)
├── workflow.json        # Actual submitted workflow
├── bundle_manifest.json # Copy of manifest used
├── render.png           # Output image
└── notes.md             # Optional observations
```

**experiment.json must include:**
- All ControlNet strengths extracted from workflow
- All IPAdapter weights and entities_used
- depth_map: "skp" or "neural"
- boundary_mask: true/false
- technical_spec_hash
- references_hash (per entity)
- timing (submit → complete)

---

## Execution Order

### Minimal Start Queue (8 experiments)

```
S1 → S1-neural → S1-no-boundary → I2-05 → I4-05 → F1 → T1 → T2
```

This validates: structure holds, depth/boundary work, class weights, integration, ТЗ impact.

### Full Order

1. **S1** — must pass before anything else
2. **S1-neural, S1-no-boundary** — validate H1, H2
3. **I2-05, I4-05** — baseline weights (skip sweep if time-constrained)
4. **F1** — critical integration gate
5. **T1, T2** — validate ТЗ impact
6. **F2** — full scene (only if F1 passes)
7. **P1, P2, P3** — production candidates

---

## Block 6: Refiner Experiments

Test SDXL Refiner impact on texture quality. Run after best config from Blocks 1-5.

| ID | Name | Base Steps | Refiner Steps | Denoise | Purpose |
|----|------|-----------|---------------|---------|---------|
| R1 | refiner-subtle | 40/50 | 10/50 | 0.2 | Subtle detail enhancement |
| R2 | refiner-medium | 35/50 | 15/50 | 0.25 | Balanced refinement |
| R3 | refiner-strong | 30/50 | 20/50 | 0.3 | Maximum detail (risk: structure drift) |

**Refiner parameters:**
- Model: SDXL Refiner 1.0 (or RealVisXL refiner if available)
- Switch: At denoise % of total steps
- IPAdapter: Applied to base only (not refiner)

**Hypothesis H7:** Refiner улучшает текстуры (плитка, ткань, хром) без потери структурной точности

**Sequential enabling:**
1. R1 first — if structure holds, proceed
2. R2 — compare texture improvement vs R1
3. R3 — test limit before structure degrades

**Pass criteria:**
- Structure matches S1 baseline
- Texture detail improved (subjective + LPIPS)
- No new artifacts introduced

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
