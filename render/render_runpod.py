"""
IRP RunPod Render Client v1.0

Submits bundle to RunPod serverless ComfyUI endpoint.
Compatible with render.py experiment tracking.
"""

import json
import requests
import base64
import time
from pathlib import Path
from typing import Dict, Any, Optional
import sys

from validate import validate_bundle
from experiment import Experiment, create_experiment


def load_config() -> Dict:
    """Load RunPod config from openclaw.json."""
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    
    return {
        "api_key": config["runpod"]["apiKey"],
        "endpoint_id": config["runpod"]["endpointId"]
    }


def load_workflow(workflow_path: Path) -> Dict:
    """Load base workflow template."""
    with open(workflow_path) as f:
        return json.load(f)


def load_manifest(bundle_path: Path) -> Dict:
    """Load bundle manifest."""
    with open(bundle_path / "manifest.json") as f:
        return json.load(f)


def encode_image(path: Path) -> str:
    """Encode image to base64 for RunPod."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def build_runpod_input(workflow: Dict, manifest: Dict, bundle_path: Path) -> Dict:
    """Build RunPod input with workflow and images."""
    prompt = workflow.get("prompt", workflow)
    
    # Encode all required images
    images = {}
    
    # Beauty image
    beauty_path = bundle_path / manifest["base_image"]
    images["beauty.png"] = encode_image(beauty_path)
    
    # Depth map
    depth_path = bundle_path / manifest.get("depth_map", "depth.png")
    if depth_path.exists():
        images["depth.png"] = encode_image(depth_path)
    
    # Boundary mask
    boundary_path = bundle_path / manifest.get("boundary_mask", "boundary_mask.png")
    if boundary_path.exists():
        images["boundary_mask.png"] = encode_image(boundary_path)
    
    # Entity masks and references
    for entity in manifest.get("entities", []):
        # Mask
        mask_path = bundle_path / entity["mask"]
        if mask_path.exists():
            images[f"masks/{entity['name']}.png"] = encode_image(mask_path)
        
        # Reference
        if entity.get("reference"):
            ref_path = bundle_path / entity["reference"]
            if ref_path.exists():
                images[f"references/{entity['name']}.png"] = encode_image(ref_path)
    
    # Update workflow paths to use /input/ (ComfyUI worker convention)
    # The worker will place uploaded images there
    
    return {
        "input": {
            "workflow": prompt,
            "images": images
        }
    }


def submit_job(config: Dict, payload: Dict) -> str:
    """Submit job to RunPod and return job ID."""
    url = f"https://api.runpod.ai/v2/{config['endpoint_id']}/run"
    
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )
    
    response.raise_for_status()
    result = response.json()
    
    return result["id"]


def poll_status(config: Dict, job_id: str, timeout: int = 600) -> Dict:
    """Poll job status until completion."""
    url = f"https://api.runpod.ai/v2/{config['endpoint_id']}/status/{job_id}"
    
    start_time = time.time()
    poll_interval = 2
    
    while time.time() - start_time < timeout:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        status = result.get("status")
        
        if status == "COMPLETED":
            return result
        elif status == "FAILED":
            raise RuntimeError(f"Job failed: {result.get('error', 'Unknown error')}")
        elif status in ("IN_QUEUE", "IN_PROGRESS"):
            print(f"  Status: {status}...", flush=True)
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.2, 10)  # Exponential backoff
        else:
            raise RuntimeError(f"Unknown status: {status}")
    
    raise TimeoutError(f"Job {job_id} timed out after {timeout}s")


def save_output(result: Dict, output_path: Path) -> Path:
    """Save output image from RunPod result."""
    output = result.get("output", {})
    
    # RunPod ComfyUI worker returns base64 images
    if "images" in output:
        for img_data in output["images"]:
            if isinstance(img_data, str):
                # Base64 encoded
                img_bytes = base64.b64decode(img_data)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                return output_path
            elif isinstance(img_data, dict) and "image" in img_data:
                img_bytes = base64.b64decode(img_data["image"])
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                return output_path
    
    # Alternative: URL to download
    if "image_url" in output:
        response = requests.get(output["image_url"], timeout=60)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path
    
    raise ValueError(f"No output image found in result: {output.keys()}")


def render_bundle(bundle_path: Path, experiment_name: str = "render") -> Dict:
    """Main entry point: render bundle on RunPod."""
    bundle_path = Path(bundle_path)
    workflow_path = Path(__file__).parent / "workflow.json"
    
    print("=" * 50)
    print("IRP RunPod Render")
    print("=" * 50)
    
    # Validate bundle
    print("\nValidating bundle...")
    is_valid, errors = validate_bundle(bundle_path)
    if not is_valid:
        print(f"  ❌ Bundle invalid: {errors}")
        return {"status": "failed", "error": "Invalid bundle"}
    print("  ✅ Bundle valid")
    
    # Load config
    config = load_config()
    print(f"\nEndpoint: {config['endpoint_id']}")
    
    # Load workflow and manifest
    print("Loading workflow and manifest...")
    workflow = load_workflow(workflow_path)
    manifest = load_manifest(bundle_path)
    
    # Create experiment
    experiment = create_experiment(
        experiment_name, 
        base_dir=bundle_path / "experiments"
    )
    experiment.set_platform("runpod", config["endpoint_id"])
    experiment.log_bundle(bundle_path, manifest)
    experiment.log_workflow(workflow)
    
    # Build RunPod input
    print("Building RunPod payload...")
    payload = build_runpod_input(workflow, manifest, bundle_path)
    print(f"  Images: {len(payload['input']['images'])}")
    
    # Submit job
    print("\nSubmitting to RunPod...")
    try:
        job_id = submit_job(config, payload)
        print(f"  ✅ Job ID: {job_id}")
        experiment.log_submit(job_id)
    except Exception as e:
        experiment.fail(str(e))
        raise
    
    # Poll for completion
    print("\nWaiting for completion...")
    submit_time = time.time()
    result = poll_status(config, job_id)
    execution_time_ms = int((time.time() - submit_time) * 1000)
    
    # Save output
    print("\nSaving output...")
    output_path = experiment.output_dir / "render.png"
    save_output(result, output_path)
    print(f"  ✅ Saved: {output_path}")
    
    # Log results
    experiment.log_output(output_path)
    experiment.log_cost(execution_time_ms)
    experiment.complete("success")
    
    print(f"\n{'=' * 50}")
    print(f"✅ Render complete!")
    print(f"   Time: {execution_time_ms / 1000:.1f}s")
    print(f"   Cost: ${experiment.data['cost']['cost_usd']:.4f}")
    print(f"   Output: {output_path}")
    print(f"   Experiment: {experiment.output_dir}")
    
    return {
        "status": "success",
        "job_id": job_id,
        "experiment_id": experiment.id,
        "experiment_dir": str(experiment.output_dir),
        "render_path": str(output_path),
        "execution_time_ms": execution_time_ms,
        "cost_usd": experiment.data["cost"]["cost_usd"]
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python render_runpod.py <bundle_path> [experiment_name]")
        sys.exit(1)
    
    bundle_path = Path(sys.argv[1])
    experiment_name = sys.argv[2] if len(sys.argv) > 2 else "S1_GPU"
    
    result = render_bundle(bundle_path, experiment_name)
    print(json.dumps(result, indent=2))
