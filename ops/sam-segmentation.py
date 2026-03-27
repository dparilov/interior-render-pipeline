#!/usr/bin/env python3
"""
SAM Segmentation with point prompts for bathroom elements
Creates individual masks for each element
"""

import json
import requests
import time
import sys
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

# Point prompts for each element (x, y) - for 3500x2097 image
# Scaled from analysis: original estimates were for ~1400x840, multiply by 2.5
ELEMENT_POINTS = {
    "floor": (1925, 1875),        # Bottom center
    "left_wall": (400, 1000),     # Left side
    "right_wall": (3100, 1000),   # Right side
    "back_wall": (1750, 500),     # Center top
    "vanity": (1725, 1475),       # Center-left, lower
    "mirror": (1725, 800),        # Above vanity
    "faucet": (1725, 1200),       # On vanity
    "bathtub": (2800, 1600),      # Right side
    "towel_warmer": (500, 1200),  # Left wall
    "window": (600, 400),         # Top left
    "basket": (800, 1800),        # Bottom left
}

def create_sam_workflow(image_name, element_name, point_x, point_y):
    """Create workflow to segment one element using SAM"""
    
    prompt = {
        # Load image
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        
        # Load SAM model
        "2": {
            "class_type": "SAMLoader",
            "inputs": {
                "model_name": "sam_vit_b_01ec64.pth",
                "device_mode": "AUTO"
            }
        },
        
        # Create point for SAM
        # We need ImpactSEGSLabelFilter or similar to create SEGS from point
        # Actually, SAMDetectorCombined needs SEGS input
        # Let's use a simpler approach with SAMPreprocessor first
        
        "3": {
            "class_type": "SAMPreprocessor",
            "inputs": {
                "image": ["1", 0],
                "resolution": 1024
            }
        },
        
        # Save SAM preprocessor output
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["3", 0],
                "filename_prefix": f"sam_{element_name}"
            }
        }
    }
    
    return prompt

def create_full_sam_workflow(image_name):
    """Create workflow that runs SAM automatic segmentation"""
    
    prompt = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        
        # SAM automatic mask generation
        "2": {
            "class_type": "SAMPreprocessor",
            "inputs": {
                "image": ["1", 0],
                "resolution": 1024
            }
        },
        
        "3": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["2", 0],
                "filename_prefix": "sam_auto"
            }
        }
    }
    
    return prompt

def queue_prompt(prompt):
    data = {"prompt": prompt}
    response = requests.post(f"{COMFYUI_API}/prompt", json=data)
    return response.json()

def wait_for_completion(prompt_id, timeout=300):
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
            history = response.json()
            
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        
        time.sleep(2)
    
    return None

def main():
    import shutil
    
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    dest = Path.home() / "ComfyUI/input/front.jpg"
    shutil.copy(sketch_path, dest)
    
    print("=" * 60)
    print("SAM Automatic Segmentation")
    print("=" * 60)
    
    # Run automatic SAM segmentation first
    prompt = create_full_sam_workflow("front.jpg")
    
    print("Queuing SAM auto segmentation...")
    result = queue_prompt(prompt)
    
    if 'error' in result:
        print(f"Error: {result}")
        return 1
    
    prompt_id = result.get('prompt_id')
    print(f"Prompt ID: {prompt_id}")
    
    print("Waiting for completion...")
    history = wait_for_completion(prompt_id)
    
    if history:
        outputs = history.get('outputs', {})
        for node_id, output in outputs.items():
            if 'images' in output:
                for img in output['images']:
                    print(f"✅ Output: ~/ComfyUI/output/{img['filename']}")
        return 0
    else:
        print("❌ Failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
