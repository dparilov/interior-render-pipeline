#!/bin/bash
#
# Pod Initialization Check
# Verifies pod is ready for rendering (models, ComfyUI, deps)
#
# Usage: ./scripts/pod_init.sh <pod_ip> <pod_port>
#
# Output: pod_init_status.json with timing and status

set -e

POD_IP="${1:?Usage: $0 <pod_ip> <pod_port>}"
POD_PORT="${2:?Usage: $0 <pod_ip> <pod_port>}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_ed25519}"
OUTPUT_DIR="${OUTPUT_DIR:-.}"

echo "=== Pod Init Check ==="
echo "Pod: $POD_IP:$POD_PORT"
echo ""

START_TOTAL=$(date +%s.%N)

# Function to run SSH command
ssh_run() {
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        root@$POD_IP -p $POD_PORT -i $SSH_KEY "$@"
}

# Step 1: Check SSH connectivity
echo "[1/4] Checking SSH..."
START=$(date +%s.%N)
if ssh_run "echo ok" > /dev/null 2>&1; then
    SSH_OK="true"
    echo "  OK"
else
    SSH_OK="false"
    echo "  FAIL: Cannot connect via SSH"
    exit 1
fi
SSH_SEC=$(echo "$(date +%s.%N) - $START" | bc)

# Step 2: Check models on network volume
echo "[2/4] Checking models..."
START=$(date +%s.%N)
MODELS_CHECK=$(ssh_run "
    MISSING=0
    [ -f /workspace/ComfyUI/models/checkpoints/RealVisXL_V4.0.safetensors ] || MISSING=1
    [ -f /workspace/ComfyUI/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors ] || MISSING=1
    [ -f /workspace/ComfyUI/models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors ] || MISSING=1
    [ -f /workspace/ComfyUI/models/controlnet/controlnet-canny-sdxl.safetensors ] || MISSING=1
    [ -f /workspace/ComfyUI/models/controlnet/controlnet-depth-sdxl.safetensors ] || MISSING=1
    
    if [ \$MISSING -eq 0 ]; then
        echo 'ok'
    else
        echo 'missing'
    fi
")
MODELS_SEC=$(echo "$(date +%s.%N) - $START" | bc)

if [ "$MODELS_CHECK" = "ok" ]; then
    MODELS_OK="true"
    echo "  OK"
else
    MODELS_OK="false"
    echo "  WARNING: Some models missing"
fi

# Step 3: Check ComfyUI
echo "[3/4] Checking ComfyUI..."
START=$(date +%s.%N)
COMFYUI_CHECK=$(ssh_run "
    if pgrep -f 'python.*main.py' > /dev/null; then
        if curl -s localhost:8188/system_stats > /dev/null 2>&1; then
            echo 'running'
        else
            echo 'starting'
        fi
    else
        echo 'stopped'
    fi
")
COMFYUI_SEC=$(echo "$(date +%s.%N) - $START" | bc)

if [ "$COMFYUI_CHECK" = "running" ]; then
    COMFYUI_OK="true"
    echo "  OK (running)"
elif [ "$COMFYUI_CHECK" = "starting" ]; then
    COMFYUI_OK="starting"
    echo "  WARNING: ComfyUI starting..."
else
    COMFYUI_OK="false"
    echo "  WARNING: ComfyUI not running"
    echo "  Starting ComfyUI..."
    ssh_run "cd /workspace/ComfyUI && nohup python main.py --listen > /tmp/comfyui.log 2>&1 &"
    sleep 10
    # Recheck
    if ssh_run "curl -s localhost:8188/system_stats" > /dev/null 2>&1; then
        COMFYUI_OK="true"
        echo "  OK (started)"
    else
        echo "  FAIL: Could not start ComfyUI"
    fi
fi

# Step 4: Log environment
echo "[4/4] Logging environment..."
START=$(date +%s.%N)
ENV_INFO=$(ssh_run "
    echo '{\"gpu\": \"'$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)'\", \"vram_mb\": '$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)', \"python\": \"'$(python3 --version 2>&1 | cut -d' ' -f2)'\", \"comfyui_version\": \"'$(grep -o 'comfyui_version.*[0-9.]*' /tmp/comfyui.log 2>/dev/null | head -1 | grep -o '[0-9.]*$' || echo 'unknown')'\"}'
")
ENV_SEC=$(echo "$(date +%s.%N) - $START" | bc)
echo "  $ENV_INFO"

TOTAL_SEC=$(echo "$(date +%s.%N) - $START_TOTAL" | bc)

# Determine overall status
if [ "$SSH_OK" = "true" ] && [ "$MODELS_OK" = "true" ] && [ "$COMFYUI_OK" = "true" ]; then
    STATUS="ready"
else
    STATUS="not_ready"
fi

# Output JSON
cat > "$OUTPUT_DIR/pod_init_status.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "pod_ip": "$POD_IP",
  "pod_port": "$POD_PORT",
  "status": "$STATUS",
  "checks": {
    "ssh": {"ok": $SSH_OK, "duration_sec": $SSH_SEC},
    "models": {"ok": $MODELS_OK, "duration_sec": $MODELS_SEC},
    "comfyui": {"ok": $COMFYUI_OK, "duration_sec": $COMFYUI_SEC},
    "environment": {"duration_sec": $ENV_SEC, "info": $ENV_INFO}
  },
  "total_duration_sec": $TOTAL_SEC
}
EOF

echo ""
echo "=== Pod Status: $STATUS ($TOTAL_SEC sec) ==="
echo "Saved: $OUTPUT_DIR/pod_init_status.json"
