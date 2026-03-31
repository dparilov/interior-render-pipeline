#!/usr/bin/env python3
"""
Offline Render Preparation Script

Prepares everything needed for a render without using GPU time:
1. Validates bundle
2. Builds workflow
3. Lists required files
4. Creates render package (zip)

Usage:
    python3 scripts/prepare_render.py \
        --bundle examples/bathroom_01_surface_only \
        --experiment SF1 \
        --output results/SF1/
"""

import argparse
import json
import zipfile
import hashlib
import time
from pathlib import Path
from datetime import datetime
import sys

# Add render module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "render"))

from workflow_builder import WorkflowBuilder, validate_manifest_entities


def validate_bundle(bundle_path: Path) -> dict:
    """Validate bundle structure and files."""
    result = {
        "status": "ok",
        "errors": [],
        "warnings": []
    }
    
    required_files = ["manifest.json", "beauty.png", "depth.png", "boundary_mask.png"]
    for f in required_files:
        if not (bundle_path / f).exists():
            result["errors"].append(f"Missing required file: {f}")
            result["status"] = "error"
    
    # Check manifest
    manifest_path = bundle_path / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        # Check entities have required fields
        for entity in manifest.get("entities", []):
            name = entity.get("name", "unknown")
            render_mode = entity.get("render_mode")
            
            if render_mode == "regional_ipadapter":
                if not entity.get("mask"):
                    result["errors"].append(f"{name}: missing mask")
                if not entity.get("reference"):
                    result["errors"].append(f"{name}: missing reference")
            elif render_mode == "preserve":
                # Preserve entities don't need reference
                pass
    
    if result["errors"]:
        result["status"] = "error"
    
    return result


def build_workflow(bundle_path: Path, base_workflow_path: Path) -> tuple:
    """Build workflow from bundle manifest."""
    
    manifest_path = bundle_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Filter to only regional_ipadapter entities
    active_entities = [
        e for e in manifest.get("entities", [])
        if e.get("render_mode") == "regional_ipadapter"
    ]
    
    skipped_entities = [
        e.get("name") for e in manifest.get("entities", [])
        if e.get("render_mode") != "regional_ipadapter"
    ]
    
    # Create filtered manifest
    filtered_manifest = manifest.copy()
    filtered_manifest["entities"] = active_entities
    
    # Build workflow
    builder = WorkflowBuilder(str(base_workflow_path))
    workflow, metadata = builder.build(
        entities=active_entities,
        bundle_path=str(bundle_path),
        mode="all",
        order_policy="default"
    )
    
    # Replace BUNDLE_PATH placeholder with actual bundle name
    bundle_name = bundle_path.name
    workflow_str = json.dumps(workflow)
    workflow_str = workflow_str.replace("BUNDLE_PATH", bundle_name)
    workflow = json.loads(workflow_str)
    
    # Set positive prompt
    positive_prompt = manifest.get("prompt", 
        "photorealistic modern bathroom interior, high quality render, architectural visualization")
    workflow["prompt"]["positive"]["inputs"]["text"] = positive_prompt
    
    metadata["entities_skipped"] = skipped_entities
    
    return workflow, metadata


def list_required_files(bundle_path: Path, workflow: dict) -> list:
    """Extract list of files needed for render."""
    files = []
    bundle_name = bundle_path.name
    
    # Parse workflow for file references
    workflow_str = json.dumps(workflow)
    
    # Find all paths like "bundle_name/..."
    import re
    pattern = rf'"{bundle_name}/([^"]+)"'
    matches = re.findall(pattern, workflow_str)
    
    for match in matches:
        file_path = bundle_path / match
        if file_path.exists():
            files.append({
                "path": match,
                "size": file_path.stat().st_size,
                "exists": True
            })
        else:
            files.append({
                "path": match,
                "size": 0,
                "exists": False
            })
    
    return files


def create_render_package(
    bundle_path: Path,
    workflow: dict,
    metadata: dict,
    required_files: list,
    output_path: Path,
    experiment: str
) -> Path:
    """Create zip package with everything needed for render."""
    
    package_name = f"{experiment}_render_package.zip"
    package_path = output_path / package_name
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add workflow
        zf.writestr("workflow_api.json", json.dumps(workflow, indent=2))
        
        # Add metadata
        zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        # Add required files from bundle
        bundle_name = bundle_path.name
        for file_info in required_files:
            if file_info["exists"]:
                src_path = bundle_path / file_info["path"]
                dst_path = f"{bundle_name}/{file_info['path']}"
                zf.write(src_path, dst_path)
    
    return package_path


