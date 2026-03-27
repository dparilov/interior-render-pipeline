#!/usr/bin/env python3
"""
Interior Design Render v2 - Based on StableDesign workflow
Uses SD 1.5 + Dual ControlNet (Depth + Segmentation) + IP-Adapter
"""

import json
import requests
import time
import sys
import os
import shutil
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

def create_workflow(input_image, positive_prompt, negative_prompt="", seed=42, steps=50):
    """Create the Interior Design workflow"""
    
    # Check if input image exists
    if not os.path.exists(input_image):
        print(f"Error: Input image not found: {input_image}")
        return None
    
    # Copy image to ComfyUI input folder
    input_dir = Path.home() / "ComfyUI/input"
    image_name = os.path.basename(input_image)
    dest_path = input_dir / image_name
    
    if not dest_path.exists() or os.path.getmtime(input_image) > os.path.getmtime(dest_path):
        shutil.copy(input_image, dest_path)
        print(f"Copied input image to {dest_path}")
    
    # Full prompt with quality suffixes
    full_positive = f"{positive_prompt}, interior design, 4K, high resolution, photorealistic"
    full_negative = f"window, door, low resolution, banner, logo, watermark, text, deformed, blurry, out of focus, surreal, ugly, beginner, {negative_prompt}"
    
    prompt = {
        # === INPUT ===
        # Load input image
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        # Normalize image to 512px
        "2": {
            "class_type": "Image Normalize",
            "inputs": {
                "images": ["1", 0],
                "target_size": 512,
                "multiple": 8,
                "mode": "bilinear"
            }
        },
        
        # === DEPTH ESTIMATION ===
        "3": {
            "class_type": "DownloadAndLoadDepthAnythingV2Model",
            "inputs": {
                "model": "depth_anything_v2_vitl_fp32.safetensors",
                "precision": "auto"
            }
        },
        "4": {
            "class_type": "DepthAnything_V2",
            "inputs": {
                "da_model": ["3", 0],
                "images": ["2", 0]
            }
        },
        
        # === SEGMENTATION ===
        "5": {
            "class_type": "Control Items",
            "inputs": {
                "window": True,
                "door": True,
                "staircase": False,
                "columns": False
            }
        },
        "6": {
            "class_type": "Interior Design Segmentator",
            "inputs": {
                "image": ["2", 0],
                "control_items": ["5", 0]
            }
        },
        
        # === STYLE GUIDANCE (SSD-1B) ===
        "7": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "SSD-1B.safetensors"}
        },
        "8": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["7", 1],
                "text": full_positive
            }
        },
        "9": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["7", 1],
                "text": full_negative
            }
        },
        # Get image size for empty latent
        "10": {
            "class_type": "GetImageSize",
            "inputs": {"image": ["2", 0]}
        },
        "11": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            }
        },
        # First KSampler - generate style guidance image
        "12": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["7", 0],
                "positive": ["8", 0],
                "negative": ["9", 0],
                "latent_image": ["11", 0],
                "seed": seed,
                "steps": 25,
                "cfg": 9,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 0.9
            }
        },
        # VAE Decode style image
        "13": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["12", 0],
                "vae": ["7", 2]
            }
        },
        
        # === MAIN DIFFUSION (Realistic Vision Inpainting) ===
        "14": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "Realistic_Vision_V5.1-inpainting.safetensors"}
        },
        
        # Load ControlNets
        "15": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "control_v11p_sd15_seg_fp16.safetensors"}
        },
        "16": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "control_v11f1p_sd15_depth_fp16.safetensors"}
        },
        
        # CLIP encode for inpainting
        "17": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["14", 1],
                "text": full_positive
            }
        },
        "18": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["14", 1],
                "text": full_negative
            }
        },
        
        # Apply Segmentation ControlNet
        "19": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["17", 0],
                "negative": ["18", 0],
                "control_net": ["15", 0],
                "image": ["6", 0],  # segmentation map
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 1
            }
        },
        # Apply Depth ControlNet
        "20": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["19", 0],
                "negative": ["19", 1],
                "control_net": ["16", 0],
                "image": ["4", 0],  # depth map
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 1
            }
        },
        
        # Grow mask from segmentation
        "21": {
            "class_type": "GrowMask",
            "inputs": {
                "mask": ["6", 1],
                "expand": 2,
                "tapered_corners": True
            }
        },
        
        # VAE Encode for Inpaint
        "22": {
            "class_type": "VAEEncodeForInpaint",
            "inputs": {
                "pixels": ["2", 0],
                "vae": ["14", 2],
                "mask": ["21", 0],
                "grow_mask_by": 0
            }
        },
        
        # === IP-ADAPTER ===
        "23": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter_sd15.safetensors"}
        },
        "24": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        },
        # Invert mask for attention
        "25": {
            "class_type": "InvertMask",
            "inputs": {"mask": ["21", 0]}
        },
        # IP-Adapter Advanced
        "26": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["14", 0],
                "ipadapter": ["23", 0],
                "image": ["13", 0],  # style guidance image
                "attn_mask": ["25", 0],
                "clip_vision": ["24", 0],
                "weight": 0.4,
                "weight_type": "linear",
                "combine_embeds": "concat",
                "start_at": 0,
                "end_at": 1,
                "embeds_scaling": "V only"
            }
        },
        
        # Main KSampler - inpainting
        "27": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["26", 0],
                "positive": ["20", 0],
                "negative": ["20", 1],
                "latent_image": ["22", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 10,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 0.9
            }
        },
        
        # VAE Decode final
        "28": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["27", 0],
                "vae": ["14", 2]
            }
        },
        
        # Save Image
        "29": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["28", 0],
                "filename_prefix": "interior_design_v2"
            }
        },
        
        # === PREVIEW NODES ===
        "30": {
            "class_type": "PreviewImage",
            "inputs": {"images": ["4", 0]}
        },
        "31": {
            "class_type": "PreviewImage",
            "inputs": {"images": ["6", 0]}
        },
        "32": {
            "class_type": "PreviewImage",
            "inputs": {"images": ["13", 0]}
        }
    }
    
    return prompt

