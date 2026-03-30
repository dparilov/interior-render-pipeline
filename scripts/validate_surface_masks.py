#!/usr/bin/env python3
"""
Validate surface masks for bathroom_01_surface_only bundle.

Checks:
1. walls_tile.png exists
2. walls_upper.png exists
3. Dimensions match bundle image size (1920x1080)
4. Masks are not empty
5. walls_tile ∩ walls_upper ≈ 0 (no significant overlap)
6. Masks don't exceed reasonable wall region
7. surfaces_combined = floor ∪ walls_tile ∪ walls_upper
8. window remains preserved geometry

Usage:
    python3 scripts/validate_surface_masks.py
"""

import json
import numpy as np
from PIL import Image
from pathlib import Path
import sys

BUNDLE_PATH = Path(__file__).parent.parent / "examples" / "bathroom_01_surface_only"
EXPECTED_SIZE = (1920, 1080)

def load_mask(name):
    """Load a mask file and return as numpy array."""
    path = BUNDLE_PATH / "masks" / f"{name}.png"
    if not path.exists():
        return None, f"File not found: {path}"
    
    img = Image.open(path)
    arr = np.array(img)
    
    # Convert to binary mask
    if len(arr.shape) == 3:
        arr = np.mean(arr, axis=2)
    
    return (arr > 128).astype(np.uint8), None


