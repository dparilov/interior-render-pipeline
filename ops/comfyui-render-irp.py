#!/usr/bin/env python3
"""
IRP ComfyUI Renderer v1
Interior Render Pipeline - читает manifest.json и рендерит с масками

Usage:
    python3 comfyui-render-irp.py --bundle ~/bundle --steps 20 --output bathroom_irp
"""

import argparse
import json
import os
import sys
import requests
from PIL import Image

COMFYUI_URL = "http://127.0.0.1:8188"

def load_manifest(bundle_dir):
    """Load manifest.json from bundle directory"""
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"❌ manifest.json not found in {bundle_dir}")
        sys.exit(1)
    
    with open(manifest_path) as f:
        return json.load(f)

def check_comfyui():
    """Check if ComfyUI is running"""
    try:
        r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return r.status_code == 200
    except:
        return False

def get_relative_path(bundle_dir, path):
    """Convert bundle path to ComfyUI input-relative path"""
    # Assume bundle is in ~/ComfyUI/input/
    comfy_input = os.path.expanduser("~/ComfyUI/input")
    full_path = os.path.join(bundle_dir, path)
    
    if os.path.exists(full_path):
        return os.path.relpath(full_path, comfy_input)
    return None

def analyze_mask(mask_path):
    """Analyze mask coverage"""
    if not os.path.exists(mask_path):
        return 0.0
    
    img = Image.open(mask_path).convert('L')
    white_pixels = sum(1 for p in img.getdata() if p > 128)
    total_pixels = img.size[0] * img.size[1]
    return 100.0 * white_pixels / total_pixels

def build_prompt_from_manifest(manifest):
    """Build positive prompt from entity prompts"""
    parts = ["modern bathroom interior, photorealistic, 8k, professional photography"]
    
    for entity in manifest['entities']:
        if entity.get('prompt'):
            parts.append(entity['prompt'])
    
    return ", ".join(parts)

def build_workflow(manifest, bundle_dir, args):
    """Build ComfyUI workflow from manifest"""
    
    comfy_input = os.path.expanduser("~/ComfyUI/input")
    
    # Base workflow
    workflow = {
        # Checkpoint
        "checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}
        },
        
        # VAE
        "vae": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "sdxl_vae.safetensors"}
        },
        
        # Load beauty image (base sketch)
        "load_beauty": {
            "class_type": "LoadImage",
            "inputs": {"image": get_relative_path(bundle_dir, manifest['images']['beauty'])}
        },
        
        # Canny edge detection
        "canny_preprocess": {
            "class_type": "Canny",
            "inputs": {
                "image": ["load_beauty", 0],
                "low_threshold": 0.1,
                "high_threshold": 0.4
            }
        },
        
        # ControlNet
        "controlnet_canny": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "control-lora-canny-rank256.safetensors"}
        },
        
        # Positive prompt
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": build_prompt_from_manifest(manifest)
            }
        },
        
        # Negative prompt
        "negative": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": "cartoon, anime, sketch, drawing, painting, blurry, low quality, watermark, text, oversaturated"
            }
        },
        
        # Apply ControlNet
        "apply_controlnet": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["positive", 0],
                "negative": ["negative", 0],
                "control_net": ["controlnet_canny", 0],
                "image": ["canny_preprocess", 0],
                "strength": 0.6,
                "start_percent": 0.0,
                "end_percent": 0.8
            }
        },
        
        # Empty latent
        "empty_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": manifest['resolution'][0],
                "height": manifest['resolution'][1],
                "batch_size": 1
            }
        },
        
        # IP-Adapter model
        "ipadapter_model": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        },
        
        # CLIP Vision
        "clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        }
    }
    
    # Add IP-Adapters for each entity with reference and mask
    prev_model = ["checkpoint", 0]
    
    entities_with_ref = [e for e in manifest['entities'] if e.get('reference')]
    
    for entity in entities_with_ref:
        name = entity['name']
        
        mask_path = os.path.join(bundle_dir, entity['mask'])
        ref_path = os.path.join(bundle_dir, entity['reference'])
        
        if not os.path.exists(ref_path):
            print(f"  ⚠️  Reference not found: {ref_path}")
            continue
            
        if not os.path.exists(mask_path):
            print(f"  ⚠️  Mask not found: {mask_path}")
            continue
        
        coverage = analyze_mask(mask_path)
        
        # Skip tiny masks
        if coverage < 0.1:
            print(f"  ⚠️  {name}: coverage too small ({coverage:.1f}%), skipping")
            continue
        
        # Dynamic weight based on coverage
        weight = 0.6 if coverage > 5 else 0.4
        
        mask_rel = os.path.relpath(mask_path, comfy_input)
        ref_rel = os.path.relpath(ref_path, comfy_input)
        
        # Load reference
        workflow[f"load_ref_{name}"] = {
            "class_type": "LoadImage",
            "inputs": {"image": ref_rel}
        }
        
        # Load mask
        workflow[f"load_mask_{name}"] = {
            "class_type": "LoadImageMask",
            "inputs": {
                "image": mask_rel,
                "channel": "red"
            }
        }
        
        # IP-Adapter with attention mask
        workflow[f"ipadapter_{name}"] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": prev_model,
                "ipadapter": ["ipadapter_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": [f"load_ref_{name}", 0],
                "attn_mask": [f"load_mask_{name}", 0],
                "weight": weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": 0.8,
                "unfold_batch": False,
                "combine_embeds": "concat",
                "embeds_scaling": "V only"
            }
        }
        
        prev_model = [f"ipadapter_{name}", 0]
        print(f"  ✅ {name}: coverage={coverage:.1f}%, weight={weight}")
    
    # KSampler
    workflow["sampler"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": prev_model,
            "positive": ["apply_controlnet", 0],
            "negative": ["apply_controlnet", 1],
            "latent_image": ["empty_latent", 0],
            "seed": 42,
            "steps": args.steps,
            "cfg": 7.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0
        }
    }
    
    # VAE Decode
    workflow["vae_decode"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["sampler", 0],
            "vae": ["vae", 0]
        }
    }
    
    # Save
    workflow["save"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["vae_decode", 0],
            "filename_prefix": args.output
        }
    }
    
    return workflow

