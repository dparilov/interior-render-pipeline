#!/usr/bin/env python3
"""
ComfyUI Render v5 - SDXL + Canny + Depth + Regional IP-Adapter
Each region gets its own IP-Adapter with attention mask
"""

import json
import requests
import time
import sys
import shutil
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

# Regions with their masks and reference descriptions
# For now using seg_map colors as "reference" since we don't have actual material photos
REGIONS = {
    "floor": {
        "mask": "mask_floor.png",
        "prompt": "blue and white geometric pattern ceramic floor tiles, Mediterranean style",
        "weight": 0.5
    },
    "wall": {
        "mask": "mask_wall.png",
        "prompt": "white glossy wavy textured wall tiles, vertical installation",
        "weight": 0.4
    },
    "vanity": {
        "mask": "mask_vanity.png",
        "prompt": "dark charcoal gray floating vanity cabinet with two drawers, white ceramic sink",
        "weight": 0.5
    },
    "mirror": {
        "mask": "mask_mirror.png",
        "prompt": "rectangular mirror with LED backlight",
        "weight": 0.3
    },
    "bathtub": {
        "mask": "mask_bathtub.png",
        "prompt": "white acrylic bathtub with chrome fixtures, glass shower partition",
        "weight": 0.4
    }
}

def create_v5_workflow(seed=42):
    """
    Create workflow with regional IP-Adapter using attention masks
    """
    
    base_prompt = """A modern compact bathroom interior, photorealistic photograph, 8K resolution, 
warm natural lighting from small window, magazine quality interior design photo.
Dark charcoal gray floating vanity with white ceramic sink.
Blue and white geometric pattern floor tiles, Mediterranean style.
White glossy wavy textured wall tiles.
Chrome faucet and fixtures.
White towel warmer on left wall.
Rectangular mirror with LED backlight above vanity.
White acrylic bathtub on right with glass partition."""

    negative_prompt = "low quality, blurry, watermark, text, deformed, brass faucet, gold fixtures, black towel warmer, cartoon, anime, illustration, white vanity, beige tiles"
    
    prompt = {
        # === INPUTS ===
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        
        # === PREPROCESSING ===
        "2": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },
        
        # Load depth map
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": "depth_map.png"}
        },
        
        # === MODEL ===
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        
        # === CLIP ENCODE ===
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": base_prompt
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["4", 1],
                "text": negative_prompt
            }
        },
        
        # === CONTROLNET CANNY ===
        "7": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        "8": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["5", 0],
                "negative": ["6", 0],
                "control_net": ["7", 0],
                "image": ["2", 0],
                "strength": 0.7,
                "start_percent": 0,
                "end_percent": 0.8
            }
        },
        
        # === CONTROLNET DEPTH ===
        "9": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-depth-sdxl.safetensors"}
        },
        "10": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["8", 1],
                "control_net": ["9", 0],
                "image": ["3", 0],
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 0.6
            }
        },
        
        # === IP-ADAPTER SETUP ===
        "11": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        },
        "12": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        },
        
        # === LOAD MASKS ===
        "13": {
            "class_type": "LoadImage",
            "inputs": {"image": "masks/mask_floor.png"}
        },
        "13a": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["13", 0], "channel": "red"}
        },
        "14": {
            "class_type": "LoadImage",
            "inputs": {"image": "masks/mask_vanity.png"}
        },
        "14a": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["14", 0], "channel": "red"}
        },
        "15": {
            "class_type": "LoadImage",
            "inputs": {"image": "masks/mask_wall.png"}
        },
        "15a": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["15", 0], "channel": "red"}
        },
        
        # === LOAD SEGMENTATION AS STYLE REFERENCES ===
        # Using seg_map regions as color/style hints
        "16": {
            "class_type": "LoadImage",
            "inputs": {"image": "seg_map.png"}
        },
        
        # === IP-ADAPTER WITH FLOOR MASK ===
        "20": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["4", 0],
                "ipadapter": ["12", 0],
                "clip_vision": ["11", 0],
                "image": ["16", 0],
                "weight": 0.4,
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.6,
                "embeds_scaling": "V only",
                "attn_mask": ["13a", 0]  # Floor mask
            }
        },
        
        # === IP-ADAPTER WITH VANITY MASK ===
        "21": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["20", 0],
                "ipadapter": ["12", 0],
                "clip_vision": ["11", 0],
                "image": ["16", 0],
                "weight": 0.4,
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.6,
                "embeds_scaling": "V only",
                "attn_mask": ["14a", 0]  # Vanity mask
            }
        },
        
        # === IP-ADAPTER WITH WALL MASK ===
        "22": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["21", 0],
                "ipadapter": ["12", 0],
                "clip_vision": ["11", 0],
                "image": ["16", 0],
                "weight": 0.3,
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.5,
                "embeds_scaling": "V only",
                "attn_mask": ["15a", 0]  # Wall mask
            }
        },
        
        # === EMPTY LATENT ===
        "30": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        
        # === KSAMPLER ===
        "31": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["22", 0],
                "positive": ["10", 0],
                "negative": ["10", 1],
                "latent_image": ["30", 0],
                "seed": seed,
                "steps": 50,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 1.0
            }
        },
        
        # === VAE DECODE ===
        "32": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["31", 0],
                "vae": ["4", 2]
            }
        },
        
        # === SAVE ===
        "33": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["32", 0],
                "filename_prefix": "bathroom_v5"
            }
        }
    }
    
    return prompt

