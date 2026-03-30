#!/bin/bash
# IRP Pod Setup Script
# Usage: ./pod-setup.sh
# Run this after SSH into a new pod to prepare ComfyUI

set -e

echo "=== IRP Pod Setup ==="
echo "Started at: $(date)"

# 1. Check GPU
echo ""
echo "[1/5] Checking GPU..."
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "UNKNOWN")
GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null || echo "UNKNOWN")
echo "GPU: $GPU_NAME ($GPU_MEM)"

# 2. Check if ComfyUI exists (network volume)
echo ""
echo "[2/5] Checking ComfyUI installation..."
if [ -f "/workspace/ComfyUI/main.py" ]; then
    echo "✓ ComfyUI found at /workspace/ComfyUI"
    COMFYUI_PATH="/workspace/ComfyUI"
else
    echo "ComfyUI not found. Installing..."
    cd /workspace
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
    COMFYUI_PATH="/workspace/ComfyUI"
fi

# 3. Install dependencies
echo ""
echo "[3/5] Installing Python dependencies..."
pip install -q -r $COMFYUI_PATH/requirements.txt 2>/dev/null || true
pip install -q opencv-python-headless tqdm alembic blake3 sqlalchemy aiohttp 2>/dev/null || true

# 4. Check models
echo ""
echo "[4/5] Checking models..."
MODELS_OK=true

check_model() {
    local path="$1"
    local name="$2"
    if [ -f "$path" ]; then
        SIZE=$(du -h "$path" | cut -f1)
        echo "✓ $name ($SIZE)"
    else
        echo "✗ $name MISSING"
        MODELS_OK=false
    fi
}

check_model "$COMFYUI_PATH/models/checkpoints/RealVisXL_V4.0.safetensors" "RealVisXL_V4.0"
check_model "$COMFYUI_PATH/models/controlnet/controlnet-canny-sdxl.safetensors" "ControlNet Canny"
check_model "$COMFYUI_PATH/models/controlnet/controlnet-depth-sdxl.safetensors" "ControlNet Depth"
check_model "$COMFYUI_PATH/models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors" "IP-Adapter"
check_model "$COMFYUI_PATH/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" "CLIP Vision"

if [ "$MODELS_OK" = false ]; then
    echo ""
    echo "⚠ Missing models. Download with:"
    echo "  ./download-models.sh"
fi

# 5. Install screen and start ComfyUI
echo ""
echo "[5/5] Starting ComfyUI..."
apt-get update -qq && apt-get install -y -qq screen > /dev/null 2>&1

pkill -9 -f main.py 2>/dev/null || true
sleep 2

screen -dmS comfyui bash -c "cd $COMFYUI_PATH && python main.py --listen 0.0.0.0 --port 8188"
sleep 20

# Verify
if curl -s localhost:8188/system_stats > /dev/null 2>&1; then
    echo "✓ ComfyUI running on port 8188"
    curl -s localhost:8188/system_stats | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Device: {d[\"devices\"][0][\"name\"]}')"
else
    echo "✗ ComfyUI failed to start"
    echo "Check logs: screen -r comfyui"
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo "ComfyUI: http://localhost:8188"
echo "Screen: screen -r comfyui"

# 6. Setup file compatibility
echo ""
echo "[6/6] Setting up file compatibility..."
cd /workspace/ComfyUI/input

# Create symlinks for folder compatibility
ln -sf refs references 2>/dev/null || true
ln -sf masks_final masks 2>/dev/null || true

# Create depth.png from available depth file
if [ ! -f depth.png ]; then
    cp s1_depth.png depth.png 2>/dev/null || cp v6_depth*.png depth.png 2>/dev/null || true
fi

# Create mask symlinks without prefix
cd masks_final 2>/dev/null || cd masks || true
for f in mask_*.png; do
    [ -f "$f" ] && ln -sf "$f" "${f#mask_}" 2>/dev/null || true
done

# Special case mappings
ln -sf mask_bathtub_screen.png shower_screen.png 2>/dev/null || true
ln -sf mask_wall.png walls.png 2>/dev/null || true

# Create empty masks for missing ones
python3 -c 'from PIL import Image; import numpy as np; Image.fromarray(np.zeros((1024, 1024), dtype=np.uint8)).save("mask_rainshower.png")' 2>/dev/null || true
ln -sf mask_rainshower.png rainshower.png 2>/dev/null || true

echo "✓ File compatibility setup complete"
