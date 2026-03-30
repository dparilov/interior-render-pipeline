#!/bin/bash
# Interior Render Pipeline - RunPod Setup Script
# Устанавливает ComfyUI, модели и custom nodes для V6/T2 workflows

set -e

echo "=== IRP RunPod Setup ==="

# 1. Install openssh-server
echo "[1/6] Installing SSH server..."
apt update -qq && apt install -y openssh-server > /dev/null
service ssh start

# 2. Add SSH key
echo "[2/6] Adding SSH key..."
mkdir -p ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJD/EGU5kk/VOkXsXlR+nN+mMzD65l8q/P4i0dBRoZOV dima@openclaw" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 3. Clone ComfyUI
echo "[3/6] Cloning ComfyUI..."
cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 4. Install dependencies
echo "[4/6] Installing dependencies..."
pip install -q 'numpy<2' opencv-python timm scikit-image mediapipe

# 5. Download models
echo "[5/6] Downloading models..."
cd /workspace/ComfyUI/models

# Checkpoint
wget -q --show-progress -P checkpoints/ \
  https://huggingface.co/SG161222/RealVisXL_V4.0/resolve/main/RealVisXL_V4.0.safetensors

# ControlNets
wget -q --show-progress -P controlnet/ \
  https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors \
  -O controlnet/controlnet-canny-sdxl.safetensors
wget -q --show-progress -P controlnet/ \
  https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors \
  -O controlnet/controlnet-depth-sdxl.safetensors

# IP-Adapter
mkdir -p ipadapter clip_vision
wget -q --show-progress -P ipadapter/ \
  https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors
wget -q --show-progress -P clip_vision/ \
  https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors \
  -O clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors

# 6. Install custom nodes
echo "[6/6] Installing custom nodes..."
cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git

# 7. Clone IRP repo with examples
echo "[7/6] Cloning IRP repo..."
cd /workspace/ComfyUI/input
git clone https://github.com/dparilov/interior-render-pipeline.git irp_repo
cd irp_repo && git checkout delta
cp -r examples/bathroom_01/* /workspace/ComfyUI/input/

# Setup masks and refs
cd /workspace/ComfyUI/input
cp references/* refs/ 2>/dev/null || mkdir -p refs && cp references/* refs/
cp masks/* masks_final/ 2>/dev/null || mkdir -p masks_final && cp masks/* masks_final/
cp beauty.png front.jpg 2>/dev/null || true
cp depth.png v6_depth_00001_.png

# Create missing masks
cd masks_final
cp mask_walls.png mask_wall.png 2>/dev/null || true
cp mask_shower_screen.png mask_bathtub_screen.png 2>/dev/null || true
python3 -c 'import numpy as np; from PIL import Image; Image.fromarray(np.zeros((1024, 1024), dtype=np.uint8)).save("mask_faucet.png")' 2>/dev/null || true

echo ""
echo "=== Setup Complete ==="
echo "Start ComfyUI: cd /workspace/ComfyUI && python main.py --listen 0.0.0.0 --port 8188"
