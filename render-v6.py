#!/usr/bin/env python3
"""
Render v6 - Regional IP-Adapter with verified masks
"""
import requests
import json
import time
import shutil
from pathlib import Path

COMFYUI_API = "http://127.0.0.1:8188"

# Paths
INPUT_DIR = Path.home() / "ComfyUI/input"
OUTPUT_DIR = Path.home() / "ComfyUI/output"
REFS_DIR = INPUT_DIR / "bathroom_masha/референсы"
MASKS_DIR = INPUT_DIR / "masks_final"

# Create masks_final directory with best masks
MASKS_DIR.mkdir(exist_ok=True)

# Final masks from verification
FINAL_MASKS = {
    "mirror": ("sam_mirror_00001_.png", OUTPUT_DIR),
    "basket": ("sam_basket_00001_.png", OUTPUT_DIR),
    "towel_warmer": ("sam_towel_warmer_00001_.png", OUTPUT_DIR),
    "window": ("sam_window_iter2.png", INPUT_DIR / "sam_iter"),
    "faucet": ("sam_faucet_iter2.png", INPUT_DIR / "sam_iter"),
    "floor": ("sam_floor_00001_.png", OUTPUT_DIR),
    "vanity": ("mask_vanity.png", INPUT_DIR / "masks"),
    "bathtub_screen": ("sam_bathtub_screen_iter2.png", INPUT_DIR / "sam_iter"),
    "wall": ("mask_wall.png", INPUT_DIR / "masks"),
    "bathtub": ("mask_bathtub.png", INPUT_DIR / "masks"),
}

# Copy masks to masks_final
print("Copying best masks to masks_final/")
for name, (filename, src_dir) in FINAL_MASKS.items():
    src = src_dir / filename
    dst = MASKS_DIR / f"mask_{name}.png"
    if src.exists():
        shutil.copy(src, dst)
        print(f"  {name}: OK")
    else:
        print(f"  {name}: NOT FOUND ({src})")

# References from ТЗ
REFERENCES = {
    "floor": "floor_tiles.jpg",
    "wall": "wall_tiles.png",
    "vanity": "vanity.jpg",
    "mirror": "mirror.jpg",
    "bathtub": "bathtub.jpg",
    "bathtub_screen": "wall_tiles.png",  # Same as wall
    "basket": "basket.jpg",
    "towel_warmer": "towel_warmer.jpg",
    "faucet": "faucet.jpg",
    # window has no reference
}

# Copy references
refs_input = INPUT_DIR / "refs"
refs_input.mkdir(exist_ok=True)
print("\nCopying references to input/refs/")
for name, ref in REFERENCES.items():
    src = REFS_DIR / ref
    dst = refs_input / ref
    if src.exists() and not dst.exists():
        shutil.copy(src, dst)
        print(f"  {ref}: OK")

# Copy sketch
shutil.copy(INPUT_DIR / "bathroom_masha/скетчи/front.jpg", INPUT_DIR / "front.jpg")
print("\nSketch copied to input/front.jpg")

