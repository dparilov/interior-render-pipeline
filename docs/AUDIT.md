# IRP Audit Guidelines

## Phase B Audit Requirements

For any Phase B (-v2) experiment, the audit MUST verify:

### Required Fields in experiment.json

| Field | Description | Example |
|-------|-------------|---------|
| `workflow_mode` | Must be `multi_ipadapter_regional` | `"multi_ipadapter_regional"` |
| `workflow_snapshot` | Path to executed workflow JSON | `"workflow_f2_v2.json"` |
| `workflow_hash` | SHA256 hash of workflow | `"sha256:a1b2c3d4..."` |
| `entities_requested` | All entities from manifest | `["walls", "floor", ...]` |
| `entities_applied` | Entities with generated branches | `["walls", "floor", ...]` |
| `entities_skipped` | Entities missing mask/ref | `[]` |
| `entity_order` | Actual application order | `["walls", "floor", ...]` |
| `entity_weights` | Per-entity IPAdapter weights | `{"walls": 0.55, ...}` |
| `regional_ipadapter_count` | Number of IPAdapter branches | `9` |
| `workflow_validation_passed` | Pre-render validation result | `true` |
| `workflow_validation_summary` | Detailed validation breakdown | `{...}` |

### Workflow Snapshot Verification

1. `regional_ipadapter_count` MUST match branch count in snapshot
2. Each entity in `entities_applied` MUST have corresponding nodes:
   - `entity_N_<name>_ref` (LoadImage)
   - `entity_N_<name>_mask` (LoadImageMask)
   - `entity_N_<name>_apply` (IPAdapterAdvanced)
3. Entity order in workflow MUST match `entity_order` field

### Cross-Experiment Checks

| Test | Verification |
|------|--------------|
| F2-v2 vs F2-order2-v2 | `entity_order` must be reversed |
| F1-v2 vs F2-v2 | `regional_ipadapter_count`: 4 vs 9 |
| P2-v2 vs P2-refiner-v2 | Refiner nodes present in snapshot |

### Audit Checklist

- [ ] All -v2 experiments have workflow_snapshot
- [ ] workflow_hash matches actual snapshot
- [ ] entities_applied matches branch count
- [ ] entity_order matches workflow node sequence
- [ ] No entities_skipped for production tests
- [ ] Refiner tests have both multi-IPAdapter AND refiner nodes

## Phase A (Historical)

Phase A results are NOT subject to multi-IPAdapter audit.
They serve as baseline comparison only.

---

## Blender Flow Audit

For bundles generated via Blender headless renderer:

### Required Checks

| Check | Description |
|-------|-------------|
| Size match | beauty, depth, all masks same resolution |
| Depth range | Values span 0-65535 (16-bit) |
| Mask binary | Only black (0) and white (255) pixels |
| Entity coverage | Each manifest entity has mask file |
| Manifest valid | JSON parses, required fields present |

### Parity Checks (vs SketchUp)

| Check | Description |
|-------|-------------|
| Entity names | Match expected IRP_ naming |
| Mask alignment | Masks align with beauty geometry |
| Depth consistency | Near/far correct (white=near, black=far) |

### Contract Gaps

Blender bundles must be manually enriched with:
- [ ] `references/` directory
- [ ] `technical_spec.md`
- [ ] `ipadapter_weight` per entity
- [ ] `role` and `critical` flags
- [ ] `render_mode` per entity
