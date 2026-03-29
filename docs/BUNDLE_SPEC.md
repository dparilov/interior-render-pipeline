
---

## Runtime Entity Application Contract

For each active entity, the pipeline MUST:

1. **Load** `entity.reference` as IPAdapter input image
2. **Load** `entity.mask` as regional mask
3. **Apply** entity-specific IPAdapter branch with:
   - `entity.ipadapter_weight`
   - `entity.render_mode`
4. **Chain** entity branches in defined `entity_order`
5. **Log** application details in experiment.json:
   - `entities_requested`
   - `entities_applied`
   - `entity_order`
   - `regional_ipadapter_count`

### Required Fields for Multi-IPAdapter Mode

Each active entity MUST have:
- `mask` — path to regional mask PNG
- `reference` — path to reference image PNG
- `ipadapter_weight` — float 0.0-1.0
- `render_mode` — one of: structural, regional_texture, regional_object

### Validation Requirements

Before render:
- All active entities have mask file present
- All active entities have reference file present
- All weights are in valid range
- render_mode is compatible with workflow
