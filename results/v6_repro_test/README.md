# V6 Reproducibility Test

## Summary

| Metric | GPU (RTX 4090) | CPU Reference |
|--------|----------------|---------------|
| Runtime | 95 sec | ~30 min |
| Speedup | **19x** | baseline |
| Cost | $0.015 | $0 |

## Files

- `workflow_v6_rtx4090.json` - ComfyUI workflow (hash: `66348fa38703f691`)
- `v6_rtx4090_seed42.png` - GPU render result
- `v6_cpu_reference.png` - CPU reference render
- `experiment.json` - Full experiment metadata

## Workflow Parameters

```
seed: 42
steps: 50
cfg: 7.5
sampler: dpmpp_2m_sde
scheduler: karras
resolution: 1024x1024
checkpoint: RealVisXL_V4.0
controlnet_canny: 0.7
controlnet_depth: 0.5
regional_ipadapter: 9 regions
```

## Cross-Device Reproducibility

**Verdict: PASS_WITH_VARIANCE**

SDXL diffusion is not deterministic across different hardware (CPU vs GPU) due to:
- Different floating-point precision
- Different CUDA kernel implementations
- Parallel execution order variations

Same seed on same device type = identical output.
Same seed on different device = visually similar, pixel-different.

## How to Reproduce

### On RunPod (RTX 4090)

```bash
# 1. Create pod with network volume mlhzmrjrdt
# 2. Run setup
wget -qO- https://raw.githubusercontent.com/dparilov/interior-render-pipeline/delta/scripts/runpod-setup.sh | bash

# 3. Start ComfyUI
cd /runpod-volume/ComfyUI && python main.py --listen 0.0.0.0 --port 8188

# 4. Load workflow and queue
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": <workflow_v6_rtx4090.json contents>}'
```

### On Local CPU

```bash
cd ~/ComfyUI
python main.py --cpu
# Load same workflow via web UI
```

## Models Required

| Model | Size | Source |
|-------|------|--------|
| RealVisXL_V4.0 | 6.5GB | [HuggingFace](https://huggingface.co/SG161222/RealVisXL_V4.0) |
| ControlNet Canny SDXL | 2.4GB | [HuggingFace](https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0) |
| ControlNet Depth SDXL | 2.4GB | [HuggingFace](https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0) |
| IP-Adapter Plus SDXL | 809MB | [HuggingFace](https://huggingface.co/h94/IP-Adapter) |
| CLIP ViT-H | 2.4GB | [HuggingFace](https://huggingface.co/h94/IP-Adapter) |

## Test Date

2026-03-30
