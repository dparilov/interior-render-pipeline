#!/usr/bin/env python3
"""
Generate region masks from sketch using SAM (Segment Anything Model)
Outputs: floor_mask.png, wall_mask.png, vanity_mask.png, etc.
"""

import json
import requests
import time
import sys
import os
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

def create_mask_workflow(input_image):
    """Create workflow to generate segmentation masks using SAM"""
    
    image_name = os.path.basename(input_image)
    
    prompt = {
        # Load sketch
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name}
        },
        
        # SAM Loader
        "2": {
            "class_type": "SAMLoader",
            "inputs": {
                "model_name": "sam_vit_b_01ec64.pth",
                "device_mode": "AUTO"
            }
        },
        
        # SAM Detector - Floor region (bottom of image)
        "3": {
            "class_type": "SAMDetectorCombined",
            "inputs": {
                "sam_model": ["2", 0],
                "segs": ["10", 0],  # from bbox detector
                "image": ["1", 0],
                "detection_hint": "center-1",
                "dilation": 0,
                "threshold": 0.93,
                "bbox_expansion": 0,
                "mask_hint_threshold": 0.7,
                "mask_hint_use_negative": "False"
            }
        },
        
        # Use Interior Design Segmentator for automatic segmentation
        "4": {
            "class_type": "Control Items",
            "inputs": {
                "window": True,
                "door": True,
                "staircase": False,
                "columns": False
            }
        },
        
        "5": {
            "class_type": "Interior Design Segmentator", 
            "inputs": {
                "image": ["1", 0],
                "control_items": ["4", 0]
            }
        },
        
        # Save segmentation map
        "6": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["5", 0],
                "filename_prefix": "segmentation_map"
            }
        },
        
        # Preview mask
        "7": {
            "class_type": "MaskPreview",
            "inputs": {
                "mask": ["5", 1]
            }
        },
        
        # Also get Depth map for reference
        "8": {
            "class_type": "DownloadAndLoadDepthAnythingV2Model",
            "inputs": {
                "model": "depth_anything_v2_vitl_fp32.safetensors",
                "precision": "auto"
            }
        },
        "9": {
            "class_type": "DepthAnything_V2",
            "inputs": {
                "da_model": ["8", 0],
                "images": ["1", 0]
            }
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": "depth_map"
            }
        }
    }
    
    return prompt

def queue_prompt(prompt):
    """Send prompt to ComfyUI queue"""
    data = {"prompt": prompt}
    response = requests.post(f"{COMFYUI_API}/prompt", json=data)
    return response.json()

def wait_for_completion(prompt_id, timeout=600):
    """Wait for prompt to complete"""
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
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    
    # Copy to input folder
    import shutil
    dest = Path.home() / "ComfyUI/input/front.jpg"
    if not dest.exists():
        shutil.copy(sketch_path, dest)
    
    print("=" * 60)
    print("Generating Region Masks from Sketch")
    print("=" * 60)
    print(f"Input: {sketch_path}")
    
    # Create simplified workflow - just segmentation + depth
    prompt = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        "2": {
            "class_type": "Control Items",
            "inputs": {
                "window": True,
                "door": True,
                "staircase": False,
                "columns": False
            }
        },
        "3": {
            "class_type": "Interior Design Segmentator", 
            "inputs": {
                "image": ["1", 0],
                "control_items": ["2", 0]
            }
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["3", 0],
                "filename_prefix": "seg_map"
            }
        },
        "5": {
            "class_type": "DownloadAndLoadDepthAnythingV2Model",
            "inputs": {
                "model": "depth_anything_v2_vitl_fp32.safetensors",
                "precision": "auto"
            }
        },
        "6": {
            "class_type": "DepthAnything_V2",
            "inputs": {
                "da_model": ["5", 0],
                "images": ["1", 0]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "depth_map"
            }
        }
    }
    
    print("\nQueuing mask generation...")
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
                    print(f"Output: ~/ComfyUI/output/{img['filename']}")
        print("\n✅ Masks generated!")
        return 0
    else:
        print("\n❌ Failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