def queue_prompt(prompt):
    data = {"prompt": prompt}
    response = requests.post(f"{COMFYUI_API}/prompt", json=data)
    return response.json()

def wait_for_completion(prompt_id, timeout=7200):
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
            history = response.json()
            
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        
        elapsed = int(time.time() - start_time)
        print(f"\r[{elapsed//60}:{elapsed%60:02d}] Rendering...", end="", flush=True)
        time.sleep(10)
    
    return None

def main():
    # Setup files
    input_dir = Path.home() / "ComfyUI/input"
    
    sketch = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    seg_map = Path.home() / "ComfyUI/output/seg_map_00001_.png"
    depth_map = Path.home() / "ComfyUI/output/depth_map_00001_.png"
    
    shutil.copy(sketch, input_dir / "front.jpg")
    shutil.copy(seg_map, input_dir / "seg_map.png")
    shutil.copy(depth_map, input_dir / "depth_map.png")
    
    print("=" * 60)
    print("ComfyUI Render v5 - Regional IP-Adapter with Attention Masks")
    print("=" * 60)
    print("\nRegions with masks:")
    print("  - Floor (mask_floor.png)")
    print("  - Vanity (mask_vanity.png)")
    print("  - Wall (mask_wall.png)")
    
    # Create workflow
    prompt = create_v5_workflow(seed=42)
    
    # Save workflow
    log_dir = Path.home() / ".openclaw/workspace/logs/comfyui"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"v5_{int(time.time())}.json", "w") as f:
        json.dump(prompt, f, indent=2)
    
    # Queue
    print("\nQueuing render...")
    result = queue_prompt(prompt)
    
    if 'error' in result:
        print(f"\nError: {json.dumps(result, indent=2)}")
        return 1
    
    prompt_id = result.get('prompt_id')
    print(f"Prompt ID: {prompt_id}")
    
    # Wait
    print("\nRendering (SDXL + 3x Regional IP-Adapter, 50 steps, ETA ~40-50 min)...")
    history = wait_for_completion(prompt_id)
    
    if history:
        status = history.get('status', {}).get('status_str')
        if status == 'error':
            print(f"\n❌ Error during rendering")
            return 1
        
        outputs = history.get('outputs', {})
        for node_id, output in outputs.items():
            if 'images' in output:
                for img in output['images']:
                    print(f"\n✅ Output: ~/ComfyUI/output/{img['filename']}")
        return 0
    else:
        print("\n❌ Timeout")
        return 1

if __name__ == "__main__":
    sys.exit(main())
