# RunPod GPU Renders — 2026-03-30

## Environment
- **Pod:** wilful_ivory_giraffe (1fn8bewp35ahzq)
- **GPU:** NVIDIA GeForce RTX 4090 (24GB VRAM)
- **Storage:** alxzxq0gil (EU-RO-1, 50GB)
- **ComfyUI:** v0.18.1

## V6 Render (bathroom_v6_runpod.png)
- **Workflow:** v6_workflow_fixed.json
- **Input:** sketch.jpg (hand-drawn bathroom)
- **ControlNet:** Canny 0.7 (end 80%), Depth 0.5 (end 60%)
- **IP-Adapter:** 9 regional zones with attention masks
- **Steps:** 50, CFG 7.5, dpmpp_2m_sde + karras
- **Seed:** 42
- **Time:** ~99 sec (incl. model loading), ~8 sec pure sampling
- **Resolution:** 1024×1024

## S2 Phase B (bathroom_s2_phaseb_00001_.png)
- **Workflow:** s2_workflow.json
- **Input:** beauty.png (SketchUp render)
- **Depth:** Ground-truth from SketchUp (s1_depth.png)
- **Boundary:** SetLatentNoiseMask with boundary_mask.png
- **ControlNet:** Canny 0.8 (end 90%), Depth 0.9 (end 70%)
- **IP-Adapter:** 7 regional zones (floor, walls, vanity, mirror, bathtub, basket, towel_warmer)
- **Steps:** 50, CFG 7.5, dpmpp_2m_sde + karras
- **Seed:** 42
- **Time:** ~27 sec (models cached)
- **Resolution:** 1920×1080

## Key Differences
| Aspect | V6 | S2 Phase B |
|--------|-----|------------|
| Input | Hand sketch | SketchUp render |
| Depth | Neural (DepthAnything) | Ground-truth |
| Boundary mask | None | SketchUp silhouette |
| Resolution | 1024×1024 | 1920×1080 |
| Canny strength | 0.7 | 0.8 |
| Depth strength | 0.5 | 0.9 |

## Performance Comparison
- **CPU (local):** ~34 min for 50 steps
- **GPU (RTX 4090):** ~8-27 sec for 50 steps
- **Speedup:** ~75-250x

## F2-v2 Phase B Reference (from delta branch)
- **Source:** `results/F2-v2/IRP_render_00053_.png`
- **Experiment:** F2-v2 (all entities, multi-IPAdapter regional)
- **9 Entities:** walls, floor, bathtub, shower_screen, vanity, mirror, towel_warmer, basket, rainshower
- **Weights:** surfaces 0.55, fixtures 0.5
- **Refiner:** OFF
- **Time:** 78.1 sec
- **Platform:** RunPod RTX 4090

This is the canonical Phase B reference render from the experiment plan.
