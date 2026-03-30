# V6 Pod Repro Check

## Status: BLOCKED (Environment Issues)

**Date:** 2026-03-30

## Blockers

1. **RunPod RTX 4090** — supply constraint (no GPUs available)
2. **RunPod RTX 3090** — supply constraint
3. **RunPod A40** — SSH not accessible (container issue)
4. **Local CPU ComfyUI** — cv2 dependency conflict with custom_nodes

### Local ComfyUI Details

ComfyUI starts, but `comfyui_controlnet_aux` and `ComfyUI-Impact-Pack` fail to import:
- cv2 is installed in venv (opencv-python 4.13.0)
- When imported directly via Python, controlnet_aux loads successfully
- ComfyUI's custom_node loader reports "No module named 'cv2'" despite cv2 being available
- Suspected cause: ComfyUI subprocess or path isolation issue

### Workaround Attempted

- Installed opencv-python, opencv-python-headless (conflict)
- Cleared __pycache__, .pyc files
- Renamed controlnet_aux folder
- Deleted ComfyUI database caches

None resolved the import failure.

## Original V6 Workflow Reference

**Source file:** `~/.openclaw/workspace/logs/comfyui/v6_1774613056.json`

**CPU Output:** `~/ComfyUI/output/bathroom_v6_00001_.png`

### V6 Parameters

| Parameter | Value |
|-----------|-------|
| Checkpoint | RealVisXL_V4.0.safetensors |
| IP-Adapter | ip-adapter-plus_sdxl_vit-h.safetensors |
| CLIP Vision | CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors |
| Canny Strength | 0.7, end_at 0.8 |
| Depth Strength | 0.5, end_at 0.6 |
| Steps | 50 |
| Sampler | dpmpp_2m_sde |
| Scheduler | karras |
| CFG | 7.5 |
| Seed | 42 |
| Resolution | 1024x1024 |

### Regional IP-Adapters (9 entities)

| Entity | Weight | End At |
|--------|--------|--------|
| floor | 0.5 | 0.6 |
| wall | 0.5 | 0.6 |
| vanity | 0.6 | 0.6 |
| mirror | 0.5 | 0.6 |
| bathtub | 0.5 | 0.6 |
| bathtub_screen | 0.5 | 0.6 |
| basket | 0.5 | 0.6 |
| towel_warmer | 0.5 | 0.6 |
| faucet | 0.4 | 0.6 |

## Planned Test

When environment is available:

1. Load v6 workflow on RunPod GPU
2. Use same seed (42), same models, same prompts
3. Run 1-2 renders
4. Compare with CPU version:
   - Visual comparison
   - Semantic feature check
   - SSIM/LPIPS metrics (secondary)
5. Verdict: near-identical | minor drift | semantic drift too large

## Files Available

**Inputs:**
- [x] front.jpg (source sketch)
- [x] v6_depth_00001_.png (depth map)
- [x] refs/*.jpg (9 reference images)
- [x] masks_final/*.png (9 masks)

**Output:**
- [x] bathroom_v6_00001_.png (CPU render, ~34 min)

## Next Steps

1. **Option A:** Wait for RunPod GPU availability (check later)
2. **Option B:** Debug ComfyUI cv2 issue (subprocess env isolation)
3. **Option C:** Use existing v6 CPU render for baseline comparison

### Immediate Alternative

Compare **existing outputs** instead of re-running:
- V6 CPU render: `~/ComfyUI/output/bathroom_v6_00001_.png`
- Phase B GPU renders: `results/T2-v2/`, `results/P2-v2/`

Visual comparison is valid for determining if workflows produce comparable results.

## Workflow Comparison: V6 vs Phase B

| Aspect | V6 | Phase B |
|--------|-----|---------|
| Canny strength | 0.7 | 0.8 |
| Canny end_at | 0.8 | 0.9 |
| Depth strength | 0.5 | 0.9 |
| Depth end_at | 0.6 | 0.8 |
| IP-Adapter weight | 0.4-0.6 | 0.5-0.7 |
| IP-Adapter end_at | 0.6 | 0.8 |
| Steps | 50 | 50 |
| Sampler | dpmpp_2m_sde | euler |
| Scheduler | karras | normal |
| CFG | 7.5 | 7.0 |
| Masks source | UperNet + SAM | SketchUp bundle |

**Key differences:**
- V6 uses weaker ControlNet (especially Depth)
- V6 uses earlier IP-Adapter cutoff (0.6 vs 0.8)
- V6 uses dpmpp_2m_sde/karras (more detailed)
- V6 masks are AI-generated, Phase B uses SketchUp