# Build workflow
def build_workflow(seed=42):
    prompt = {
        # === INPUTS ===
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        
        # Canny preprocessing
        "2": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },
        
        # Depth (use existing)
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": "v6_depth_00001_.png"}  # From earlier segmentation
        },
        
        # === MODEL ===
        "10": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        
        # === PROMPTS ===
        "11": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["10", 1],
                "text": """A photorealistic modern bathroom interior, 8K resolution, warm natural lighting from small window.
Dark charcoal gray floating vanity cabinet with white ceramic sink.
White glossy wavy textured wall tiles in vertical pattern.
Blue and white geometric patterned floor tiles, Mediterranean style.
White bathtub on right side with tiled front panel.
Chrome faucet and fixtures.
Rectangular mirror with LED backlight above vanity.
White vertical towel warmer on left wall.
Woven rattan laundry basket.
Magazine quality interior photo, Architectural Digest style, clear textures, visible tile grout."""
            }
        },
        "12": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["10", 1],
                "text": """low quality, blurry, watermark, text, brass faucet, gold fixtures, 
black towel warmer, chrome towel warmer, white vanity, wooden vanity, 
beige floor tiles, horizontal wall tiles, cartoon, anime, 3D render look"""
            }
        },
        
        # === CONTROLNET CANNY ===
        "20": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        "21": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["11", 0],
                "negative": ["12", 0],
                "control_net": ["20", 0],
                "image": ["2", 0],
                "strength": 0.7,
                "start_percent": 0,
                "end_percent": 0.8
            }
        },
        
        # === CONTROLNET DEPTH ===
        "22": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-depth-sdxl.safetensors"}
        },
        "23": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["21", 0],
                "negative": ["21", 1],
                "control_net": ["22", 0],
                "image": ["3", 0],
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 0.6
            }
        },
        
        # === IP-ADAPTER SETUP ===
        "30": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        },
        "31": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        },
    }
    
    # Add IP-Adapters for each element with mask
    node_id = 100
    prev_model = "10"  # Start from checkpoint
    
    elements_with_refs = [
        ("floor", "floor_tiles.jpg", 0.5),
        ("wall", "wall_tiles.png", 0.5),
        ("vanity", "vanity.jpg", 0.6),  # Critical
        ("mirror", "mirror.jpg", 0.4),
        ("bathtub", "bathtub.jpg", 0.4),
        ("bathtub_screen", "wall_tiles.png", 0.4),
        ("basket", "basket.jpg", 0.35),
        ("towel_warmer", "towel_warmer.jpg", 0.5),  # Critical
        ("faucet", "faucet.jpg", 0.4),
    ]
    
    for name, ref, weight in elements_with_refs:
        # Load reference
        ref_node = str(node_id)
        prompt[ref_node] = {
            "class_type": "LoadImage",
            "inputs": {"image": f"refs/{ref}"}
        }
        node_id += 1
        
        # Load mask
        mask_load = str(node_id)
        prompt[mask_load] = {
            "class_type": "LoadImage",
            "inputs": {"image": f"masks_final/mask_{name}.png"}
        }
        node_id += 1
        
        # Convert to mask
        mask_conv = str(node_id)
        prompt[mask_conv] = {
            "class_type": "ImageToMask",
            "inputs": {"image": [mask_load, 0], "channel": "red"}
        }
        node_id += 1
        
        # IP-Adapter with attention mask
        ipa_node = str(node_id)
        prompt[ipa_node] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": [prev_model, 0],
                "ipadapter": ["31", 0],
                "clip_vision": ["30", 0],
                "image": [ref_node, 0],
                "weight": weight,
                "weight_type": "style transfer",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.6,
                "embeds_scaling": "V only",
                "attn_mask": [mask_conv, 0]
            }
        }
        prev_model = ipa_node
        node_id += 1
    
    # === SAMPLER ===
    prompt["200"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
    }
    
    prompt["201"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": [prev_model, 0],
            "positive": ["23", 0],
            "negative": ["23", 1],
            "latent_image": ["200", 0],
            "seed": seed,
            "steps": 50,
            "cfg": 7.5,
            "sampler_name": "dpmpp_2m_sde",
            "scheduler": "karras",
            "denoise": 1.0
        }
    }
    
    prompt["202"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["201", 0], "vae": ["10", 2]}
    }
    
    prompt["203"] = {
        "class_type": "SaveImage",
        "inputs": {"images": ["202", 0], "filename_prefix": "bathroom_v6"}
    }
    
    return prompt

# Queue and run
print("\n" + "=" * 60)
print("RENDER V6 - Regional IP-Adapter")
print("=" * 60)

workflow = build_workflow(seed=42)

# Save workflow for debugging
log_dir = Path.home() / ".openclaw/workspace/logs/comfyui"
log_dir.mkdir(parents=True, exist_ok=True)
with open(log_dir / f"v6_{int(time.time())}.json", "w") as f:
    json.dump(workflow, f, indent=2)
print(f"Workflow saved to {log_dir}")

print("\nQueuing render...")
response = requests.post(f"{COMFYUI_API}/prompt", json={"prompt": workflow})
result = response.json()

if 'error' in result:
    print(f"Error: {result}")
    if 'node_errors' in result:
        for node, err in result['node_errors'].items():
            print(f"  Node {node}: {err}")
else:
    prompt_id = result.get('prompt_id')
    print(f"Prompt ID: {prompt_id}")
    print("Rendering... (this will take ~40-60 minutes on CPU)")
    
    # Monitor progress
    start_time = time.time()
    while True:
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        
        try:
            queue_resp = requests.get(f"{COMFYUI_API}/queue", timeout=5)
            queue = queue_resp.json()
            running = len(queue.get('queue_running', []))
            pending = len(queue.get('queue_pending', []))
            
            if running == 0 and pending == 0:
                print(f"\n[{mins:02d}:{secs:02d}] Done!")
                break
            
            print(f"[{mins:02d}:{secs:02d}] Rendering...", end="\r")
        except:
            print(f"[{mins:02d}:{secs:02d}] (checking...)", end="\r")
        
        time.sleep(10)
    
    # Find output
    outputs = list(OUTPUT_DIR.glob("bathroom_v6*.png"))
    if outputs:
        latest = max(outputs, key=lambda p: p.stat().st_mtime)
        print(f"\nOutput: {latest}")
        print(f"Size: {latest.stat().st_size / 1024:.1f} KB")
