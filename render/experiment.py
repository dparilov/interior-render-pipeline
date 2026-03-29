"""
IRP Experiment Tracking Module

Provides deterministic, traceable experiment logging.
All parameters are extracted from actual workflow, not hardcoded.
"""

import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


class Experiment:
    """Single experiment run with full traceability."""
    
    def __init__(self, experiment_id: str, output_dir: Path):
        self.id = experiment_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.data = {
            "experiment_id": experiment_id,
            "created": datetime.utcnow().isoformat() + "Z",
            "status": "running",
            "platform": "local",  # local | runpod
            "git_sha": self._get_git_sha(),
            "environment": {},
            "params": {},
            "workflow": {},
            "bundle": {},
            "result": {},
            "timing": {},
            "hashes": {},
            "cost": {}  # For cloud platforms
        }
        
    def _get_git_sha(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _hash_file(self, path: Path) -> str:
        if not path.exists():
            return "missing"
        with open(path, "rb") as f:
            return f"sha256:{hashlib.sha256(f.read()).hexdigest()[:16]}"
    
    def _hash_dict(self, d: Dict) -> str:
        return f"sha256:{hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]}"
    
    def set_platform(self, platform: str, endpoint_id: str = None):
        """Set compute platform (local | runpod)."""
        self.data["platform"] = platform
        if endpoint_id:
            self.data["environment"]["endpoint_id"] = endpoint_id
    
    def log_environment(self, comfyui_version: str, models: Dict[str, str]):
        """Log runtime environment."""
        self.data["environment"] = {
            **self.data.get("environment", {}),
            "comfyui_version": comfyui_version,
            "models": models
        }
    
    def log_bundle(self, bundle_path: Path, manifest: Dict):
        """Log bundle info with hashes."""
        self.data["bundle"] = {
            "path": str(bundle_path),
            "manifest_hash": self._hash_dict(manifest),
            "technical_spec_hash": manifest.get("technical_spec", {}).get("hash", "none"),
            "entities_count": len(manifest.get("entities", [])),
            "entities_used": [e["name"] for e in manifest.get("entities", [])],
            "critical_entities": [e["name"] for e in manifest.get("entities", []) if e.get("critical")]
        }
        
        # Log manifest field usage
        self.data["manifest_usage"] = {
            "depth_map_present": bool(manifest.get("depth_map")),
            "boundary_mask_present": bool(manifest.get("boundary_mask")),
            "technical_spec_present": bool(manifest.get("technical_spec")),
            "technical_spec_hash": manifest.get("technical_spec", {}).get("hash"),
            "technical_spec_summary": manifest.get("technical_spec", {}).get("summary"),
            "entities_with_prompt_source": sum(1 for e in manifest.get("entities", []) if e.get("prompt_source")),
            "entities_with_reference": sum(1 for e in manifest.get("entities", []) if e.get("reference")),
            "entities_with_coverage": sum(1 for e in manifest.get("entities", []) if e.get("coverage_pct")),
            "entities_list": [e["name"] for e in manifest.get("entities", [])]
        }
        
        # Hash key files
        self.data["hashes"]["beauty"] = self._hash_file(bundle_path / manifest.get("base_image", "beauty.png"))
        self.data["hashes"]["depth"] = self._hash_file(bundle_path / manifest.get("depth_map", "depth.png"))
        self.data["hashes"]["boundary"] = self._hash_file(bundle_path / manifest.get("boundary_mask", "boundary_mask.png"))
        
        # Hash all references
        ref_hashes = {}
        for entity in manifest.get("entities", []):
            if entity.get("reference"):
                ref_path = bundle_path / entity["reference"]
                ref_hashes[entity["name"]] = self._hash_file(ref_path)
        self.data["hashes"]["references"] = ref_hashes
    
    def log_workflow(self, workflow: Dict):
        """Extract actual parameters from workflow - NOT hardcoded values."""
        prompt = workflow.get("prompt", workflow)
        
        # Extract ControlNet strengths from actual workflow
        canny_node = prompt.get("apply_controlnet_canny", {}).get("inputs", {})
        depth_node = prompt.get("apply_controlnet_depth", {}).get("inputs", {})
        sampler_node = prompt.get("sampler", {}).get("inputs", {})
        
        self.data["params"] = {
            "canny_strength": canny_node.get("strength", "unknown"),
            "canny_start": canny_node.get("start_percent", "unknown"),
            "canny_end": canny_node.get("end_percent", "unknown"),
            "depth_strength": depth_node.get("strength", "unknown"),
            "depth_start": depth_node.get("start_percent", "unknown"),
            "depth_end": depth_node.get("end_percent", "unknown"),
            "seed": sampler_node.get("seed", "unknown"),
            "steps": sampler_node.get("steps", "unknown"),
            "cfg": sampler_node.get("cfg", "unknown"),
            "sampler_name": sampler_node.get("sampler_name", "unknown"),
            "scheduler": sampler_node.get("scheduler", "unknown")
        }
        
        # Extract IPAdapter info
        ipadapter_nodes = [k for k in prompt.keys() if k.startswith("ipadapter_")]
        self.data["params"]["ipadapter_count"] = len(ipadapter_nodes)
        self.data["params"]["ipadapter_entities"] = [n.replace("ipadapter_", "") for n in ipadapter_nodes]
        
        # Extract negative prompt
        negative_node = prompt.get("negative", {}).get("inputs", {})
        self.data["params"]["negative_prompt"] = negative_node.get("text", "")
        
        # Store workflow hash
        self.data["hashes"]["workflow"] = self._hash_dict(workflow)
        
        # Log depth source
        depth_source = "skp" if "load_depth" in prompt else "neural"
        if "depth_preprocess" in prompt:
            depth_source = "neural"
        self.data["params"]["depth_source"] = depth_source
        
        # Log boundary usage
        self.data["params"]["boundary_mask_active"] = "set_latent_mask" in prompt
        
        # Store full workflow for reproducibility
        workflow_path = self.output_dir / "workflow.json"
        with open(workflow_path, "w") as f:
            json.dump(workflow, f, indent=2)
    
    def log_submit(self, prompt_id: str):
        """Log ComfyUI prompt submission."""
        self.data["result"]["prompt_id"] = prompt_id
        self.data["timing"]["submitted"] = datetime.utcnow().isoformat() + "Z"
    
    def log_output(self, render_path: Path):
        """Log render output."""
        self.data["result"]["render_path"] = str(render_path)
        self.data["hashes"]["render"] = self._hash_file(render_path)
        self.data["timing"]["completed"] = datetime.utcnow().isoformat() + "Z"
        
        # Copy render to experiment dir
        if render_path.exists():
            import shutil
            shutil.copy(render_path, self.output_dir / "render.png")
    
    def log_cost(self, execution_time_ms: int, cost_usd: float = None):
        """Log cloud execution cost."""
        self.data["cost"] = {
            "execution_time_ms": execution_time_ms,
            "execution_time_sec": execution_time_ms / 1000,
            "cost_usd": cost_usd
        }
        # Calculate cost if not provided (RunPod serverless: ~$0.00044/sec for 4090)
        if cost_usd is None and self.data["platform"] == "runpod":
            self.data["cost"]["cost_usd"] = round((execution_time_ms / 1000) * 0.00044, 4)
    
    def complete(self, status: str = "success", notes: str = "", verdict: str = ""):
        """Mark experiment as complete and save.
        
        Args:
            status: success/failed/timeout
            notes: Free-form observations
            verdict: Structured result (e.g., "passed_structural", "failed_drift", "failed_hallucination")
        """
        self.data["status"] = status
        self.data["notes"] = notes
        self.data["verdict"] = verdict
        
        # Calculate duration if we have timing
        if "submitted" in self.data["timing"] and "completed" in self.data["timing"]:
            start = datetime.fromisoformat(self.data["timing"]["submitted"].rstrip("Z"))
            end = datetime.fromisoformat(self.data["timing"]["completed"].rstrip("Z"))
            self.data["timing"]["duration_seconds"] = (end - start).total_seconds()
        
        self._save()
    
    def fail(self, error: str):
        """Mark experiment as failed."""
        self.data["status"] = "failed"
        self.data["result"]["error"] = error
        self.data["timing"]["failed"] = datetime.utcnow().isoformat() + "Z"
        self._save()
    
    def _save(self):
        """Save experiment data to JSON."""
        path = self.output_dir / "experiment.json"
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)
        
        # Also save bundle manifest copy
        if "bundle" in self.data and self.data["bundle"].get("path"):
            bundle_path = Path(self.data["bundle"]["path"])
            manifest_path = bundle_path / "manifest.json"
            if manifest_path.exists():
                import shutil
                shutil.copy(manifest_path, self.output_dir / "bundle_manifest.json")


def create_experiment(name: str, base_dir: Path = None) -> Experiment:
    """Create a new experiment with timestamped ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"{name}_{timestamp}"
    
    if base_dir is None:
        base_dir = Path("experiments")
    
    output_dir = base_dir / experiment_id
    return Experiment(experiment_id, output_dir)


def load_experiment(path: Path) -> Dict:
    """Load experiment data from JSON."""
    with open(path / "experiment.json") as f:
        return json.load(f)