def queue_prompt(prompt):
    """Send prompt to ComfyUI queue"""
    data = {"prompt": prompt}
    response = requests.post(f"{COMFYUI_API}/prompt", json=data)
    return response.json()

def wait_for_completion(prompt_id, timeout=7200):
    """Wait for prompt to complete"""
    start_time = time.time()
    last_progress = ""
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
            history = response.json()
            
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        
        # Check progress
        try:
            response = requests.get(f"{COMFYUI_API}/queue")
            queue = response.json()
            running = queue.get('queue_running', [])
            pending = queue.get('queue_pending', [])
            
            elapsed = int(time.time() - start_time)
            progress = f"\r[{elapsed//60}:{elapsed%60:02d}] Running: {len(running)}, Pending: {len(pending)}"
            
            if progress != last_progress:
                print(progress, end="", flush=True)
                last_progress = progress
            
            if not running and not pending:
                # Check if completed
                response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
                history = response.json()
                if prompt_id in history:
                    print("\nCompleted!")
                    return history[prompt_id]
        except Exception as e:
            print(f"\nError checking progress: {e}")
        
        time.sleep(5)
    
    print(f"\nTimeout after {timeout}s")
    return None

def main():
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    
    # English prompt for bathroom
    positive_prompt = """A modern compact bathroom with warm natural lighting from a small window.
Mediterranean-style blue patterned floor tiles with white geometric circles pattern.
White glossy ribbed subway tiles on walls, vertically laid.
Dark charcoal floating vanity with two drawers and white ceramic sink.
Rectangular mirror with rounded corners and warm LED backlight.
Chrome rain shower system. White cast iron bathtub.
White vertical electric towel warmer. Natural rattan laundry basket."""

    negative_prompt = """brass faucet, gold faucet, black towel warmer, chrome towel warmer,
white vanity, wooden vanity, beige floor tiles, light floor tiles"""
    
    print("=" * 60)
    print("Interior Design Render v2 - SD 1.5 Pipeline")
    print("=" * 60)
    print(f"Input: {sketch_path}")
    print(f"Prompt: {positive_prompt[:80]}...")
    print("=" * 60)
    
    # Create workflow
    prompt = create_workflow(
        input_image=str(sketch_path),
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=42,
        steps=50
    )
    
    if not prompt:
        return 1
    
    # Save workflow for debugging
    workflow_log = Path.home() / ".openclaw/workspace/logs/comfyui"
    workflow_log.mkdir(parents=True, exist_ok=True)
    log_file = workflow_log / f"interior_v2_{int(time.time())}.json"
    with open(log_file, "w") as f:
        json.dump(prompt, f, indent=2)
    print(f"Workflow saved to: {log_file}")
    
    # Queue prompt
    print("\nQueuing prompt...")
    result = queue_prompt(prompt)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        if 'node_errors' in result:
            for node_id, errors in result['node_errors'].items():
                print(f"  Node {node_id}: {errors}")
        return 1
    
    prompt_id = result.get('prompt_id')
    print(f"Prompt ID: {prompt_id}")
    
    # Wait for completion
    print("\nWaiting for completion (CPU: ~30-60 min, 50 steps)...")
    history = wait_for_completion(prompt_id)
    
    if history:
        outputs = history.get('outputs', {})
        for node_id, output in outputs.items():
            if 'images' in output:
                for img in output['images']:
                    filename = img['filename']
                    print(f"Output: ~/ComfyUI/output/{filename}")
        print("\n✅ Render completed!")
        return 0
    else:
        print("\n❌ Render failed or timed out")
        return 1

if __name__ == "__main__":
    sys.exit(main())
