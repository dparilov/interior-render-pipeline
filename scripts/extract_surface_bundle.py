#!/usr/bin/env python3
"""
Extract surface-only bundle from full bathroom_01 bundle.

Creates: examples/bathroom_01_surfaces/
From:    examples/bathroom_01/

This script prepares the bundle structure for Epic D surface-only experiments.
It does NOT run any renders — only prepares input files.

Usage:
    python3 scripts/extract_surface_bundle.py

Requirements:
    - PIL/Pillow for mask operations
    - Source bundle: examples/bathroom_01/
"""

import json
import shutil
from pathlib import Path

# Configuration
SOURCE_BUNDLE = Path("examples/bathroom_01")
TARGET_BUNDLE = Path("examples/bathroom_01_surfaces")

# Files to copy directly
DIRECT_COPY = [
    "beauty.png",
    "depth.png",
    "boundary_mask.png",
    "technical_spec.md",
]

# Masks to copy (existing)
MASKS_COPY = [
    "masks/floor.png",
    "masks/window.png",
]

# References to copy
REFS_COPY = [
    "references/wall_tiles.png",
    "references/floor_tiles.jpg",
]

# Fixtures to combine into fixtures_all.png
FIXTURE_MASKS = [
    "masks/bathtub.png",
    "masks/vanity.png",
    "masks/shower_screen.png",
    "masks/rainshower.png",
    "masks/towel_warmer.png",
    "masks/basket.png",
    "masks/mirror.png",
]


def check_source_bundle():
    """Verify source bundle exists and has required files."""
    if not SOURCE_BUNDLE.exists():
        raise FileNotFoundError(f"Source bundle not found: {SOURCE_BUNDLE}")
    
    missing = []
    for f in DIRECT_COPY + MASKS_COPY + REFS_COPY:
        if not (SOURCE_BUNDLE / f).exists():
            missing.append(f)
    
    # walls.png is special - needs to be split
    if not (SOURCE_BUNDLE / "masks/walls.png").exists():
        missing.append("masks/walls.png")
    
    if missing:
        print(f"WARNING: Missing files in source bundle: {missing}")
        return False
    return True


def create_target_structure():
    """Create target bundle directory structure."""
    TARGET_BUNDLE.mkdir(parents=True, exist_ok=True)
    (TARGET_BUNDLE / "masks").mkdir(exist_ok=True)
    (TARGET_BUNDLE / "references").mkdir(exist_ok=True)


def copy_direct_files():
    """Copy files that don't need modification."""
    for f in DIRECT_COPY:
        src = SOURCE_BUNDLE / f
        dst = TARGET_BUNDLE / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {f}")
        else:
            print(f"  SKIP (missing): {f}")


def copy_masks():
    """Copy existing masks."""
    for f in MASKS_COPY:
        src = SOURCE_BUNDLE / f
        dst = TARGET_BUNDLE / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {f}")
        else:
            print(f"  SKIP (missing): {f}")


def copy_references():
    """Copy reference images."""
    for f in REFS_COPY:
        src = SOURCE_BUNDLE / f
        dst = TARGET_BUNDLE / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {f}")
        else:
            print(f"  SKIP (missing): {f}")


def split_walls_mask():
    """
    Split walls.png into walls_tile.png and walls_upper.png.
    
    Strategy: The original walls.png covers both tile and upper areas.
    We need to split based on the horizontal boundary between them.
    
    Options:
    1. Manual split with known Y coordinate
    2. Detect boundary from beauty.png color analysis
    3. Use existing separate masks if available
    
    For now: STUB - creates placeholder with instructions.
    """
    try:
        from PIL import Image
        import numpy as np
        
        walls_path = SOURCE_BUNDLE / "masks/walls.png"
        if not walls_path.exists():
            print("  SKIP: walls.png not found")
            return False
        
        walls = np.array(Image.open(walls_path))
        h, w = walls.shape[:2] if len(walls.shape) > 2 else walls.shape
        
        # TODO: Detect actual tile/upper boundary
        # For now, this is a placeholder that needs manual adjustment
        # The boundary Y coordinate should be determined from:
        # 1. Visual inspection of beauty.png
        # 2. Or provided in manifest.json
        
        # Placeholder: assume tile is lower 60%, upper is top 40%
        # This MUST be adjusted based on actual scene geometry
        TILE_UPPER_BOUNDARY_Y = int(h * 0.4)  # ADJUST THIS
        
        print(f"  NOTE: Using placeholder boundary at Y={TILE_UPPER_BOUNDARY_Y}")
        print(f"        Image size: {w}x{h}")
        print(f"        VERIFY THIS MANUALLY before running experiments!")
        
        # Create split masks
        walls_upper = walls.copy()
        walls_tile = walls.copy()
        
        if len(walls.shape) > 2:
            walls_upper[TILE_UPPER_BOUNDARY_Y:, :, :] = 0
            walls_tile[:TILE_UPPER_BOUNDARY_Y, :, :] = 0
        else:
            walls_upper[TILE_UPPER_BOUNDARY_Y:, :] = 0
            walls_tile[:TILE_UPPER_BOUNDARY_Y, :] = 0
        
        Image.fromarray(walls_upper).save(TARGET_BUNDLE / "masks/walls_upper.png")
        Image.fromarray(walls_tile).save(TARGET_BUNDLE / "masks/walls_tile.png")
        
        print(f"  Created: masks/walls_upper.png (Y < {TILE_UPPER_BOUNDARY_Y})")
        print(f"  Created: masks/walls_tile.png (Y >= {TILE_UPPER_BOUNDARY_Y})")
        return True
        
    except ImportError:
        print("  ERROR: PIL/Pillow not installed")
        print("         Run: pip install Pillow")
        return False


