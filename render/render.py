#!/usr/bin/env python3
"""
IRP Delta - Canonical Render Script

Renders a bundle using ComfyUI API with experiment tracking.
"""

import argparse
import json
import time
import requests
from pathlib import Path

from experiment import Experiment, create_experiment


def load_manifest(bundle_path: Path) -> dict:
    """Load and validate bundle manifest."""
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {bundle_path}")
    
    manifest = json.loads(manifest_path.read_text())
    
    # Validate required fields
    required = ["version", "base_image", "image_size", "entities"]
    for field in required:
        if field not in manifest:
            raise ValueError(f"Missing required field: {field}")
    
    return manifest


def build_workflow(manifest: dict, bundle_path: Path) -> dict:
    """Build ComfyUI workflow from manifest."""
    
    # Load base workflow
    workflow_path = Path(__file__).parent / "workflow.json"
    workflow = json.loads(workflow_path.read_text())
    prompt = workflow["prompt"]
    
    # Set image size from manifest
    width = manifest["image_size"]["width"]
    height = manifest["image_size"]["height"]
    prompt["empty_latent"]["inputs"]["width"] = width
    prompt["empty_latent"]["inputs"]["height"] = height
    
    # Set beauty path
    beauty_path = str(bundle_path / manifest["base_image"])
    prompt["load_beauty"]["inputs"]["image"] = beauty_path
    
    # Build positive prompt from entities
    entity_prompts = []
    for entity in manifest["entities"]:
        if entity.get("prompt"):
            entity_prompts.append(f"{entity['name'].upper()}: {entity['prompt']}")
    
    base_prompt = "photorealistic interior photograph, professional architectural photography, 8k uhd"
    full_prompt = base_prompt + "\n\n" + "\n".join(entity_prompts)
    prompt["positive"]["inputs"]["text"] = full_prompt
    
    # Use SketchUp depth map instead of neural estimation
    if manifest.get("depth_map"):
        depth_path = str(bundle_path / manifest["depth_map"])
        prompt["load_depth"] = {
            "class_type": "LoadImage",
            "inputs": {"image": depth_path}
        }
        # Replace DepthAnything preprocessor with direct depth load
        if "depth_preprocess" in prompt:
            del prompt["depth_preprocess"]
        prompt["apply_controlnet_depth"]["inputs"]["image"] = ["load_depth", 0]
    
    # Use boundary mask for latent masking (no generation outside room)
    if manifest.get("boundary_mask"):
        boundary_path = str(bundle_path / manifest["boundary_mask"])
        prompt["load_boundary"] = {
            "class_type": "LoadImageMask",
            "inputs": {"image": boundary_path, "channel": "red"}
        }
        prompt["set_latent_mask"] = {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": ["empty_latent", 0],
                "mask": ["load_boundary", 0]
            }
        }
        # Update sampler to use masked latent
        prompt["sampler"]["inputs"]["latent_image"] = ["set_latent_mask", 0]
    
    # Add IPAdapters for entities with references
    last_model = "checkpoint"
    for i, entity in enumerate(manifest["entities"]):
        if entity.get("render_mode") != "regional_ipadapter":
            continue
        if not entity.get("reference"):
            continue
        
        ref_path = str(bundle_path / entity["reference"])
        mask_path = str(bundle_path / entity["mask"])
        weight = entity.get("ipadapter_weight", 0.5)
        
        # Load reference
        ref_node = f"load_ref_{entity['name']}"
        prompt[ref_node] = {
            "class_type": "LoadImage",
            "inputs": {"image": ref_path}
        }
        
        # Load mask
        mask_node = f"load_mask_{entity['name']}"
        prompt[mask_node] = {
            "class_type": "LoadImageMask",
            "inputs": {"image": mask_path, "channel": "red"}
        }
        
        # Apply IPAdapter
        ipadapter_node = f"ipadapter_{entity['name']}"
        prompt[ipadapter_node] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": [last_model, 0],
                "ipadapter": ["ipadapter_model", 0],
                "image": [ref_node, 0],
                "weight": weight,
                "weight_type": "ease in-out",
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
                "start_at": 0.0,
                "end_at": 0.9,
                "attn_mask": [mask_node, 0]
            }
        }
        last_model = ipadapter_node
    
    # Connect last IPAdapter to sampler
    if last_model != "checkpoint":
        prompt["sampler"]["inputs"]["model"] = [last_model, 0]
    
    return workflow


def render(bundle_path: Path, host: str = "127.0.0.1", port: int = 8188, 
            seed: int = 42, track: bool = True) -> dict:
    """Submit workflow to ComfyUI with experiment tracking."""
    
    manifest = load_manifest(bundle_path)
    workflow = build_workflow(manifest, bundle_path)
    
    # Override seed if specified
    if "sampler" in workflow.get("prompt", workflow):
        workflow["prompt"]["sampler"]["inputs"]["seed"] = seed
    
    # Create experiment
    exp = None
    if track:
        exp = create_experiment(bundle_path)
        exp.log_params({
            "seed": seed,
            "host": host,
            "port": port,
            "canny_strength": 0.8,
            "depth_strength": 0.9,
            "steps": 50
        })
        exp.log_workflow(workflow)
        exp.log_bundle()
    
    # Submit to ComfyUI
    start_time = time.time()
    url = f"http://{host}:{port}/prompt"
    response = requests.post(url, json=workflow)
    response.raise_for_status()
    
    result = response.json()
    
    if exp:
        exp.log_comfyui_response(result)
    
    return {
        "prompt_id": result.get("prompt_id"),
        "experiment_id": exp.exp_id if exp else None,
        "experiment_dir": str(exp.exp_dir) if exp else None
    }


def main():
    parser = argparse.ArgumentParser(description="IRP Delta Renderer")
    parser.add_argument("bundle", type=Path, help="Path to bundle directory")
    parser.add_argument("--host", default="127.0.0.1", help="ComfyUI host")
    parser.add_argument("--port", type=int, default=8188, help="ComfyUI port")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-track", action="store_true", help="Disable experiment tracking")
    
    args = parser.parse_args()
    
    if not args.bundle.exists():
        print(f"Error: Bundle not found: {args.bundle}")
        return 1
    
    try:
        result = render(args.bundle, args.host, args.port, 
                       seed=args.seed, track=not args.no_track)
        print(f"Submitted: {result['prompt_id']}")
        if result.get('experiment_id'):
            print(f"Experiment: {result['experiment_id']}")
            print(f"Tracking: {result['experiment_dir']}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
