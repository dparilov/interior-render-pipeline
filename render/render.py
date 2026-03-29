"""
IRP Render Orchestrator v1.1

Submits bundle to ComfyUI with full experiment tracking.
All parameters are extracted from actual workflow, not hardcoded.
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import sys

from validate import validate_bundle, BundleValidator
from experiment import Experiment, create_experiment


COMFYUI_URL = "http://127.0.0.1:8188"


def load_workflow(workflow_path: Path) -> Dict:
    """Load base workflow template."""
    with open(workflow_path) as f:
        return json.load(f)


def load_manifest(bundle_path: Path) -> Dict:
    """Load and return bundle manifest."""
    with open(bundle_path / "manifest.json") as f:
        return json.load(f)


def build_prompt(workflow: Dict, manifest: Dict, bundle_path: Path) -> Dict:
    """Build ComfyUI prompt from workflow template and bundle manifest.
    
    Modifies workflow in-place and returns it.
    """
    prompt = workflow.get("prompt", workflow)
    
    # Set image size from manifest
    width = manifest["image_size"]["width"]
    height = manifest["image_size"]["height"]
    
    if "empty_latent" in prompt:
        prompt["empty_latent"]["inputs"]["width"] = width
        prompt["empty_latent"]["inputs"]["height"] = height
    
    # Set beauty path
    beauty_path = str(bundle_path / manifest["base_image"])
    if "load_beauty" in prompt:
        prompt["load_beauty"]["inputs"]["image"] = beauty_path
    
    # Use SketchUp depth map (ground truth)
    if manifest.get("depth_map"):
        depth_path = str(bundle_path / manifest["depth_map"])
        
        # Add or update depth loader
        prompt["load_depth"] = {
            "class_type": "LoadImage",
            "inputs": {"image": depth_path}
        }
        
        # Remove neural depth preprocessor if exists
        if "depth_preprocess" in prompt:
            del prompt["depth_preprocess"]
        
        # Point ControlNet to loaded depth
        if "apply_controlnet_depth" in prompt:
            prompt["apply_controlnet_depth"]["inputs"]["image"] = ["load_depth", 0]
    
    # Use boundary mask for latent masking
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
        if "sampler" in prompt:
            prompt["sampler"]["inputs"]["latent_image"] = ["set_latent_mask", 0]
    
    # Build positive prompt from entities
    entity_prompts = []
    for entity in manifest.get("entities", []):
        if entity.get("prompt"):
            entity_prompts.append(f"{entity['name'].upper()}: {entity['prompt']}")
    
    base_prompt = "photorealistic interior photograph, professional architectural photography, 8k uhd, natural lighting"
    
    # Add room summary from technical spec if available
    tech_spec = manifest.get("technical_spec", {})
    if tech_spec.get("summary"):
        base_prompt += f", {tech_spec['summary']}"
    
    full_prompt = base_prompt + "\n\n" + "\n".join(entity_prompts)
    
    if "positive" in prompt:
        prompt["positive"]["inputs"]["text"] = full_prompt
    
    # Add IPAdapters for entities with references
    last_model = "checkpoint"
    for i, entity in enumerate(manifest.get("entities", [])):
        if entity.get("render_mode") != "regional_ipadapter":
            continue
        if not entity.get("reference"):
            continue
        
        ref_path = str(bundle_path / entity["reference"])
        mask_path = str(bundle_path / entity["mask"])
        weight = entity.get("ipadapter_weight", 0.5)
        
        # Skip if reference file doesn't exist
        if not Path(ref_path).exists():
            print(f"Warning: Reference not found for {entity['name']}: {ref_path}")
            continue
        
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
                "end_at": 0.8,
                "attn_mask": [mask_node, 0]
            }
        }
        
        last_model = ipadapter_node
    
    # Update final model connection
    if last_model != "checkpoint":
        for node_name in ["apply_controlnet_canny", "apply_controlnet_depth"]:
            if node_name in prompt:
                # Find which node uses checkpoint and update
                pass
        
        if "sampler" in prompt:
            prompt["sampler"]["inputs"]["model"] = [last_model, 0]
    
    return workflow


def submit_prompt(prompt: Dict, experiment: Optional[Experiment] = None) -> Dict:
    """Submit prompt to ComfyUI and return response."""
    try:
        response = requests.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": prompt},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if experiment and result.get("prompt_id"):
            experiment.log_submit(result["prompt_id"])
        
        return result
    except requests.exceptions.RequestException as e:
        if experiment:
            experiment.fail(str(e))
        raise


def poll_completion(prompt_id: str, timeout_seconds: int = 7200, poll_interval: int = 10) -> Optional[Dict]:
    """Poll ComfyUI history until prompt completes or times out.
    
    Args:
        prompt_id: The prompt ID to wait for
        timeout_seconds: Max wait time (default 2 hours for CPU render)
        poll_interval: Seconds between polls
    
    Returns:
        History entry dict or None if timeout/error
    """
    import time
    start = time.time()
    
    while time.time() - start < timeout_seconds:
        try:
            response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    entry = history[prompt_id]
                    # Check if completed
                    if entry.get("status", {}).get("completed", False):
                        return entry
                    # Check for error
                    if entry.get("status", {}).get("status_str") == "error":
                        return entry
        except requests.exceptions.RequestException:
            pass  # Retry on network errors
        
        time.sleep(poll_interval)
    
    return None  # Timeout


def get_output_images(history_entry: Dict, comfyui_output_dir: Path = None) -> List[Path]:
    """Extract output image paths from history entry."""
    if comfyui_output_dir is None:
        comfyui_output_dir = Path.home() / "ComfyUI" / "output"
    
    images = []
    outputs = history_entry.get("outputs", {})
    
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                filename = img.get("filename")
                subfolder = img.get("subfolder", "")
                if filename:
                    img_path = comfyui_output_dir / subfolder / filename
                    if img_path.exists():
                        images.append(img_path)
    
    return images


def render(
    bundle_path: Path,
    workflow_path: Path = None,
    experiment_name: str = "render",
    experiments_dir: Path = None,
    validate: bool = True,
    dry_run: bool = False,
    wait: bool = True,
    timeout_seconds: int = 7200
) -> Dict:
    """Main render function.
    
    Args:
        bundle_path: Path to IRP bundle
        workflow_path: Path to workflow JSON (default: render/workflow.json)
        experiment_name: Name prefix for experiment
        experiments_dir: Where to save experiment data
        validate: Whether to validate bundle first
        dry_run: If True, don't submit to ComfyUI
        wait: If True, poll until completion and save output
        timeout_seconds: Max wait time for completion (default 2h)
    
    Returns:
        Dict with prompt_id and experiment info
    """
    bundle_path = Path(bundle_path)
    
    if workflow_path is None:
        workflow_path = Path(__file__).parent / "workflow.json"
    
    if experiments_dir is None:
        experiments_dir = bundle_path / "experiments"
    
    # Create experiment
    experiment = create_experiment(experiment_name, experiments_dir)
    
    try:
        # Validate bundle
        if validate:
            print("Validating bundle...")
            is_valid, errors = validate_bundle(bundle_path)
            for error in errors:
                print(f"  {error}")
            if not is_valid:
                experiment.fail("Bundle validation failed")
                return {"error": "Bundle validation failed", "errors": errors}
            print("  ✅ Bundle valid")
        
        # Load manifest
        print("Loading manifest...")
        manifest = load_manifest(bundle_path)
        experiment.log_bundle(bundle_path, manifest)
        
        # Load and build workflow
        print("Building workflow...")
        workflow = load_workflow(workflow_path)
        workflow = build_prompt(workflow, manifest, bundle_path)
        experiment.log_workflow(workflow)
        
        # Log environment
        experiment.log_environment(
            comfyui_version="unknown",  # Could query /system_stats
            models={
                "checkpoint": workflow.get("prompt", workflow).get("checkpoint", {}).get("inputs", {}).get("ckpt_name", "unknown"),
                "ipadapter": workflow.get("prompt", workflow).get("ipadapter_model", {}).get("inputs", {}).get("ipadapter_file", "unknown")
            }
        )
        
        if dry_run:
            print("Dry run - not submitting to ComfyUI")
            experiment.complete(status="dry_run")
            return {"experiment_id": experiment.id, "dry_run": True}
        
        # Submit to ComfyUI
        print("Submitting to ComfyUI...")
        result = submit_prompt(workflow.get("prompt", workflow), experiment)
        
        prompt_id = result.get("prompt_id")
        print(f"  ✅ Submitted: {prompt_id}")
        
        if not wait:
            return {
                "prompt_id": prompt_id,
                "experiment_id": experiment.id,
                "experiment_dir": str(experiment.output_dir),
                "status": "submitted"
            }
        
        # Wait for completion
        print(f"Waiting for completion (timeout: {timeout_seconds}s)...")
        history = poll_completion(prompt_id, timeout_seconds)
        
        if history is None:
            experiment.fail("Timeout waiting for completion")
            return {
                "prompt_id": prompt_id,
                "experiment_id": experiment.id,
                "experiment_dir": str(experiment.output_dir),
                "status": "timeout"
            }
        
        if history.get("status", {}).get("status_str") == "error":
            error_msg = str(history.get("status", {}).get("messages", []))
            experiment.fail(f"ComfyUI error: {error_msg}")
            return {
                "prompt_id": prompt_id,
                "experiment_id": experiment.id,
                "experiment_dir": str(experiment.output_dir),
                "status": "error",
                "error": error_msg
            }
        
        # Get output images
        output_images = get_output_images(history)
        if output_images:
            # Save first image to experiment
            experiment.log_output(output_images[0])
            print(f"  ✅ Output saved: {output_images[0].name}")
        
        experiment.complete(status="success")
        print(f"  ✅ Experiment complete: {experiment.id}")
        
        return {
            "prompt_id": prompt_id,
            "experiment_id": experiment.id,
            "experiment_dir": str(experiment.output_dir),
            "status": "success",
            "output_images": [str(p) for p in output_images]
        }
        
    except Exception as e:
        experiment.fail(str(e))
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render.py <bundle_path> [--dry-run] [--no-validate] [--no-wait]")
        sys.exit(1)
    
    bundle_path = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    validate = "--no-validate" not in sys.argv
    wait = "--no-wait" not in sys.argv
    
    result = render(
        bundle_path=bundle_path,
        dry_run=dry_run,
        validate=validate,
        wait=wait
    )
    
    print(json.dumps(result, indent=2))
