#!/usr/bin/env python3
"""
ComfyUI Render v3 - SDXL + Canny + Depth + IP-Adapter per region
Based on research: parallel IP-Adapter with attention masks
"""

import json
import requests
import time
import sys
import os
import shutil
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

def parse_tz(tz_path):
    """Parse ТЗ.md and extract elements with references"""
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
        
        elif line.startswith('- **КРИТИЧНО:**'):
            current['critical'] = 'ДА' in line
    
    if current.get('name'):
        elements.append(current)
    
    return elements

def create_workflow(sketch_path, tz_elements, seed=42, steps=50):
    """Create SDXL + Canny + Depth + IP-Adapter workflow"""
    
    image_name = os.path.basename(sketch_path)
    
    # Build English prompt from ТЗ
    prompt_parts = ["A modern compact bathroom with warm natural lighting, photorealistic interior photograph, 8K resolution"]
    
    for el in tz_elements:
        if el.get('description'):
            # Simple RU→EN translation for key terms
            desc = el['description']
            desc = desc.replace('СИНИЙ', 'blue').replace('БЕЛЫЙ', 'white')
            desc = desc.replace('ТЁМНО-СЕРЫЙ', 'dark charcoal').replace('ХРОМ', 'chrome')
            desc = desc.replace('керамическая', 'ceramic').replace('глянцевая', 'glossy')
            prompt_parts.append(desc)
    
    positive_prompt = ". ".join(prompt_parts[:5])  # Limit to avoid too long
    
    negative_prompt = "low resolution, blurry, watermark, text, deformed, bad anatomy, brass faucet, gold faucet, black towel warmer, white vanity"
    
    # Main workflow
    prompt = {
        # === INPUT ===
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        
        # === PREPROCESSING ===
        # Canny edge detection
        "2": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },
        
        # Depth estimation
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
                "images": ["1", 0]
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
        
        # === CONTROLNET CANNY ===
        "8": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        "9": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "control_net": ["8", 0],
                "image": ["2", 0],
                "strength": 0.7,
                "start_percent": 0,
                "end_percent": 0.8
            }
        },
        
        # === CONTROLNET DEPTH ===
        "10": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-depth-sdxl.safetensors"}
        },
        "11": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["9", 0],
                "negative": ["9", 1],
                "control_net": ["10", 0],
                "image": ["4", 0],
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 0.6
            }
        },
        
        # === IP-ADAPTER (single, for style) ===
        # We'll add regional IP-Adapter in next iteration
        # For now, just Canny + Depth
        
        # === EMPTY LATENT ===
        "12": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            }
        },
        
        # === KSAMPLER ===
        "13": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["5", 0],
                "positive": ["11", 0],
                "negative": ["11", 1],
                "latent_image": ["12", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m_sde",
                "scheduler": "karras",
                "denoise": 1.0
            }
        },
        
        # === VAE DECODE ===
        "14": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["13", 0],
                "vae": ["5", 2]
            }
        },
        
        # === SAVE ===
        "15": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["14", 0],
                "filename_prefix": "bathroom_v3"
            }
        },
        
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
        print(f"\r[{elapsed//60}:{elapsed%60:02d}] Waiting...", end="", flush=True)
        time.sleep(10)
    
    return None

def main():
    tz_path = Path.home() / "ComfyUI/input/bathroom_masha/ТЗ.md"
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    
    # Copy sketch to input
    dest = Path.home() / "ComfyUI/input/front.jpg"
    shutil.copy(sketch_path, dest)
    
    print("=" * 60)
    print("ComfyUI Render v3 - SDXL + Canny + Depth")
    print("=" * 60)
    
    # Parse ТЗ
    elements = parse_tz(tz_path)
    print(f"Found {len(elements)} elements in ТЗ")
    
    # Create workflow
    prompt, pos_prompt = create_workflow("front.jpg", elements, seed=42, steps=50)
    
    print(f"\nPrompt: {pos_prompt[:100]}...")
    
    # Save workflow
    log_dir = Path.home() / ".openclaw/workspace/logs/comfyui"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"v3_{int(time.time())}.json", "w") as f:
        json.dump(prompt, f, indent=2)
    
    # Queue
    print("\nQueuing...")
    result = queue_prompt(prompt)
    
    if 'error' in result:
        print(f"Error: {result}")
        return 1
    
    prompt_id = result.get('prompt_id')
    print(f"Prompt ID: {prompt_id}")
    
    # Wait
    print("\nRendering (SDXL, 50 steps, CPU ~30-45 min)...")
    history = wait_for_completion(prompt_id)
    
    if history:
        outputs = history.get('outputs', {})
        for node_id, output in outputs.items():
            if 'images' in output:
                for img in output['images']:
                    print(f"\n✅ Output: ~/ComfyUI/output/{img['filename']}")
        return 0
    else:
        print("\n❌ Failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
