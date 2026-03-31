# Render Pipeline Optimization

## Goal

Minimize billable GPU time by splitting render pipeline into:
1. **Offline prep** (local, no pod) — prepare everything before pod starts
2. **Pod init** (one-time) — verify pod readiness
3. **Render** (per experiment) — upload → execute → download

**Target:** Pod billable time < 2 min per render

---

## Pipeline Phases

### Phase 1: Offline Prep (local, no pod)

| Step | Action | Output |
|------|--------|--------|
| 1.1 | Validate bundle | validation_report.json |
| 1.2 | Build workflow | workflow_api.json |
| 1.3 | List required files | render_manifest.json |
| 1.4 | Package render bundle | {experiment}_render_package.zip |

**Script:** `scripts/prepare_render.py`

**Usage:**
```bash
python3 scripts/prepare_render.py \
  --bundle examples/bathroom_01_surface_only \
  --experiment SF1 \
  --output results/SF1/
```

### Phase 2: Pod Init (one-time per session)

| Step | Action | Target Time |
|------|--------|-------------|
| 2.1 | Verify models on network volume | <10s |
| 2.2 | Verify ComfyUI ready | <5s |
| 2.3 | Log environment state | <5s |

**Script:** `scripts/pod_init.sh`

**Usage:**
```bash
./scripts/pod_init.sh <pod_ip> <pod_port>
```

### Phase 3: Render (per experiment)

| Step | Action | Target Time |
|------|--------|-------------|
| 3.1 | Upload render package | <10s |
| 3.2 | Execute workflow | 20-60s |
| 3.3 | Download results | <10s |
| 3.4 | Log timing | <1s |

**Script:** `scripts/pod_render.sh`

**Usage:**
```bash
./scripts/pod_render.sh <pod_ip> <pod_port> results/SF1/SF1_render_package.zip
```

---

## Logging Format

Every render produces a timing log:

```json
{
  "experiment": "SF1",
  "timestamp": "2026-03-31T16:00:00Z",
  "phases": {
    "offline_prep": {"duration_sec": 5.2, "status": "ok"},
    "pod_init": {"duration_sec": 12.1, "status": "ok"},
    "upload": {"duration_sec": 3.4, "bytes": 2048000},
    "render": {"duration_sec": 22.5, "status": "ok"},
    "download": {"duration_sec": 2.1, "bytes": 1024000}
  },
  "total_pod_time_sec": 40.1,
  "total_billable_sec": 40.1
}
```

**Location:** `logs/render_{experiment}_{timestamp}.json`

---

## Network Volume Requirements

Models and dependencies must be pre-installed on network volume:

```
/runpod-volume/
├── ComfyUI/
│   ├── models/
│   │   ├── checkpoints/
│   │   │   └── RealVisXL_V4.0.safetensors
│   │   ├── clip_vision/
│   │   │   └── CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
│   │   ├── ipadapter/
│   │   │   └── ip-adapter-plus_sdxl_vit-h.safetensors
│   │   └── controlnet/
│   │       ├── controlnet-canny-sdxl.safetensors
│   │       └── controlnet-depth-sdxl.safetensors
│   └── custom_nodes/
│       ├── ComfyUI_IPAdapter_plus/
│       └── ComfyUI-Advanced-ControlNet/
└── deps_installed.marker
```

**One-time setup:** `scripts/setup_network_volume.sh`

---

## Comparison: Before vs After

| Metric | Before (SF1) | Target |
|--------|--------------|--------|
| Total pod time | ~5+ min | < 2 min |
| Render time | ~20 sec | ~20 sec |
| Upload/download | inline | batched |
| Deps install | every time | never |

---

## Quick Reference

```bash
# 1. Offline prep (local)
python3 scripts/prepare_render.py --bundle examples/bathroom_01_surface_only --experiment SF2

# 2. Start pod (via RunPod UI or API)
# ...

# 3. Init pod (once per session)
./scripts/pod_init.sh 213.173.98.39 15587

# 4. Run render
./scripts/pod_render.sh 213.173.98.39 15587 results/SF2/SF2_render_package.zip

# 5. Stop pod
curl ... podStop mutation
```
