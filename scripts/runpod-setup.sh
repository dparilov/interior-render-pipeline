#!/bin/bash
# Interior Render Pipeline - RunPod Setup Script
# Устанавливает ComfyUI, модели и custom nodes для V6/Phase B workflows
#
# Network Volume: mlhzmrjrdt (US-TX-3, 50GB)
# При подключении volume монтируется в /runpod-volume
#
# Usage:
#   First run (empty volume):  ./runpod-setup.sh
#   Subsequent runs:           ./runpod-setup.sh --resume

set -e

VOLUME_PATH="/runpod-volume"
COMFYUI_PATH="$VOLUME_PATH/ComfyUI"

echo "=== IRP RunPod Setup ==="

# Check if network volume is mounted
if [ -d "$VOLUME_PATH" ]; then
    echo "✓ Network volume mounted at $VOLUME_PATH"
    USE_VOLUME=true
else
    echo "⚠ No network volume, using /workspace"
    VOLUME_PATH="/workspace"
    COMFYUI_PATH="/workspace/ComfyUI"
    USE_VOLUME=false
fi

# Check if already setup (resume mode)
if [ -f "$COMFYUI_PATH/main.py" ] && [ -f "$COMFYUI_PATH/models/checkpoints/RealVisXL_V4.0.safetensors" ]; then
    echo "✓ ComfyUI already installed, skipping setup"
    echo ""
    echo "Starting ComfyUI..."
    cd "$COMFYUI_PATH"
    python main.py --listen 0.0.0.0 --port 8188
    exit 0
fi

# 1. Install openssh-server
echo "[1/7] Installing SSH server..."
apt update -qq && apt install -y openssh-server > /dev/null 2>&1
service ssh start

# 2. Add SSH key
echo "[2/7] Adding SSH key..."
mkdir -p ~/.ssh
grep -q "dima@openclaw" ~/.ssh/authorized_keys 2>/dev/null || \
    echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJD/EGU5kk/VOkXsXlR+nN+mMzD65l8q/P4i0dBRoZOV dima@openclaw" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 3. Clone ComfyUI (stable version)
echo "[3/7] Cloning ComfyUI v0.2.4..."
cd "$VOLUME_PATH"
rm -rf ComfyUI 2>/dev/null || true
git clone --branch v0.2.4 --depth 1 https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 4. Install dependencies
echo "[4/7] Installing dependencies..."
pip install -q 'numpy<2' opencv-python timm scikit-image mediapipe sqlalchemy aiohttp

# 5. Download models (parallel)
echo "[5/7] Downloading models (~14GB)..."
cd "$COMFYUI_PATH/models"
mkdir -p checkpoints controlnet ipadapter clip_vision

# Parallel downloads
wget -q --show-progress -P checkpoints/ \
    https://huggingface.co/SG161222/RealVisXL_V4.0/resolve/main/RealVisXL_V4.0.safetensors &
wget -q --show-progress -O controlnet/controlnet-canny-sdxl.safetensors \
    https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors &
wget -q --show-progress -O controlnet/controlnet-depth-sdxl.safetensors \
    https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors &
wget -q --show-progress -P ipadapter/ \
    https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors &
wget -q --show-progress -O clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors \
    https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors &
wait
echo "✓ Models downloaded"

# 6. Install custom nodes
echo "[6/7] Installing custom nodes..."
cd "$COMFYUI_PATH/custom_nodes"
git clone --depth 1 https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
git clone --depth 1 https://github.com/Fannovel16/comfyui_controlnet_aux.git

# 7. Setup input files from IRP repo
echo "[7/7] Setting up input files..."
cd "$COMFYUI_PATH/input"
git clone --depth 1 -b delta https://github.com/dparilov/interior-render-pipeline.git irp
cp -r irp/examples/bathroom_01/* .
mkdir -p refs masks_final
cp references/* refs/ 2>/dev/null || true
cp masks/* masks_final/ 2>/dev/null || true
cp beauty.png front.jpg 2>/dev/null || true
cp depth.png v6_depth_00001_.png 2>/dev/null || true

# Fix mask naming for V6 workflow
cd masks_final
for f in *.png; do
    base=$(basename "$f" .png)
    cp "$f" "mask_${base}.png" 2>/dev/null || true
done
cp walls.png mask_wall.png 2>/dev/null || true
cp shower_screen.png mask_bathtub_screen.png 2>/dev/null || true
python3 -c 'import numpy as np; from PIL import Image; Image.fromarray(np.zeros((1024, 1024), dtype=np.uint8)).save("mask_faucet.png")' 2>/dev/null || true

echo ""
echo "==========================================="
echo "=== Setup Complete ==="
echo "==========================================="
echo ""
echo "ComfyUI path: $COMFYUI_PATH"
echo "Models: $(ls -1 $COMFYUI_PATH/models/checkpoints/*.safetensors 2>/dev/null | wc -l) checkpoint(s)"
echo ""
echo "To start ComfyUI:"
echo "  cd $COMFYUI_PATH && python main.py --listen 0.0.0.0 --port 8188"
echo ""
if [ "$USE_VOLUME" = true ]; then
    echo "✓ Using network volume - data persists between sessions!"
else
    echo "⚠ No network volume - data will be lost on pod termination"
fi