def validate():
    """Run all validation checks."""
    print("=" * 60)
    print("SURFACE MASK VALIDATION")
    print(f"Bundle: {BUNDLE_PATH}")
    print("=" * 60)
    
    errors = []
    warnings = []
    
    # 1. Check walls_tile.png exists
    print("\n[1] Checking walls_tile.png exists...")
    walls_tile, err = load_mask("walls_tile")
    if err:
        errors.append(f"walls_tile: {err}")
        print(f"  ✗ {err}")
    else:
        print(f"  ✓ walls_tile.png exists")
    
    # 2. Check walls_upper.png exists
    print("\n[2] Checking walls_upper.png exists...")
    walls_upper, err = load_mask("walls_upper")
    if err:
        errors.append(f"walls_upper: {err}")
        print(f"  ✗ {err}")
    else:
        print(f"  ✓ walls_upper.png exists")
    
    if walls_tile is None or walls_upper is None:
        print("\n⛔ Cannot continue validation - required masks missing")
        return False
    
    # 3. Check dimensions
    print("\n[3] Checking dimensions...")
    for name, mask in [("walls_tile", walls_tile), ("walls_upper", walls_upper)]:
        h, w = mask.shape
        if (w, h) != EXPECTED_SIZE:
            errors.append(f"{name}: Wrong size {w}x{h}, expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}")
            print(f"  ✗ {name}: {w}x{h} (expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]})")
        else:
            print(f"  ✓ {name}: {w}x{h}")
    
    # 4. Check masks are not empty
    print("\n[4] Checking masks are not empty...")
    for name, mask in [("walls_tile", walls_tile), ("walls_upper", walls_upper)]:
        pixel_count = np.sum(mask)
        coverage = 100 * pixel_count / mask.size
        if pixel_count < 1000:
            errors.append(f"{name}: Too few pixels ({pixel_count})")
            print(f"  ✗ {name}: {pixel_count} pixels ({coverage:.2f}%) - TOO FEW")
        else:
            print(f"  ✓ {name}: {pixel_count} pixels ({coverage:.2f}%)")
    
    # 5. Check overlap
    print("\n[5] Checking walls_tile ∩ walls_upper overlap...")
    overlap = np.sum(walls_tile & walls_upper)
    max_overlap = 100
    if overlap > max_overlap:
        warnings.append(f"walls_tile/walls_upper overlap: {overlap} pixels (max {max_overlap})")
        print(f"  ⚠ Overlap: {overlap} pixels (warning threshold: {max_overlap})")
    else:
        print(f"  ✓ Overlap: {overlap} pixels (within tolerance)")
    
    # 6. Check masks don't exceed reasonable region (top 10% and bottom 10% should be mostly empty)
    print("\n[6] Checking mask region bounds...")
    h = walls_tile.shape[0]
    top_region = h // 10
    bottom_region = h - (h // 10)
    
    tile_top = np.sum(walls_tile[:top_region, :])
    tile_bottom = np.sum(walls_tile[bottom_region:, :])
    upper_bottom = np.sum(walls_upper[bottom_region:, :])
    
    if tile_top > 1000:
        warnings.append(f"walls_tile has {tile_top} pixels in top 10% region")
        print(f"  ⚠ walls_tile: {tile_top} pixels in top 10% (unusual)")
    else:
        print(f"  ✓ walls_tile top region: {tile_top} pixels")
    
    if upper_bottom > 5000:
        warnings.append(f"walls_upper has {upper_bottom} pixels in bottom 10% region")
        print(f"  ⚠ walls_upper: {upper_bottom} pixels in bottom 10% (unusual)")
    else:
        print(f"  ✓ walls_upper bottom region: {upper_bottom} pixels")
    
    # 7. Check surfaces_combined
    print("\n[7] Checking surfaces_combined...")
    floor, err = load_mask("floor")
    if err:
        errors.append(f"floor: {err}")
        print(f"  ✗ floor.png: {err}")
    else:
        surfaces_combined, err = load_mask("surfaces_combined")
        if err:
            errors.append(f"surfaces_combined: {err}")
            print(f"  ✗ surfaces_combined.png: {err}")
        else:
            expected_combined = np.maximum(floor, np.maximum(walls_tile, walls_upper))
            diff = np.sum(np.abs(surfaces_combined.astype(int) - expected_combined.astype(int)))
            
            if diff > 100:
                errors.append(f"surfaces_combined doesn't match floor ∪ walls_tile ∪ walls_upper (diff={diff})")
                print(f"  ✗ Mismatch with expected union: {diff} pixel difference")
            else:
                combined_pixels = np.sum(surfaces_combined)
                floor_pixels = np.sum(floor)
                print(f"  ✓ surfaces_combined = floor({floor_pixels}) ∪ walls_tile ∪ walls_upper")
                print(f"    Total: {combined_pixels} pixels ({100*combined_pixels/surfaces_combined.size:.1f}%)")
    
    # 8. Check window (preserved geometry)
    print("\n[8] Checking window (preserved geometry)...")
    window, err = load_mask("window")
    if err:
        errors.append(f"window: {err}")
        print(f"  ✗ window.png: {err}")
    else:
        window_pixels = np.sum(window)
        # Window should not overlap significantly with wall masks
        window_tile_overlap = np.sum(window & walls_tile)
        window_upper_overlap = np.sum(window & walls_upper)
        
        if window_tile_overlap > 50 or window_upper_overlap > 50:
            warnings.append(f"window overlaps with wall masks: tile={window_tile_overlap}, upper={window_upper_overlap}")
            print(f"  ⚠ Window overlaps: tile={window_tile_overlap}, upper={window_upper_overlap}")
        else:
            print(f"  ✓ window: {window_pixels} pixels, minimal overlap with walls")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("\n✅ All checks passed!")
        status = "VALID"
    elif not errors:
        print("\n✅ Validation passed with warnings")
        status = "VALID_WITH_WARNINGS"
    else:
        print("\n❌ Validation FAILED")
        status = "INVALID"
    
    # Write validation report
    report = {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "masks": {
            "walls_tile": {"pixels": int(np.sum(walls_tile)), "coverage_pct": round(100*np.sum(walls_tile)/walls_tile.size, 2)},
            "walls_upper": {"pixels": int(np.sum(walls_upper)), "coverage_pct": round(100*np.sum(walls_upper)/walls_upper.size, 2)},
            "overlap": int(overlap)
        }
    }
    
    report_path = BUNDLE_PATH / "validation_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")
    
    return len(errors) == 0


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
