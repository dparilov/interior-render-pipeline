#!/usr/bin/env python3
"""
Opus Mask Verification - итеративная верификация SAM масок через Claude Opus
Цикл до достижения 95% confidence по всем регионам
"""

import json
import base64
import sys
import os
from pathlib import Path
import anthropic

# Threshold для завершения
CONFIDENCE_THRESHOLD = 0.95
MAX_ITERATIONS = 5

def encode_image(image_path):
    """Encode image to base64"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def get_image_media_type(path):
    """Get media type from extension"""
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", 
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }.get(ext, "image/png")

def load_tz_elements(tz_path):
    """Parse ТЗ and extract elements with references"""
    with open(tz_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    elements = []
    current = {}
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('### ') and not line.startswith('###  '):
            if current.get('name'):
                elements.append(current)
            current = {'name': line[4:].strip()}
        
        elif line.startswith('- **Референс:**'):
            ref = line.split('`')[1] if '`' in line else ''
            current['reference'] = ref
    
    if current.get('name'):
        elements.append(current)
    
    return elements

def create_overlay(sketch_path, mask_path, output_path):
    """Create overlay of mask on sketch for visual verification"""
    from PIL import Image
    
    sketch = Image.open(sketch_path).convert('RGBA')
    mask = Image.open(mask_path).convert('RGBA')
    
    # Resize mask to match sketch if needed
    if mask.size != sketch.size:
        mask = mask.resize(sketch.size, Image.Resampling.LANCZOS)
    
    # Create semi-transparent overlay
    mask_overlay = Image.new('RGBA', sketch.size, (255, 0, 0, 0))
    for x in range(mask.width):
        for y in range(mask.height):
            r, g, b, a = mask.getpixel((x, y))
            if r > 128 or g > 128 or b > 128:  # White/bright areas
                mask_overlay.putpixel((x, y), (255, 0, 0, 128))  # Red with 50% alpha
    
    # Composite
    result = Image.alpha_composite(sketch, mask_overlay)
    result.save(output_path)
    return output_path

def verify_mask_with_opus(client, sketch_path, mask_path, seg_map_path, element_name, reference_path=None):
    """
    Ask Opus to verify if mask correctly covers the element
    Returns: (confidence: float, feedback: str)
    """
    
    images = []
    
    # 1. Sketch
    images.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": get_image_media_type(sketch_path),
            "data": encode_image(sketch_path)
        }
    })
    
    # 2. Segmentation map
    images.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": get_image_media_type(seg_map_path),
            "data": encode_image(seg_map_path)
        }
    })
    
    # 3. Individual mask (if provided)
    if mask_path and Path(mask_path).exists():
        images.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": get_image_media_type(mask_path),
                "data": encode_image(mask_path)
            }
        })
    
    # 4. Reference material (if provided)
    if reference_path and Path(reference_path).exists():
        images.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": get_image_media_type(reference_path),
                "data": encode_image(reference_path)
            }
        })
    
    prompt = f"""Analyze these images for interior design mask verification.

Image 1: Original sketch/layout of a bathroom
Image 2: Segmentation map with colored regions
{"Image 3: Individual mask for the element" if mask_path else ""}
{"Image 4: Reference material that should be applied to this region" if reference_path else ""}

TASK: Verify the segmentation for element: "{element_name}"

Analyze and respond with JSON:
{{
    "element": "{element_name}",
    "found_in_segmentation": true/false,
    "coverage_quality": 0.0-1.0,  // How well does the mask cover the element? 1.0 = perfect
    "boundary_accuracy": 0.0-1.0,  // Are boundaries clean and accurate?
    "no_overlap_issues": true/false,  // Does mask NOT overlap with other elements?
    "overall_confidence": 0.0-1.0,  // Overall confidence this mask is correct
    "issues": ["list of specific issues if any"],
    "suggestions": ["specific suggestions to fix issues"],
    "color_in_segmap": "describe the color representing this element in segmentation map"
}}

Be strict - only give high confidence if the mask is truly accurate.
Focus on: complete coverage, clean boundaries, no false positives."""

    content = images + [{"type": "text", "text": prompt}]
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",  # Using Sonnet for cost efficiency, can upgrade to Opus
        max_tokens=1000,
        messages=[{"role": "user", "content": content}]
    )
    
    # Parse response
    text = response.content[0].text
    
    # Extract JSON from response
    try:
        # Find JSON in response
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            return result.get('overall_confidence', 0.5), result
    except json.JSONDecodeError:
        pass
    
    return 0.5, {"error": "Could not parse response", "raw": text}

def verify_all_masks(tz_path, sketch_path, seg_map_path, masks_dir=None):
    """
    Verify all masks from ТЗ elements
    Returns: dict of element -> (confidence, feedback)
    """
    
    client = anthropic.Anthropic()
    elements = load_tz_elements(tz_path)
    
    results = {}
    all_pass = True
    
    print(f"\n{'='*60}")
    print("OPUS MASK VERIFICATION")
    print(f"{'='*60}")
    print(f"Elements to verify: {len(elements)}")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD*100}%")
    print()
    
    for el in elements:
        name = el['name']
        ref_path = None
        
        # Find reference if specified
        if el.get('reference'):
            ref_candidate = Path(tz_path).parent / el['reference']
            if ref_candidate.exists():
                ref_path = str(ref_candidate)
        
        # Find individual mask if available
        mask_path = None
        if masks_dir:
            mask_candidate = Path(masks_dir) / f"{name.lower().replace(' ', '_')}_mask.png"
            if mask_candidate.exists():
                mask_path = str(mask_candidate)
        
        print(f"Verifying: {name}...", end=" ", flush=True)
        
        confidence, feedback = verify_mask_with_opus(
            client, sketch_path, mask_path, seg_map_path, name, ref_path
        )
        
        results[name] = {
            'confidence': confidence,
            'feedback': feedback,
            'passed': confidence >= CONFIDENCE_THRESHOLD
        }
        
        status = "✅" if confidence >= CONFIDENCE_THRESHOLD else "❌"
        print(f"{status} {confidence*100:.0f}%")
        
        if confidence < CONFIDENCE_THRESHOLD:
            all_pass = False
            if isinstance(feedback, dict) and feedback.get('issues'):
                for issue in feedback['issues'][:2]:
                    print(f"   └─ {issue}")
    
    print()
    print(f"{'='*60}")
    print(f"RESULT: {'ALL PASSED ✅' if all_pass else 'NEEDS ITERATION ❌'}")
    print(f"{'='*60}")
    
    return results, all_pass

def main():
    # Paths
    tz_path = Path.home() / "ComfyUI/input/bathroom_masha/ТЗ.md"
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    seg_map_path = Path.home() / "ComfyUI/output/seg_map_00001_.png"
    
    if not seg_map_path.exists():
        print(f"❌ Segmentation map not found: {seg_map_path}")
        print("Run generate-region-masks.py first")
        return 1
    
    # Run verification
    results, all_pass = verify_all_masks(
        str(tz_path),
        str(sketch_path), 
        str(seg_map_path)
    )
    
    # Save results
    output_path = Path.home() / ".openclaw/workspace/logs/comfyui/mask_verification.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_path}")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
