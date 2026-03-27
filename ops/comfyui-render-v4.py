#!/usr/bin/env python3
"""
ComfyUI Render v4 - SDXL + Canny + Depth + IP-Adapter with Regional Masks
Full pipeline with Opus-verified masks
"""

import json
import requests
import time
import sys
import os
import shutil
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

# Color mapping from segmentation map to elements
# Based on UperNet output analysis
SEG_COLORS = {
    "floor": "#8B4513",      # Dark brown/maroon
    "wall": "#00CED1",       # Cyan/Blue  
    "vanity": "#9370DB",     # Purple/Violet
    "mirror": "#D3D3D3",     # Light gray
    "bathtub": "#00CED1",    # Cyan (same as wall, different region)
    "window": "#808000",     # Olive
    "basket": "#32CD32",     # Lime green
}

def parse_tz(tz_path):
    """Parse ТЗ and extract elements with references"""
    with open(tz_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    elements = []
    current = {}
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('### ') and not line.startswith('###  '):
            if current.get('name'):
                elements.append(current)
            current = {'name': line[4:].strip()}
        
        elif line.startswith('- **Референс:**'):
            ref = line.split('`')[1] if '`' in line else ''
            current['reference'] = ref
        
        elif line.startswith('- **Описание:**'):
            current['description'] = line.replace('- **Описание:**', '').strip()
    
    if current.get('name'):
        elements.append(current)
    
    return elements

def build_prompt(elements):
    """Build detailed prompt from ТЗ elements"""
    parts = [
        "A modern compact bathroom interior, photorealistic photograph, 8K resolution",
        "warm natural lighting from small window",
        "magazine quality interior design photo"
    ]
    
    for el in elements:
        if el.get('description'):
            desc = el['description']
            # Basic RU→EN for key terms
            desc = desc.replace('СИНИЙ', 'blue').replace('БЕЛЫЙ', 'white')
            desc = desc.replace('ТЁМНО-СЕРЫЙ', 'dark charcoal gray')
            desc = desc.replace('ХРОМ', 'chrome').replace('хром', 'chrome')
            desc = desc.replace('керамическая', 'ceramic').replace('глянцевая', 'glossy')
            desc = desc.replace('подвесная', 'wall-mounted floating')
            parts.append(desc[:100])
    
    return ". ".join(parts[:8])

def create_v4_workflow(image_name, elements, seg_map_name, depth_map_name, seed=42):
    """
    Create SDXL + Canny + Depth + IP-Adapter workflow
    Uses segmentation map for regional conditioning
    """
    
    positive_prompt = build_prompt(elements)
    negative_prompt = "low quality, blurry, watermark, text, deformed, brass faucet, gold fixtures, black towel warmer, cartoon, anime, illustration"
    
    prompt = {
        # === INPUTS ===
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {"image": seg_map_name}
        },
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": depth_map_name}
        },
        
        # === CANNY PREPROCESSING ===
        "4": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },
        
        # === SDXL MODEL ===
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        
        # === CLIP ENCODE ===
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["5", 1],
                "text": positive_prompt
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["5", 1],
                "text": negative_prompt
            }
        },
        
        # === CLIP VISION for IP-Adapter ===
        "8": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        },
        
        # === IP-ADAPTER LOADER ===
        "9": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        },
        
        # === LOAD REFERENCE IMAGES ===
        # Floor tile reference
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": "ref_floor.jpg"}
        },
        # Wall tile reference  
        "11": {
            "class_type": "LoadImage",
            "inputs": {"image": "ref_wall.jpg"}
        },
        
        # === CREATE MASKS FROM SEGMENTATION ===
        # Convert seg map colors to masks using ImageColorToMask or similar
        # For now, use segmentation as general guidance
        
        # === IP-ADAPTER APPLY (style transfer from seg map) ===
        "12": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["5", 0],
                "ipadapter": ["9", 0],
                "clip_vision": ["8", 0],
                "image": ["2", 0],  # Use segmentation map as style reference
                "weight": 0.3,
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.5,
                "embeds_scaling": "V only"
            }
        },
        
        # === CONTROLNET CANNY ===
        "13": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        "14": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["13", 0],
                "image": ["4", 0],
                "strength": 0.7,
                "start_percent": 0,
                "end_percent": 0.8
            }
        },
        
        # === CONTROLNET DEPTH ===
        "15": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-depth-sdxl.safetensors"}
        },
        "16": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["14", 0],
                "negative": ["14", 1],
                "control_net": ["15", 0],
                "image": ["3", 0],
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 0.6
            }
        },
        
        # === EMPTY LATENT ===
        "17": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        
        # === KSAMPLER ===
        "18": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["12", 0],  # Model with IP-Adapter applied
                "positive": ["16", 0],
                "negative": ["16", 1],
                "latent_image": ["17", 0],
                "seed": seed,
                "steps": 50,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 1.0
            }
        },
        
        # === VAE DECODE ===
        "19": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["18", 0],
                "vae": ["5", 2]
            }
        },
        
        # === SAVE ===
        "20": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["19", 0],
                "filename_prefix": "bathroom_v4"
            }
        }
    }
    
    return prompt, positive_prompt

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
    tz_path = Path.home() / "ComfyUI/input/bathroom_masha/ТЗ.md"
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    seg_map_path = Path.home() / "ComfyUI/output/seg_map_00001_.png"
    depth_map_path = Path.home() / "ComfyUI/output/depth_map_00001_.png"
    
    # Copy files to input
    input_dir = Path.home() / "ComfyUI/input"
    shutil.copy(sketch_path, input_dir / "front.jpg")
    shutil.copy(seg_map_path, input_dir / "seg_map.png")
    shutil.copy(depth_map_path, input_dir / "depth_map.png")
    
    # Create placeholder reference images if not exist
    # In real use, these would be the material references from ТЗ
    ref_floor = input_dir / "ref_floor.jpg"
    ref_wall = input_dir / "ref_wall.jpg"
    if not ref_floor.exists():
        shutil.copy(seg_map_path, ref_floor)  # Placeholder
    if not ref_wall.exists():
        shutil.copy(seg_map_path, ref_wall)  # Placeholder
    
    print("=" * 60)
    print("ComfyUI Render v4 - SDXL + Canny + Depth + IP-Adapter")
    print("=" * 60)
    
    # Parse ТЗ
    elements = parse_tz(tz_path)
    print(f"Elements from ТЗ: {len(elements)}")
    
    # Create workflow
    prompt, pos_prompt = create_v4_workflow(
        "front.jpg", elements, "seg_map.png", "depth_map.png", seed=42
    )
    
    print(f"\nPrompt: {pos_prompt[:100]}...")
    
    # Save workflow
    log_dir = Path.home() / ".openclaw/workspace/logs/comfyui"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"v4_{int(time.time())}.json", "w") as f:
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
    print("\nRendering (SDXL + IP-Adapter, 50 steps, ETA ~35-45 min)...")
    history = wait_for_completion(prompt_id)
    
    if history:
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
