#!/usr/bin/env python3
"""
Extract individual masks from UperNet segmentation map by color
"""

from PIL import Image
import numpy as np
from pathlib import Path

# Color mapping from UperNet seg map (approximate RGB values)
COLOR_TO_ELEMENT = {
    (139, 69, 19): "floor",      # Dark brown
    (128, 128, 128): "wall",     # Gray
    (0, 206, 209): "wall_tile",  # Cyan
    (147, 112, 219): "vanity",   # Purple
    (211, 211, 211): "mirror",   # Light gray  
    (128, 128, 0): "window",     # Olive
    (50, 205, 50): "basket",     # Lime green
}

def extract_mask_by_color(seg_map_path, target_color, tolerance=30):
    """Extract binary mask for pixels matching target color"""
    img = Image.open(seg_map_path).convert('RGB')
    arr = np.array(img)
    
    # Create mask where color matches within tolerance
    diff = np.abs(arr.astype(int) - np.array(target_color))
    mask = np.all(diff <= tolerance, axis=2)
    
    # Convert to image (white=match, black=no match)
    mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
    return mask_img

def extract_all_masks(seg_map_path, output_dir):
    """Extract masks for all known elements"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    seg_img = Image.open(seg_map_path).convert('RGB')
    arr = np.array(seg_img)
    
    # Get unique colors in image
    pixels = arr.reshape(-1, 3)
    unique_colors = np.unique(pixels, axis=0)
    
    print(f"Found {len(unique_colors)} unique colors in segmentation map")
    
    masks = {}
    
    # Extract mask for each color region
    for i, color in enumerate(unique_colors):
        color_tuple = tuple(color)
        
        # Find matching element name or use generic
        element_name = None
        for known_color, name in COLOR_TO_ELEMENT.items():
            diff = np.abs(np.array(color_tuple) - np.array(known_color))
            if np.all(diff <= 40):
                element_name = name
                break
        
        if element_name is None:
            element_name = f"region_{i}"
        
        # Extract mask
        diff = np.abs(arr.astype(int) - color)
        mask = np.all(diff <= 5, axis=2)
        
        # Skip very small regions
        pixel_count = np.sum(mask)
        if pixel_count < 100:
            continue
        
        mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
        
        # Save
        mask_path = output_dir / f"mask_{element_name}.png"
        mask_img.save(mask_path)
        masks[element_name] = {
            'path': str(mask_path),
            'color': color_tuple,
            'pixels': int(pixel_count)
        }
        
        print(f"  {element_name}: {color_tuple} ({pixel_count} pixels)")
    
    return masks

def main():
    seg_map_path = Path.home() / "ComfyUI/output/seg_map_00001_.png"
    output_dir = Path.home() / "ComfyUI/input/masks"
    
    print("=" * 60)
    print("Extracting masks from segmentation map")
    print("=" * 60)
    
    masks = extract_all_masks(seg_map_path, output_dir)
    
    print(f"\n✅ Extracted {len(masks)} masks to {output_dir}")
    
    # Save manifest
    import json
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(masks, f, indent=2)
    
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    main()
