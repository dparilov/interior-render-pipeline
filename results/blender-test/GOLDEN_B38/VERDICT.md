# GOLDEN_B38 — Verdict

**Status: ✅ APPROVED**

## Configuration

- **Bundle**: bathroom_05
- **Resolution**: 1066 x 1239 (portrait, exact viewport)
- **Aspect**: 0.86
- **FOV**: 35° / 0.86 = **40.7°**
- **Camera Y**: -4.599m (with wall offset)
- **Clip start**: 5.899m

## Formula

```python
fov_adjusted = fov_sketchup / aspect
```

## What's Visible

- ✅ Floor with quatrefoil tile pattern
- ✅ Mirror (black/reflective)
- ✅ Vanity with sink
- ✅ Basket (full)
- ✅ Window (left)
- ✅ Shower area (right)
- ✅ Bathtub edge (right)
- ✅ Ceiling

## Files

- `render.png` — Golden baseline render
- `experiment.json` — Experiment parameters

## Reproduction

```bash
blender --background --python scripts/render_golden.py -- \
    --bundle examples/bathroom_05 \
    --output results/blender-test/GOLDEN_B38/render.png \
    --samples 64
```
