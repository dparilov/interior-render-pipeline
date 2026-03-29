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

## Known Pods

| ID | Name | GPU | Cost/hr | SSH |
|----|------|-----|---------|-----|
| m88nqdtocfd818 | pale_salmon_wildcat | RTX 4090 | $0.59 | root@IP -p PORT |

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
