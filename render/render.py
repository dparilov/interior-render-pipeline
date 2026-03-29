#!/usr/bin/env python3
"""
IRP Delta - Canonical Render Script

Renders a bundle using ComfyUI API.
"""

import argparse
import json
import requests
from pathlib import Path


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


def render(bundle_path: Path, host: str = "127.0.0.1", port: int = 8188) -> str:
    """Submit workflow to ComfyUI and return prompt ID."""
    
    manifest = load_manifest(bundle_path)
    workflow = build_workflow(manifest, bundle_path)
    
    url = f"http://{host}:{port}/prompt"
    response = requests.post(url, json=workflow)
    response.raise_for_status()
    
    result = response.json()
    return result.get("prompt_id")


def main():
    parser = argparse.ArgumentParser(description="IRP Delta Renderer")
    parser.add_argument("bundle", type=Path, help="Path to bundle directory")
    parser.add_argument("--host", default="127.0.0.1", help="ComfyUI host")
    parser.add_argument("--port", type=int, default=8188, help="ComfyUI port")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    if not args.bundle.exists():
        print(f"Error: Bundle not found: {args.bundle}")
        return 1
    
    try:
        prompt_id = render(args.bundle, args.host, args.port)
        print(f"Submitted: {prompt_id}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
