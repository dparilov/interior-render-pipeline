# RunPod Skill

## Purpose

Manage RunPod GPU compute resources: pods, serverless endpoints, cost tracking.

## Credentials

**Location:** `~/.openclaw/workspace/.secrets/runpod.json`

```json
{
  "apiKey": "rpa_..."
}
```

## Quick Reference

### API Base
```
https://api.runpod.io/graphql?api_key=<API_KEY>
```

### Get API Key
```bash
API_KEY=$(cat ~/.openclaw/workspace/.secrets/runpod.json | python3 -c "import json,sys; print(json.load(sys.stdin)['apiKey'])")
```

## Pod Operations

### List Pods
```bash
curl -s "https://api.runpod.io/graphql?api_key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { myself { pods { id name runtime { uptimeInSeconds } machine { gpuDisplayName } costPerHr } } }"}' | python3 -m json.tool
```

### Start Pod
```bash
curl -s "https://api.runpod.io/graphql?api_key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { podResume(input: {podId: \"<POD_ID>\"}) { id desiredStatus } }"}'
```

### Stop Pod
```bash
curl -s "https://api.runpod.io/graphql?api_key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { podStop(input: {podId: \"<POD_ID>\"}) { id desiredStatus } }"}'
```

### SSH to Pod
```bash
ssh root@<IP> -p <PORT> -i ~/.ssh/id_rsa
```

## Network Volume (IRP Persistent Storage)

- **ID:** `mlhzmrjrdt`
- **Name:** `magnificent_azure_slug`
- **Size:** 50GB
- **Datacenter:** US-TX-3
- **Cost:** ~$5/month (persistent)
- **Mount:** `/runpod-volume` (auto-mounted when pod uses this volume)

При создании pod выбирай этот volume — модели и настройки сохранятся между сессиями.

## Known Pods

| ID | Name | GPU | Cost/hr | Notes |
|----|------|-----|---------|-------|
| (create new) | irp-persistent | RTX 4090/A6000 | $0.44-0.79 | Use network volume mlhzmrjrdt |

## Cost Tracking

### Per-Render Estimates

| Type | Time | Cost |
|------|------|------|
| Simple render | ~32s | 0.52¢ |
| Multi-IPAdapter 9 | ~50s | 0.82¢ |
| With refiner | ~66s | 1.08¢ |

### Cost Formula
```
cost = (render_time_sec / 3600) * cost_per_hr
```

## Best Practices

1. **Stop pods** immediately after work
2. **Batch renders** to minimize idle time
3. **Monitor uptime** — idle pods still cost
4. **Use serverless** only for production API (not dev)

## Render Workflow Governance

⚠️ **CRITICAL: Workflow Immutability Rules**

### Core Principles

1. **Workflows are immutable source-of-truth**
   - Never substitute models (e.g. sd_xl_base → RealVisXL)
   - Never change graph semantics
   - Never "adapt" prompts, weights, or node order

2. **Allowed modifications only:**
   - API format conversion (UI JSON → API JSON)
   - Path fixes (mounting, symlinks)
   - Setup scripts (dependencies, environment)
   - Execution wrappers

3. **Every execution must produce:**
   - Output PNG
   - Executed workflow JSON (exact copy used)
   - Workflow hash (sha256)
   - `experiment.json` with metadata
   - README/verdict

4. **Reproducibility tracking:**
   - "Execution confirmed" ≠ "Visual equivalence confirmed"
   - Cross-device drift makes workflow a historical artifact
   - Such workflows must NOT be used as trusted baseline

5. **Commit separation:**
   - Environment setup commits (models, deps)
   - Execution commits (results, logs)
   - Interpretation commits (analysis, verdicts)

6. **New workflow creation:**
   - ANY change to model/prompt/mask/order/weight = NEW workflow candidate
   - Document as new experiment, not "fix"

### What to do when models are missing

❌ **WRONG:** Substitute with available model
✅ **RIGHT:** Download the exact model specified in workflow

```bash
# Example: download missing sd_xl_base
wget -P models/checkpoints/ \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

### What to do when files are missing

❌ **WRONG:** Create empty mask, use different image
✅ **RIGHT:** Find original source, copy exact files

### experiment.json Template

```json
{
  "workflow": "T1-v2",
  "workflow_hash": "sha256:...",
  "timestamp": "2026-03-30T22:31:00Z",
  "gpu": "RTX 4090",
  "pod_id": "...",
  "runtime_seconds": 131,
  "output": "T1_v2_rtx4090_131s.png",
  "models_verified": true,
  "reproducibility": "execution_confirmed",
  "notes": ""
}
```

## Troubleshooting

### Pod won't start
- Check account balance
- Check GPU availability in region
- Try different GPU type

### SSH timeout
- Pod may be starting (wait 30-60s)
- Check pod status via API
- Verify SSH key is uploaded

### ComfyUI not responding
- SSH in and check: `curl localhost:8188/system_stats`
- May need restart: `pkill -f main.py && cd /workspace/ComfyUI && python main.py --listen`
