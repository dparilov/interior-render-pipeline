#!/usr/bin/env python3
"""
IRP Experiment Tracker

Tracks each render with full reproducibility:
- Input parameters
- Workflow snapshot
- Output image
- Logs and metrics
"""

import argparse
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path


class Experiment:
    """Single render experiment."""
    
    def __init__(self, experiments_dir: Path, bundle_path: Path):
        self.bundle_path = Path(bundle_path)
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate experiment ID
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.exp_id = f"exp_{self.timestamp}"
        self.exp_dir = self.experiments_dir / self.exp_id
        self.exp_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata
        self.meta = {
            "id": self.exp_id,
            "timestamp": datetime.now().isoformat(),
            "bundle": str(bundle_path),
            "status": "created"
        }
    
    def log_params(self, params: dict):
        """Log render parameters."""
        self.meta["params"] = params
        self._save_meta()
    
    def log_environment(self, env: dict = None):
        """Log environment for full reproducibility."""
        import subprocess
        
        environment = env or {}
        
        # Git SHA
        try:
            git_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], 
                stderr=subprocess.DEVNULL
            ).decode().strip()
            environment["git_sha"] = git_sha
        except:
            environment["git_sha"] = "unknown"
        
        # Python version
        import sys
        environment["python_version"] = sys.version
        
        self.meta["environment"] = environment
        self._save_meta()
    
    def log_models(self, models: dict):
        """Log model filenames/hashes."""
        self.meta["models"] = models
        self._save_meta()
    
    def log_entities_used(self, entities: list):
        """Log actual entities and weights used."""
        self.meta["entities_used"] = entities
        self._save_meta()
    
    def log_workflow(self, workflow: dict):
        """Save workflow snapshot."""
        workflow_path = self.exp_dir / "workflow.json"
        workflow_path.write_text(json.dumps(workflow, indent=2))
        
        # Hash for comparison
        workflow_hash = hashlib.md5(json.dumps(workflow, sort_keys=True).encode()).hexdigest()[:8]
        self.meta["workflow_hash"] = workflow_hash
        self._save_meta()
    
    def log_bundle(self):
        """Copy bundle manifest and compute hashes."""
        manifest_src = self.bundle_path / "manifest.json"
        if manifest_src.exists():
            shutil.copy(manifest_src, self.exp_dir / "bundle_manifest.json")
            
            # Compute bundle hash
            manifest_hash = hashlib.md5(manifest_src.read_bytes()).hexdigest()[:8]
            self.meta["manifest_hash"] = manifest_hash
        
        # Hash references directory
        refs_dir = self.bundle_path / "references"
        if refs_dir.exists():
            refs_hash = self._hash_directory(refs_dir)
            self.meta["references_hash"] = refs_hash
        
        # Hash masks directory
        masks_dir = self.bundle_path / "masks"
        if masks_dir.exists():
            masks_hash = self._hash_directory(masks_dir)
            self.meta["masks_hash"] = masks_hash
        
        self._save_meta()
    
    def _hash_directory(self, directory: Path) -> str:
        """Compute hash of all files in directory."""
        hasher = hashlib.md5()
        for filepath in sorted(directory.iterdir()):
            if filepath.is_file():
                hasher.update(filepath.read_bytes())
        return hasher.hexdigest()[:8]
    
    def log_output(self, image_path: Path):
        """Copy output image to experiment."""
        if Path(image_path).exists():
            shutil.copy(image_path, self.exp_dir / "render.png")
            self.meta["output"] = "render.png"
            self._save_meta()
    
    def log_comfyui_response(self, response: dict):
        """Log ComfyUI API response."""
        self.meta["prompt_id"] = response.get("prompt_id")
        self.meta["queue_number"] = response.get("number")
        self._save_meta()
    
    def log_timing(self, start_time: float, end_time: float):
        """Log render timing."""
        duration = end_time - start_time
        self.meta["timing"] = {
            "start": datetime.fromtimestamp(start_time).isoformat(),
            "end": datetime.fromtimestamp(end_time).isoformat(),
            "duration_seconds": round(duration, 1),
            "duration_human": f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
        }
        self._save_meta()
    
    def log_error(self, error: str):
        """Log error."""
        self.meta["status"] = "failed"
        self.meta["error"] = error
        self._save_meta()
    
    def complete(self, notes: str = None):
        """Mark experiment as complete."""
        self.meta["status"] = "completed"
        if notes:
            self.meta["notes"] = notes
        self._save_meta()
    
    def _save_meta(self):
        """Save metadata to experiment directory."""
        meta_path = self.exp_dir / "experiment.json"
        meta_path.write_text(json.dumps(self.meta, indent=2))