def main():
    parser = argparse.ArgumentParser(description="Prepare render package offline")
    parser.add_argument("--bundle", required=True, help="Path to bundle directory")
    parser.add_argument("--experiment", required=True, help="Experiment name (e.g., SF1)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--base-workflow", default="render/workflow.json", help="Base workflow template")
    args = parser.parse_args()
    
    bundle_path = Path(args.bundle)
    output_path = Path(args.output)
    base_workflow_path = Path(args.base_workflow)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    timing = {"experiment": args.experiment, "timestamp": datetime.utcnow().isoformat() + "Z"}
    start_total = time.time()
    
    print(f"=== Prepare Render: {args.experiment} ===")
    print(f"Bundle: {bundle_path}")
    print(f"Output: {output_path}")
    print()
    
    # Step 1: Validate bundle
    print("[1/4] Validating bundle...")
    start = time.time()
    validation = validate_bundle(bundle_path)
    timing["validate_sec"] = round(time.time() - start, 2)
    
    if validation["status"] != "ok":
        print(f"  ERROR: Bundle validation failed")
        for err in validation["errors"]:
            print(f"    - {err}")
        sys.exit(1)
    print(f"  OK ({timing['validate_sec']}s)")
    
    # Step 2: Build workflow
    print("[2/4] Building workflow...")
    start = time.time()
    workflow, metadata = build_workflow(bundle_path, base_workflow_path)
    timing["build_workflow_sec"] = round(time.time() - start, 2)
    print(f"  Entities applied: {metadata['entities_applied']}")
    print(f"  Entities skipped: {metadata.get('entities_skipped', [])}")
    print(f"  OK ({timing['build_workflow_sec']}s)")
    
    # Step 3: List required files
    print("[3/4] Listing required files...")
    start = time.time()
    required_files = list_required_files(bundle_path, workflow)
    timing["list_files_sec"] = round(time.time() - start, 2)
    
    total_size = sum(f["size"] for f in required_files if f["exists"])
    missing = [f["path"] for f in required_files if not f["exists"]]
    print(f"  Files: {len(required_files)}, Total size: {total_size / 1024 / 1024:.2f} MB")
    if missing:
        print(f"  WARNING: Missing files: {missing}")
    print(f"  OK ({timing['list_files_sec']}s)")
    
    # Step 4: Create render package
    print("[4/4] Creating render package...")
    start = time.time()
    package_path = create_render_package(
        bundle_path, workflow, metadata, required_files, output_path, args.experiment
    )
    timing["package_sec"] = round(time.time() - start, 2)
    package_size = package_path.stat().st_size
    print(f"  Package: {package_path.name} ({package_size / 1024 / 1024:.2f} MB)")
    print(f"  OK ({timing['package_sec']}s)")
    
    # Save timing
    timing["total_sec"] = round(time.time() - start_total, 2)
    timing["package_size_bytes"] = package_size
    timing["status"] = "ok"
    
    # Save artifacts
    with open(output_path / "validation_report.json", 'w') as f:
        json.dump(validation, f, indent=2)
    
    with open(output_path / "workflow_api.json", 'w') as f:
        json.dump(workflow, f, indent=2)
    
    with open(output_path / "render_manifest.json", 'w') as f:
        json.dump({
            "experiment": args.experiment,
            "bundle": str(bundle_path),
            "required_files": required_files,
            "metadata": metadata
        }, f, indent=2)
    
    with open(output_path / "offline_prep_timing.json", 'w') as f:
        json.dump(timing, f, indent=2)
    
    print()
    print(f"=== Done in {timing['total_sec']}s ===")
    print(f"Artifacts in {output_path}/:")
    print(f"  - {args.experiment}_render_package.zip")
    print(f"  - workflow_api.json")
    print(f"  - render_manifest.json")
    print(f"  - offline_prep_timing.json")


if __name__ == "__main__":
    main()
