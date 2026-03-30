#!/bin/bash
# Download all required models for IRP workflows
# Usage: ./download-models.sh [comfyui_path]

COMFYUI_PATH="${1:-/workspace/ComfyUI}"

echo "=== Downloading IRP Models ==="
echo "Target: $COMFYUI_PATH/models"

cd "$COMFYUI_PATH/models"
mkdir -p checkpoints controlnet ipadapter clip_vision

# Parallel downloads
echo ""
echo "Starting downloads (~14GB total)..."

# Checkpoint (6.5GB)
if [ ! -f "checkpoints/RealVisXL_V4.0.safetensors" ]; then
    echo "Downloading RealVisXL_V4.0..."
    wget -q --show-progress -P checkpoints/ \
        https://huggingface.co/SG161222/RealVisXL_V4.0/resolve/main/RealVisXL_V4.0.safetensors &
fi

# ControlNet Canny (2.4GB)
if [ ! -f "controlnet/controlnet-canny-sdxl.safetensors" ]; then
    echo "Downloading ControlNet Canny..."
    wget -q --show-progress -O controlnet/controlnet-canny-sdxl.safetensors \
        https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors &
fi

# ControlNet Depth (2.4GB)
if [ ! -f "controlnet/controlnet-depth-sdxl.safetensors" ]; then
    echo "Downloading ControlNet Depth..."
    wget -q --show-progress -O controlnet/controlnet-depth-sdxl.safetensors \
        https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0/resolve/main/diffusion_pytorch_model.fp16.safetensors &
fi

# IP-Adapter (809MB)
if [ ! -f "ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors" ]; then
    echo "Downloading IP-Adapter..."
    wget -q --show-progress -P ipadapter/ \
        https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors &
fi

# CLIP Vision (2.4GB)
if [ ! -f "clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" ]; then
    echo "Downloading CLIP Vision..."
    wget -q --show-progress -O clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors \
        https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors &
fi

# Wait for all downloads
wait

echo ""
echo "=== Download Complete ==="
ls -lh checkpoints/*.safetensors 2>/dev/null
ls -lh controlnet/*.safetensors 2>/dev/null
ls -lh ipadapter/*.safetensors 2>/dev/null
ls -lh clip_vision/*.safetensors 2>/dev/null
