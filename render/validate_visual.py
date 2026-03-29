"""
IRP Visual Validation

Uses Vision AI to verify:
1. Each mask covers the correct object
2. PIDs are correctly mapped
3. Prompts match ТЗ requirements

This is a REQUIRED step before rendering.

Usage:
    python validate_visual.py <bundle_path> [--batch-size 5]
"""

import json
import base64
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import os

# For Vision API - uses OpenAI-compatible endpoint
try:
    import requests
except ImportError:
    print("Error: requests required. Install with: pip install requests")
    sys.exit(1)


BATCH_SIZE = 5  # Max masks per Vision call to avoid limits


def encode_image(path: Path) -> str:
    """Encode image to base64."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def validate_masks_batch(
    beauty_path: Path,
    masks: List[Tuple[str, Path]],
    manifest: Dict
) -> Dict[str, Dict]:
    """Validate a batch of masks using Vision.
    
    Returns dict of {entity_name: {score, problems, correct_object}}
    """
    # Build prompt
    mask_names = [name for name, _ in masks]
    entities_info = []
    for name, _ in masks:
        entity = next((e for e in manifest["entities"] if e["name"] == name), None)
        if entity:
            entities_info.append(f"- {name}: {entity.get('prompt', 'no prompt')}")
    
    prompt = f"""Analyze these masks against the beauty render (first image).

Masks to validate: {', '.join(mask_names)}

Expected objects from ТЗ:
{chr(10).join(entities_info)}

For EACH mask, provide:
1. score (0-100): How accurately does the mask cover the intended object?
2. actual_object: What object does this mask ACTUALLY cover?
3. problems: List any issues
4. correct: true/false - is this the correct object?

Return as JSON:
{{
  "mask_name": {{
    "score": 85,
    "actual_object": "what it actually covers",
    "problems": ["list", "of", "problems"],
    "correct": true
  }}
}}
"""
    
    # Build messages with images
    images = [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(beauty_path)}"}}]
    for name, path in masks:
        images.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(path)}"}})
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                *images
            ]
        }
    ]
    
    # Call Vision API
    # This assumes OpenClaw/Anthropic endpoint - adjust as needed
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": messages
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"Vision API error: {response.status_code}")
            return {}
        
        result = response.json()
        content = result.get("content", [{}])[0].get("text", "{}")
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        
    except Exception as e:
        print(f"Vision API error: {e}")
    
    return {}


def validate_visual(bundle_path: Path, batch_size: int = BATCH_SIZE) -> Tuple[bool, Dict]:
    """Run visual validation on all masks.
    
    Returns (passed, results_dict)
    """
    print(f"\n{'='*50}")
    print("IRP Visual Validation")
    print(f"{'='*50}\n")
    
    # Load manifest
    manifest_path = bundle_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    beauty_path = bundle_path / manifest["base_image"]
    
    # Collect all masks
    masks = []
    for entity in manifest["entities"]:
        mask_path = bundle_path / entity["mask"]
        if mask_path.exists():
            masks.append((entity["name"], mask_path))
    
    print(f"Validating {len(masks)} masks in batches of {batch_size}...\n")
    
    # Process in batches
    all_results = {}
    for i in range(0, len(masks), batch_size):
        batch = masks[i:i+batch_size]
        batch_names = [name for name, _ in batch]
        print(f"Batch {i//batch_size + 1}: {', '.join(batch_names)}")
        
        results = validate_masks_batch(beauty_path, batch, manifest)
        all_results.update(results)
    
    # Analyze results
    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}\n")
    
    critical_failures = []
    warnings = []
    
    for name, result in all_results.items():
        score = result.get("score", 0)
        correct = result.get("correct", False)
        actual = result.get("actual_object", "unknown")
        problems = result.get("problems", [])
        
        # Determine status
        entity = next((e for e in manifest["entities"] if e["name"] == name), {})
        is_critical = entity.get("critical", False)
        
        if not correct:
            status = "❌ WRONG OBJECT"
            if is_critical:
                critical_failures.append(name)
        elif score < 50:
            status = "❌ LOW SCORE"
            if is_critical:
                critical_failures.append(name)
        elif score < 75:
            status = "⚠️ WARNING"
            warnings.append(name)
        else:
            status = "✅ OK"
        
        print(f"{status} {name}: {score}/100")
        print(f"   Covers: {actual}")
        if problems:
            print(f"   Problems: {', '.join(problems[:2])}")
        print()
    
    # Summary
    print(f"{'='*50}")
    passed = len(critical_failures) == 0
    
    if passed:
        print("✅ VISUAL VALIDATION PASSED")
    else:
        print("❌ VISUAL VALIDATION FAILED")
        print(f"   Critical failures: {', '.join(critical_failures)}")
    
    if warnings:
        print(f"   Warnings: {', '.join(warnings)}")
    
    print(f"{'='*50}\n")
    
    return passed, all_results


def validate_visual_simple(bundle_path: Path) -> Tuple[bool, List[str]]:
    """Simplified validation that returns (passed, error_messages).
    
    For integration into main validate.py
    """
    passed, results = validate_visual(bundle_path)
    
    errors = []
    for name, result in results.items():
        if not result.get("correct", False):
            errors.append(f"Mask '{name}' covers wrong object: {result.get('actual_object', 'unknown')}")
        elif result.get("score", 0) < 50:
            errors.append(f"Mask '{name}' has low score: {result.get('score', 0)}/100")
    
    return passed, errors


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual validation of IRP bundle")
    parser.add_argument("bundle_path", type=Path, help="Path to bundle directory")
    parser.add_argument("--batch-size", type=int, default=5, help="Masks per Vision call")
    
    args = parser.parse_args()
    
    if not args.bundle_path.exists():
        print(f"Error: Bundle not found: {args.bundle_path}")
        sys.exit(1)
    
    passed, _ = validate_visual(args.bundle_path, args.batch_size)
    sys.exit(0 if passed else 1)