class ExperimentLog:
    """Aggregate experiment log."""
    
    def __init__(self, experiments_dir: Path):
        self.experiments_dir = Path(experiments_dir)
    
    def list_experiments(self, limit: int = 20) -> list:
        """List recent experiments."""
        experiments = []
        
        for exp_dir in sorted(self.experiments_dir.iterdir(), reverse=True):
            if not exp_dir.is_dir():
                continue
            
            meta_path = exp_dir / "experiment.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                experiments.append(meta)
            
            if len(experiments) >= limit:
                break
        
        return experiments
    
    def compare(self, exp_id_1: str, exp_id_2: str) -> dict:
        """Compare two experiments."""
        exp1 = self._load_experiment(exp_id_1)
        exp2 = self._load_experiment(exp_id_2)
        
        if not exp1 or not exp2:
            return {"error": "Experiment not found"}
        
        return {
            "exp1": exp_id_1,
            "exp2": exp_id_2,
            "workflow_same": exp1.get("workflow_hash") == exp2.get("workflow_hash"),
            "params_diff": self._diff_params(exp1.get("params", {}), exp2.get("params", {}))
        }
    
    def _load_experiment(self, exp_id: str) -> dict:
        """Load experiment metadata."""
        meta_path = self.experiments_dir / exp_id / "experiment.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())
        return None
    
    def _diff_params(self, params1: dict, params2: dict) -> dict:
        """Find differences between params."""
        diff = {}
        all_keys = set(params1.keys()) | set(params2.keys())
        
        for key in all_keys:
            v1 = params1.get(key)
            v2 = params2.get(key)
            if v1 != v2:
                diff[key] = {"exp1": v1, "exp2": v2}
        
        return diff


def create_experiment(bundle_path: str, experiments_dir: str = None) -> Experiment:
    """Create a new experiment."""
    if experiments_dir is None:
        experiments_dir = Path(bundle_path).parent / "experiments"
    
    return Experiment(Path(experiments_dir), Path(bundle_path))


def main():
    parser = argparse.ArgumentParser(description="IRP Experiment Tracker")
    subparsers = parser.add_subparsers(dest="command")
    
    # List experiments
    list_parser = subparsers.add_parser("list", help="List experiments")
    list_parser.add_argument("--dir", type=Path, required=True, help="Experiments directory")
    list_parser.add_argument("--limit", type=int, default=20, help="Max experiments to show")
    
    # Compare experiments
    compare_parser = subparsers.add_parser("compare", help="Compare two experiments")
    compare_parser.add_argument("--dir", type=Path, required=True, help="Experiments directory")
    compare_parser.add_argument("exp1", help="First experiment ID")
    compare_parser.add_argument("exp2", help="Second experiment ID")
    
    args = parser.parse_args()
    
    if args.command == "list":
        log = ExperimentLog(args.dir)
        experiments = log.list_experiments(args.limit)
        
        print(f"\n{'ID':<25} {'Status':<12} {'Duration':<15} {'Workflow':<10}")
        print("-" * 65)
        
        for exp in experiments:
            duration = exp.get("timing", {}).get("duration_human", "-")
            workflow = exp.get("workflow_hash", "-")
            print(f"{exp['id']:<25} {exp['status']:<12} {duration:<15} {workflow:<10}")
    
    elif args.command == "compare":
        log = ExperimentLog(args.dir)
        result = log.compare(args.exp1, args.exp2)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