def combine_surfaces_mask():
    """Create surfaces_combined.png from individual surface masks."""
    try:
        from PIL import Image
        import numpy as np
        
        masks = []
        for name in ["walls_tile.png", "walls_upper.png", "floor.png"]:
            path = TARGET_BUNDLE / "masks" / name
            if path.exists():
                masks.append(np.array(Image.open(path)))
        
        if not masks:
            print("  SKIP: No surface masks found")
            return False
        
        # Combine with maximum (union)
        combined = masks[0]
        for m in masks[1:]:
            combined = np.maximum(combined, m)
        
        Image.fromarray(combined).save(TARGET_BUNDLE / "masks/surfaces_combined.png")
        print(f"  Created: masks/surfaces_combined.png")
        return True
        
    except ImportError:
        print("  ERROR: PIL/Pillow not installed")
        return False


def combine_fixtures_mask():
    """Create fixtures_all.png from individual fixture masks."""
    try:
        from PIL import Image
        import numpy as np
        
        masks = []
        for f in FIXTURE_MASKS:
            path = SOURCE_BUNDLE / f
            if path.exists():
                masks.append(np.array(Image.open(path)))
        
        if not masks:
            print("  SKIP: No fixture masks found")
            return False
        
        combined = masks[0]
        for m in masks[1:]:
            combined = np.maximum(combined, m)
        
        Image.fromarray(combined).save(TARGET_BUNDLE / "masks/fixtures_all.png")
        print(f"  Created: masks/fixtures_all.png (from {len(masks)} fixtures)")
        return True
        
    except ImportError:
        print("  ERROR: PIL/Pillow not installed")
        return False


def create_geometry_preserved_mask():
    """Create geometry_preserved.png (window + structural elements)."""
    try:
        from PIL import Image
        import numpy as np
        
        window_path = TARGET_BUNDLE / "masks/window.png"
        if not window_path.exists():
            print("  SKIP: window.png not found")
            return False
        
        # For now, geometry_preserved = window only
        # Can be extended with other structural elements
        window = np.array(Image.open(window_path))
        Image.fromarray(window).save(TARGET_BUNDLE / "masks/geometry_preserved.png")
        print(f"  Created: masks/geometry_preserved.png (window)")
        return True
        
    except ImportError:
        print("  ERROR: PIL/Pillow not installed")
        return False


