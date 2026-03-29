"""
IRP Bundle Post-Processor

Required step after SketchUp export due to hardcoded 2X antialiasing
in SketchUp's write_image API (see: github.com/SketchUp/api-issue-tracker/issues/545).

This script:
1. Binarizes all masks (threshold 128 → 0/255)
2. Optionally adds references/ and technical_spec.md
3. Updates manifest with technical_spec hash

Usage:
    python postprocess.py <bundle_path> [--refs <refs_dir>] [--spec <spec_path>]
"""

import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional
import sys

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Error: PIL and numpy required. Install with: pip install pillow numpy")
    sys.exit(1)


def binarize_masks(bundle_path: Path) -> int:
    """Binarize all masks using threshold 128.
    
    Returns number of masks processed.
    """
    count = 0
    
    # Process individual masks
    masks_dir = bundle_path / "masks"
    if masks_dir.exists():
        for mask_path in masks_dir.glob("*.png"):
            img = Image.open(mask_path).convert("L")
            arr = np.array(img)
            binary = np.where(arr > 128, 255, 0).astype(np.uint8)
            Image.fromarray(binary).save(mask_path)
            count += 1
            print(f"  ✓ masks/{mask_path.name}")
    
    # Process boundary mask
    boundary_path = bundle_path / "boundary_mask.png"
    if boundary_path.exists():
        img = Image.open(boundary_path).convert("L")
        arr = np.array(img)
        binary = np.where(arr > 128, 255, 0).astype(np.uint8)
        Image.fromarray(binary).save(boundary_path)
        count += 1
        print(f"  ✓ boundary_mask.png")
    
    return count


def add_references(bundle_path: Path, refs_dir: Path) -> int:
    """Copy references directory to bundle.
    
    Returns number of files copied.
    """
    dest = bundle_path / "references"
    if dest.exists():
        shutil.rmtree(dest)
    
    shutil.copytree(refs_dir, dest)
    files = list(dest.glob("*"))
    print(f"  ✓ references/ ({len(files)} files)")
    return len(files)


def add_technical_spec(bundle_path: Path, spec_path: Path) -> str:
    """Copy technical spec and update manifest.
    
    Returns hash of spec file.
    """
    # Copy file
    dest = bundle_path / "technical_spec.md"
    shutil.copy(spec_path, dest)
    
    # Calculate hash
    with open(dest, "rb") as f:
        spec_hash = f"sha256:{hashlib.sha256(f.read()).hexdigest()}"
    
    # Extract summary
    with open(dest, encoding="utf-8") as f:
        summary = ""
        for line in f:
            if line.startswith("#"):
                summary = line.lstrip("#").strip()
                break
    
    # Update manifest
    manifest_path = bundle_path / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        manifest["technical_spec"] = {
            "path": "technical_spec.md",
            "hash": spec_hash,
            "summary": summary
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ technical_spec.md")
    print(f"    hash: {spec_hash[:50]}...")
    return spec_hash


def postprocess(
    bundle_path: Path,
    refs_dir: Optional[Path] = None,
    spec_path: Optional[Path] = None
):
    """Run full post-processing on bundle."""
    
    print(f"\n{'='*50}")
    print(f"IRP Bundle Post-Processor")
    print(f"{'='*50}\n")
    print(f"Bundle: {bundle_path}\n")
    
    # 1. Binarize masks
    print("=== BINARIZING MASKS ===")
    mask_count = binarize_masks(bundle_path)
    print(f"    Total: {mask_count} masks\n")
    
    # 2. Add references if provided
    if refs_dir and refs_dir.exists():
        print("=== ADDING REFERENCES ===")
        add_references(bundle_path, refs_dir)
        print()
    
    # 3. Add technical spec if provided
    if spec_path and spec_path.exists():
        print("=== ADDING TECHNICAL SPEC ===")
        add_technical_spec(bundle_path, spec_path)
        print()
    
    print(f"{'='*50}")
    print("Post-processing complete!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-process IRP bundle")
    parser.add_argument("bundle_path", type=Path, help="Path to bundle directory")
    parser.add_argument("--refs", type=Path, help="Path to references directory")
    parser.add_argument("--spec", type=Path, help="Path to technical spec (ТЗ.md)")
    
    args = parser.parse_args()
    
    if not args.bundle_path.exists():
        print(f"Error: Bundle not found: {args.bundle_path}")
        sys.exit(1)
    
    postprocess(
        bundle_path=args.bundle_path,
        refs_dir=args.refs,
        spec_path=args.spec
    )