def submit_workflow(workflow):
    """Submit workflow to ComfyUI"""
    payload = {"prompt": workflow}
    
    r = requests.post(f"{COMFYUI_URL}/prompt", json=payload)
    
    if r.status_code != 200:
        print(f"❌ ComfyUI error: {r.status_code}")
        print(r.text)
        return None
    
    data = r.json()
    return data.get('prompt_id')

def main():
    parser = argparse.ArgumentParser(description="IRP ComfyUI Renderer")
    parser.add_argument("--bundle", required=True, help="Path to bundle directory")
    parser.add_argument("--steps", type=int, default=20, help="Sampling steps")
    parser.add_argument("--output", default="irp_render", help="Output filename prefix")
    args = parser.parse_args()
    
    bundle_dir = os.path.expanduser(args.bundle)
    
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   IRP ComfyUI Renderer v1                ║")
    print("╚══════════════════════════════════════════╝")
    print()
    
    # Load manifest
    print(f"📦 Loading bundle: {bundle_dir}")
    manifest = load_manifest(bundle_dir)
    print(f"   Version: {manifest['version']}")
    print(f"   Scene: {manifest['scene_name']}")
    print(f"   Entities: {len(manifest['entities'])}")
    
    # Check ComfyUI
    if not check_comfyui():
        print("❌ ComfyUI not running!")
        sys.exit(1)
    print("✅ ComfyUI available")
    print()
    
    # Build workflow
    print("🔨 Building workflow...")
    workflow = build_workflow(manifest, bundle_dir, args)
    
    # Count IP-Adapters
    ipadapter_count = sum(1 for k in workflow.keys() if k.startswith("ipadapter_") and k != "ipadapter_model")
    print()
    print(f"📊 Workflow summary:")
    print(f"   Steps: {args.steps}")
    print(f"   Resolution: {manifest['resolution'][0]}x{manifest['resolution'][1]}")
    print(f"   IP-Adapters with masks: {ipadapter_count}")
    print()
    
    # Submit
    print("📤 Sending to ComfyUI...")
    prompt_id = submit_workflow(workflow)
    
    if prompt_id:
        print(f"🆔 Prompt ID: {prompt_id}")
        eta_minutes = args.steps * 45 / 60  # ~45s per step on CPU
        print(f"⏱️  ETA: ~{eta_minutes:.0f} minutes on CPU")
        print()
        print(f"💡 Output: ~/ComfyUI/output/{args.output}_*.png")
    else:
        print("❌ Failed to submit workflow")

if __name__ == "__main__":
    main()
