# Experiments Index — Full Campaign

## Summary
- **Total experiments:** 62
- **Phase A (single IPAdapter):** 36
- **Phase B (multi-IPAdapter regional):** 26
- **Leader:** T2-v2

---

## Block 0 — Infrastructure Smoke
| ID | Description | Status |
|----|-------------|--------|
| S0 | Canny only, no IPAdapter | ✅ PASSED |

## Block 1 — Structural Gate
| ID | Description | Status |
|----|-------------|--------|
| S1 | Baseline (Canny 0.8, Depth 0.9) | ✅ PASSED |
| S1-neural | Neural depth | ✅ PASSED |
| S1-no-boundary | No boundary mask | ✅ PASSED |
| S1-weak | Weak controls (0.5) | ✅ PASSED |

## Block 2 — Single-Entity Calibration
| ID | Entity | Weight | Status |
|----|--------|--------|--------|
| I2-03 | floor | 0.3 | ✅ |
| I2-04 | floor | 0.4 | ✅ |
| I2-05 | floor | 0.5 | ✅ |
| I2-06 | floor | 0.6 | ✅ |
| I2-07 | floor | 0.7 | ✅ |
| I4-03 | vanity | 0.3 | ✅ |
| I4-04 | vanity | 0.4 | ✅ |
| I4-05 | vanity | 0.5 | ✅ |
| I4-06 | vanity | 0.6 | ✅ |
| I4-07 | vanity | 0.7 | ✅ |

## Block 3 — Refiner Tests (Phase A)
| ID | Config | Status |
|----|--------|--------|
| R1a | Structural, no refiner | ✅ |
| R1b | Structural + refiner | ✅ |
| R2a | Floor only, no refiner | ✅ |
| R2b | Floor only + refiner | ✅ |
| R3a | Vanity only, no refiner | ✅ |
| R3b | Vanity only + refiner | ✅ |
| R4a | Critical entities, no refiner | ✅ |
| R4b | Critical entities + refiner | ✅ |

## Block 3.5 — Multi-IPAdapter Validation (Phase B)
| ID | Description | Status |
|----|-------------|--------|
| M1 | Single entity branch | ✅ |
| M2 | Four critical entities | ✅ |
| M3 | Entity order: large→small | ✅ |
| M4 | Entity order: small→large | ✅ |
| M5 | Missing reference handling | ✅ |
| M6 | Weight distribution | ✅ |

## Block 4 — Integration (Phase A)
| ID | Description | Status |
|----|-------------|--------|
| F1 | Full scene, default order | ✅ |
| F2 | Full scene, optimized order | ✅ |
| F2-order2 | Alternative order | ✅ |
| F1-refiner | F1 + refiner | ✅ |
| F2-refiner | F2 + refiner | ✅ |

## Block 4 — Integration (Phase B: Multi-IPAdapter)
| ID | Description | Status |
|----|-------------|--------|
| F1-v2 | Multi-IPAdapter, default | ✅ |
| F2-v2 | Multi-IPAdapter, optimized | ✅ |
| F2-order2-v2 | Multi-IPAdapter, alt order | ✅ |
| F1-refiner-v2 | Multi-IPAdapter + refiner | ✅ |
| F2-refiner-v2 | Multi-IPAdapter + refiner | ✅ |

## Block 5 — Tech Spec (Phase A)
| ID | Description | Status |
|----|-------------|--------|
| T1 | ТЗ-driven prompts | ✅ |
| T2 | ТЗ + references | ✅ |
| T3 | Full tech spec | ✅ |

## Block 5 — Tech Spec (Phase B: Multi-IPAdapter)
| ID | Description | Status |
|----|-------------|--------|
| T1-v2 | Multi-IPAdapter, ТЗ prompts | ✅ |
| **T2-v2** | **Multi-IPAdapter, ТЗ + refs** | **✅ LEADER** |
| T3-v2 | Multi-IPAdapter, full spec | ✅ |

## Block 6 — Production (Phase A)
| ID | Description | Status |
|----|-------------|--------|
| P1 | Production settings | ✅ |
| P2 | Production optimized | ✅ |
| P2-refiner | P2 + refiner | ✅ |
| P3 | Production + quality boost | ✅ |
| P4 | Production + max quality | ✅ |

## Block 6 — Production (Phase B: Multi-IPAdapter)
| ID | Description | Status |
|----|-------------|--------|
| P1-v2 | Multi-IPAdapter production | ✅ |
| P2-v2 | Multi-IPAdapter optimized | ✅ |
| P2-refiner-v2 | Multi-IPAdapter + refiner | ✅ |
| P3-v2 | Multi-IPAdapter + quality | ✅ |
| P4-v2 | Multi-IPAdapter + max | ✅ |

---

## Key Findings

### Leader: T2-v2
- Best balance of ТЗ compliance and visual quality
- Multi-IPAdapter regional with 9 entities
- ТЗ-driven prompts + reference images

### Refiner Impact
- Adds ~10 seconds runtime
- Improves texture detail
- Risk of structure drift on weak guidance

### Phase A vs Phase B
- Phase B (multi-IPAdapter) shows better entity isolation
- Phase A useful as baseline comparison
- Both phases complete and documented

---

## File Structure

Each experiment folder contains:
- `IRP_render_*.png` — output image
- `experiment.json` — metadata
- `workflow_*.json` — workflow snapshot (key experiments only)