def create_manifest():
    """Create manifest.json for surface-only bundle."""
    
    # Load original manifest for camera/image_size info
    orig_manifest_path = SOURCE_BUNDLE / "manifest.json"
    if orig_manifest_path.exists():
        with open(orig_manifest_path) as f:
            orig = json.load(f)
    else:
        orig = {}
    
    manifest = {
        "version": "1.2",
        "scene_id": orig.get("scene_id", "bathroom_01_surfaces"),
        "derived_from": "bathroom_01",
        "experiment": "Epic D: Surface-Only",
        "created": None,  # Fill at creation time
        "base_image": "beauty.png",
        "depth_map": "depth.png",
        "boundary_mask": "boundary_mask.png",
        "image_size": orig.get("image_size", {"width": 1920, "height": 1080}),
        "camera": orig.get("camera", {}),
        "entities": [
            {
                "name": "walls_tile",
                "role": "surface.walls_tile",
                "class": "surface",
                "mask": "masks/walls_tile.png",
                "reference": "references/wall_tiles.png",
                "prompt": "white glossy wavy subway tiles, Equipe Costa Nova White style, 3D ribbed texture",
                "critical": True,
                "render_mode": "regional_ipadapter",
                "ipadapter_weight": 0.55
            },
            {
                "name": "walls_upper",
                "role": "surface.walls_upper",
                "class": "surface",
                "mask": "masks/walls_upper.png",
                "reference": None,
                "prompt": "smooth gray painted wall, matte finish",
                "critical": False,
                "render_mode": "preserve",
                "note": "No image reference - evaluate by color/boundary/spec compliance"
            },
            {
                "name": "floor",
                "role": "surface.floor",
                "class": "surface",
                "mask": "masks/floor.png",
                "reference": "references/floor_tiles.jpg",
                "prompt": "blue ceramic floor tiles with white geometric pattern, Equipe Rivoli Bergen Azul style",
                "critical": True,
                "render_mode": "regional_ipadapter",
                "ipadapter_weight": 0.55
            }
        ],
        "preserved": [
            {
                "name": "window",
                "role": "opening.window",
                "class": "opening",
                "mask": "masks/window.png",
                "reason": "Natural light source, structural element - must remain unchanged"
            }
        ],
        "excluded": [
            {"name": "bathtub", "reason": "Surface-only experiment"},
            {"name": "vanity", "reason": "Surface-only experiment"},
            {"name": "shower_screen", "reason": "Surface-only experiment"},
            {"name": "rainshower", "reason": "Surface-only experiment"},
            {"name": "towel_warmer", "reason": "Surface-only experiment"},
            {"name": "basket", "reason": "Surface-only experiment"},
            {"name": "mirror", "reason": "Surface-only experiment"}
        ],
        "composite_masks": {
            "surfaces_combined": "masks/surfaces_combined.png",
            "fixtures_all": "masks/fixtures_all.png",
            "geometry_preserved": "masks/geometry_preserved.png"
        }
    }
    
    with open(TARGET_BUNDLE / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Created: manifest.json")


def create_readme():
    """Create README for the bundle."""
    readme = """# bathroom_01_surfaces

Surface-only bundle derived from bathroom_01 for Epic D experiments.

## Purpose

Test IPAdapter surface material transfer on walls and floor only,
with fixtures excluded and window preserved as structural geometry.

## Surfaces

| Surface | Mask | Reference | Notes |
|---------|------|-----------|-------|
| walls_tile | walls_tile.png | wall_tiles.png | Costa Nova white tiles |
| walls_upper | walls_upper.png | — | Gray paint, no reference |
| floor | floor.png | floor_tiles.jpg | Rivoli Bergen blue tiles |

## Preserved Geometry

- **window** — Natural light source, must remain unchanged

## Composite Masks

- `surfaces_combined.png` — All surfaces (for single-pass rendering)
- `fixtures_all.png` — All excluded fixtures (for masking)
- `geometry_preserved.png` — Window and structural elements

## ⚠️ IMPORTANT: Verify walls_tile/walls_upper Split

The boundary between walls_tile and walls_upper was created with a placeholder
Y coordinate. Before running experiments:

1. Open `beauty.png` in an image editor
2. Find the actual Y coordinate where tiles meet gray wall
3. Re-run extraction with correct boundary, or manually adjust masks

## Extraction

```bash
python3 scripts/extract_surface_bundle.py
```

## Workflows

See `docs/specs/EPIC_D_SURFACE_ONLY.md` for SF1-SF5 workflow definitions.
"""
    
    with open(TARGET_BUNDLE / "README.md", "w") as f:
        f.write(readme)
    print(f"  Created: README.md")


def main():
    print("=" * 60)
    print("Surface Bundle Extraction: bathroom_01 → bathroom_01_surfaces")
    print("=" * 60)
    
    print("\n[1/8] Checking source bundle...")
    if not check_source_bundle():
        print("WARNING: Some source files missing, continuing anyway")
    
    print("\n[2/8] Creating target structure...")
    create_target_structure()
    
    print("\n[3/8] Copying base files...")
    copy_direct_files()
    
    print("\n[4/8] Copying masks...")
    copy_masks()
    
    print("\n[5/8] Copying references...")
    copy_references()
    
    print("\n[6/8] Splitting walls mask...")
    split_walls_mask()
    
    print("\n[7/8] Creating composite masks...")
    combine_surfaces_mask()
    combine_fixtures_mask()
    create_geometry_preserved_mask()
    
    print("\n[8/8] Creating manifest and README...")
    create_manifest()
    create_readme()
    
    print("\n" + "=" * 60)
    print(f"Done! Bundle created at: {TARGET_BUNDLE}/")
    print("=" * 60)
    print("\n⚠️  NEXT STEPS:")
    print("1. Verify walls_tile/walls_upper boundary visually")
    print("2. Adjust TILE_UPPER_BOUNDARY_Y if needed and re-run")
    print("3. Review manifest.json")
    print("4. Proceed with SF1-SF5 workflow creation")


if __name__ == "__main__":
    main()
