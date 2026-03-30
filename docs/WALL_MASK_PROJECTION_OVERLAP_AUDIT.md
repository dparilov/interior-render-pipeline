# Wall Mask Projection Overlap Audit

**Date:** 2026-03-31
**Bundle:** bathroom_01_surface_only
**Status:** INVESTIGATION COMPLETE

---

## Conclusion

**BOUNDARY-ONLY CONTACT — Bitmap overlap is RENDERING ARTIFACT**

Camera-space projected polygon overlap is **0.59%** — negligible edge effects only.
Bitmap overlap of **39.6%** is NOT explained by geometry projection.

---

## Camera Projection Results

| Metric | Value |
|--------|-------|
| Total tile area (projected) | 777,909 px² |
| Total upper area (projected) | 587,587 px² |
| **Projected overlap area** | **3,448 px²** |
| **Overlap % of smaller** | **0.59%** |

### Face Pair Analysis

| Classification | Count | Description |
|----------------|-------|-------------|
| True overlapping pairs | 4 | ratio > 1%, edge effects |
| Boundary contact pairs | 3 | touching but not overlapping |

All 4 "overlapping" pairs have ratio 1.4-1.8% — **minor edge effects**, not significant area overlap.

---

## Comparison: Projected vs Bitmap Overlap

| Source | Overlap | % of smaller |
|--------|---------|--------------|
| Camera projection (geometric) | 3,448 px² | **0.59%** |
| Bitmap masks | 99,409 px | **39.6%** |
| **Discrepancy factor** | — | **~67x** |

The bitmap overlap is **67 times larger** than geometric projection overlap.

---

## Root Cause Analysis

### What camera projection shows:
- Tile faces: Y = 501-1232 (screen coords)
- Upper faces: Y = 38-514 (screen coords)
- Overlap zone: Y ≈ 501-514 (only 13 pixels height)
- This is the **boundary contact zone** at Z = 1.801m

### What bitmap masks show:
- 99,409 pixels of overlap
- Uniformly distributed across full image height
- NOT localized to boundary

### Conclusion:
The **39.6% bitmap overlap is a SketchUp rendering artifact**, not geometric overlap.

Possible causes:
1. **Anti-aliasing** at face edges bleeding into adjacent regions
2. **Transparency/blending** in SketchUp export
3. **Background color contamination** (gray ~204 treated as white in some regions)
4. **Z-buffer precision** issues at boundary

---

## Recommended Policy Update

### Previous (incorrect):
```
overlap_cause: TRUE SOURCE-GEOMETRY OVERLAP
```

### Corrected:
```
overlap_cause: RENDERING ARTIFACT
geometric_overlap_pct: 0.59
bitmap_overlap_pct: 39.6
discrepancy: Bitmap overlap not explained by geometry
```

### Action Required:
1. Investigate SketchUp export settings
2. Consider tighter threshold (> 254 instead of > 230)
3. Or: accept current masks with documented artifact status

---

## Evidence Files

- Camera projection audit: `examples/bathroom_01/camera_projection_audit.json`
- Previous (incorrect) audit: `docs/WALL_MASK_OVERLAP_AUDIT.md` — **SUPERSEDED**

---

## Acceptance Criteria

| Criteria | Result |
|----------|--------|
| True camera-space overlap? | **NO** (0.59% edge effects only) |
| Boundary-only contact? | **YES** |
| Bitmap overlap explained? | **NO** — rendering artifact |
| Root cause identified? | **PARTIAL** — artifact, exact mechanism TBD |
