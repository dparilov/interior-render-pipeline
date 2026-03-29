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
| S1 | baseline-structural | SKP 0.9 | ON | OFF | Golden structural reference |
| S1-neural | neural-depth | Neural 0.7 | ON | OFF | Compare depth sources |
| S1-no-boundary | no-boundary | SKP 0.9 | OFF | OFF | Verify boundary effect |
| S1-weak | weak-structure | SKP 0.5, Canny 0.5 | ON | OFF | Minimum viable structure |

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

## Block 5: Production Candidate

After all blocks pass:

| ID | Name | Config | Purpose |
|----|------|--------|---------|
| P1 | production-v1 | Best params from S/I/F/T | Final candidate |
| P1-seed2 | production-seed-test | Same as P1, seed=123 | Verify seed independence |
| P1-hires | production-hires | Same as P1, 2560x1440 | Resolution test |

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

1. **S1** — must pass before anything else
2. **S1-neural, S1-no-boundary** — validate H1, H2
3. **I2, I4 sweeps** — find optimal weights
4. **F1** — critical integration gate
5. **T1, T2** — validate ТЗ impact
6. **F2, F2-order2** — full scene + H5
7. **P1** — production candidate

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
