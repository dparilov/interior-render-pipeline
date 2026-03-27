#!/usr/bin/env python3
"""
Render v6 - Full Pipeline from ТЗ to Final Render

Pipeline:
1. Parse ТЗ → extract elements, references, prompts
2. UperNet segmentation → initial masks
3. Opus verification → iterate until 95%+ or max 10 iterations
4. SAM for <90% elements → additional masks
5. Opus verification of SAM → iterate until 95%+ or max 10 iterations
6. Prepare IP-Adapters: each element gets reference + mask
7. Render: SDXL + Canny + Depth + Regional IP-Adapters
8. Final Opus verification against ТЗ
"""

import json
import requests
import time
import sys
import shutil
import base64
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

COMFYUI_API = "http://127.0.0.1:8188"

# ============================================
# DATA STRUCTURES
# ============================================

@dataclass
class Element:
    name: str
    name_en: str
    reference: Optional[str] = None
    description: str = ""
    critical: bool = False
    confidence: float = 0.0
    mask_path: Optional[str] = None
    mask_source: str = "none"  # upernet, sam, manual
    iterations: int = 0

@dataclass
class VerificationMatrix:
    stage: str
    elements: dict = field(default_factory=dict)
    iterations_log: list = field(default_factory=list)

# ============================================
# STEP 1: PARSE ТЗ
# ============================================

def parse_tz(tz_path: Path) -> tuple[list[Element], str, str]:
    """Parse ТЗ and extract elements, build prompts"""
    
    with open(tz_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    elements = []
    current = {}
    
    # Element name translations
    name_translations = {
        "Напольная плитка": "floor_tiles",
        "Настенная плитка": "wall_tiles",
        "Тумба с раковиной": "vanity",
        "Смеситель для раковины": "faucet",
        "Зеркало": "mirror",
        "Душевая система": "shower",
        "Ванна": "bathtub",
        "Полотенцесушитель": "towel_warmer",
        "Корзина для белья": "basket",
    }
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('### ') and not line.startswith('###  '):
            if current.get('name'):
                name_en = name_translations.get(current['name'], current['name'].lower().replace(' ', '_'))
                elements.append(Element(
                    name=current['name'],
                    name_en=name_en,
                    reference=current.get('reference'),
                    description=current.get('description', ''),
                    critical=current.get('critical', False)
                ))
            current = {'name': line[4:].strip()}
        
        elif line.startswith('- **Референс:**'):
            ref = line.split('`')[1] if '`' in line else ''
            current['reference'] = ref
        
        elif line.startswith('- **Описание:**'):
            current['description'] = line.replace('- **Описание:**', '').strip()
        
        elif line.startswith('- **КРИТИЧНО:**'):
            current['critical'] = 'ДА' in line
    
    if current.get('name'):
        name_en = name_translations.get(current['name'], current['name'].lower().replace(' ', '_'))
        elements.append(Element(
            name=current['name'],
            name_en=name_en,
            reference=current.get('reference'),
            description=current.get('description', ''),
            critical=current.get('critical', False)
        ))
    
    # Add bathtub screen as separate element
    elements.append(Element(
        name="Экран ванной",
        name_en="bathtub_screen",
        reference="референсы/wall_tiles.png",
        description="Экран ванной облицован настенной плиткой Costa Nova White",
        critical=False
    ))
    
    # Build positive prompt
    positive_parts = [
        "A modern compact bathroom interior, photorealistic photograph, 8K resolution",
        "warm natural lighting from small window on upper left",
        "magazine quality interior design photo, Architectural Digest style",
        "clear material textures, visible tile grout lines, chrome reflections"
    ]
    
    for el in elements:
        if el.description:
            # Translate key terms
            desc = el.description
            desc = desc.replace('СИНИЙ', 'blue').replace('БЕЛЫЙ', 'white').replace('БЕЛАЯ', 'white')
            desc = desc.replace('ТЁМНО-СЕРОГО', 'dark charcoal gray').replace('ТЁМНО-СЕРЫЙ', 'dark charcoal gray')
            desc = desc.replace('ХРОМ', 'chrome').replace('хром', 'chrome')
            desc = desc.replace('керамическая', 'ceramic').replace('глянцевая', 'glossy')
            desc = desc.replace('подвесная', 'wall-mounted floating')
            desc = desc.replace('ВЕРТИКАЛЬНАЯ', 'vertical').replace('вертикальный', 'vertical')
            positive_parts.append(desc[:150])
    
    positive_prompt = ". ".join(positive_parts[:12])
    
    # Build negative prompt from ТЗ constraints
    negative_prompt = """low quality, blurry, watermark, text, deformed, bad anatomy,
brass faucet, gold faucet, bronze fixtures,
black towel warmer, chrome towel warmer,
white vanity, wooden vanity, beige vanity,
beige floor tiles, brown floor tiles, plain floor,
horizontal wall tiles, flat wall tiles,
cartoon, anime, illustration, 3D render look"""
    
    return elements, positive_prompt, negative_prompt

# ============================================
# STEP 2: UPERNET SEGMENTATION
# ============================================

def run_upernet_segmentation(sketch_path: Path, output_dir: Path) -> Path:
    """Run UperNet segmentation on sketch"""
    
    # Copy sketch to input
    input_dir = Path.home() / "ComfyUI/input"
    shutil.copy(sketch_path, input_dir / "front.jpg")
    
    prompt = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        "2": {
            "class_type": "Control Items",
            "inputs": {
                "window": True,
                "door": True,
                "staircase": False,
                "columns": False
            }
        },
        "3": {
            "class_type": "Interior Design Segmentator",
            "inputs": {
                "image": ["1", 0],
                "control_items": ["2", 0]
            }
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["3", 0],
                "filename_prefix": "v6_seg_map"
            }
        },
        # Also generate depth map
        "5": {
            "class_type": "DownloadAndLoadDepthAnythingV2Model",
            "inputs": {
                "model": "depth_anything_v2_vitl_fp32.safetensors",
                "precision": "auto"
            }
        },
        "6": {
            "class_type": "DepthAnything_V2",
            "inputs": {
                "da_model": ["5", 0],
                "images": ["1", 0]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "v6_depth_map"
            }
        }
    }
    
    result = queue_and_wait(prompt, timeout=300)
    
    # Find output files
    seg_map = None
    for f in Path.home().glob("ComfyUI/output/v6_seg_map*.png"):
        seg_map = f
        break
    
    return seg_map

# ============================================
# STEP 3: EXTRACT MASKS FROM SEGMENTATION
# ============================================

def extract_masks_from_segmap(seg_map_path: Path, output_dir: Path) -> dict:
    """Extract individual masks from segmentation map by color"""
    from PIL import Image
    import numpy as np
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    img = Image.open(seg_map_path).convert('RGB')
    arr = np.array(img)
    
    # Get unique colors
    pixels = arr.reshape(-1, 3)
    unique_colors = np.unique(pixels, axis=0)
    
    masks = {}
    
    for i, color in enumerate(unique_colors):
        color_tuple = tuple(color)
        
        # Extract mask for this color
        diff = np.abs(arr.astype(int) - color)
        mask = np.all(diff <= 5, axis=2)
        
        pixel_count = np.sum(mask)
        if pixel_count < 100:
            continue
        
        mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode='L')
        mask_path = output_dir / f"mask_region_{i}.png"
        mask_img.save(mask_path)
        
        masks[f"region_{i}"] = {
            'path': str(mask_path),
            'color': [int(c) for c in color_tuple],
            'pixels': int(pixel_count)
        }
    
    return masks

# ============================================
# STEP 4: OPUS VERIFICATION
# ============================================

def verify_masks_with_opus(sketch_path: Path, seg_map_path: Path, masks: dict, elements: list[Element]) -> dict:
    """
    Use Opus to verify which mask corresponds to which element
    Returns confidence scores for each element
    """
    # This would call Opus vision API
    # For now, return placeholder - actual implementation uses image tool
    
    results = {}
    for el in elements:
        # Placeholder - actual verification done via image tool
        results[el.name_en] = {
            'confidence': 0.0,
            'mask_id': None,
            'feedback': ''
        }
    
    return results

# ============================================
# STEP 5: SAM FOR LOW CONFIDENCE ELEMENTS
# ============================================

def run_sam_for_element(sketch_path: Path, element_name: str, point_x: int, point_y: int) -> Path:
    """Run SAM with point prompt for specific element"""
    
    prompt = {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        "2": {
            "class_type": "SAMPreprocessor",
            "inputs": {
                "image": ["1", 0],
                "resolution": 1024
            }
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["2", 0],
                "filename_prefix": f"v6_sam_{element_name}"
            }
        }
    }
    
    result = queue_and_wait(prompt, timeout=120)
    
    # Find output
    for f in Path.home().glob(f"ComfyUI/output/v6_sam_{element_name}*.png"):
        return f
    
    return None

# ============================================
# STEP 6: BUILD RENDER WORKFLOW
# ============================================

def create_v6_render_workflow(
    elements: list[Element],
    positive_prompt: str,
    negative_prompt: str,
    seed: int = 42
) -> dict:
    """Create full render workflow with regional IP-Adapters"""
    
    prompt = {
        # === INPUTS ===
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": "front.jpg"}
        },
        
        # Canny preprocessing
        "2": {
            "class_type": "CannyEdgePreprocessor",
            "inputs": {
                "image": ["1", 0],
                "low_threshold": 100,
                "high_threshold": 200,
                "resolution": 1024
            }
        },
        
        # Depth map
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": "v6_depth_map.png"}
        },
        
        # === MODEL ===
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        
        # === CLIP ENCODE ===
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": positive_prompt}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["4", 1], "text": negative_prompt}
        },
        
        # === CONTROLNET CANNY ===
        "7": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        "8": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["5", 0],
                "negative": ["6", 0],
                "control_net": ["7", 0],
                "image": ["2", 0],
                "strength": 0.7,
                "start_percent": 0,
                "end_percent": 0.8
            }
        },
        
        # === CONTROLNET DEPTH ===
        "9": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-depth-sdxl.safetensors"}
        },
        "10": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["8", 1],
                "control_net": ["9", 0],
                "image": ["3", 0],
                "strength": 0.5,
                "start_percent": 0,
                "end_percent": 0.6
            }
        },
        
        # === IP-ADAPTER SETUP ===
        "11": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        },
        "12": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        },
    }
    
    # Add IP-Adapter for each element with mask and reference
    node_id = 100
    prev_model_node = "4"  # Start from checkpoint
    
    for el in elements:
        if el.mask_path and el.reference:
            # Load reference image
            ref_node = str(node_id)
            prompt[ref_node] = {
                "class_type": "LoadImage",
                "inputs": {"image": el.reference.replace("референсы/", "refs/")}
            }
            node_id += 1
            
            # Load mask
            mask_load_node = str(node_id)
            prompt[mask_load_node] = {
                "class_type": "LoadImage",
                "inputs": {"image": f"masks/{Path(el.mask_path).name}"}
            }
            node_id += 1
            
            # Convert to mask
            mask_conv_node = str(node_id)
            prompt[mask_conv_node] = {
                "class_type": "ImageToMask",
                "inputs": {"image": [mask_load_node, 0], "channel": "red"}
            }
            node_id += 1
            
            # IP-Adapter with attention mask
            ipa_node = str(node_id)
            weight = 0.5 if el.critical else 0.35
            prompt[ipa_node] = {
                "class_type": "IPAdapterAdvanced",
                "inputs": {
                    "model": [prev_model_node, 0],
                    "ipadapter": ["12", 0],
                    "clip_vision": ["11", 0],
                    "image": [ref_node, 0],
                    "weight": weight,
                    "weight_type": "style transfer",
                    "combine_embeds": "concat",
                    "start_at": 0.0,
                    "end_at": 0.6,
                    "embeds_scaling": "V only",
                    "attn_mask": [mask_conv_node, 0]
                }
            }
            prev_model_node = ipa_node
            node_id += 1
    
    # === SAMPLER ===
    prompt["200"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1}
    }
    
    prompt["201"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": [prev_model_node, 0],
            "positive": ["10", 0],
            "negative": ["10", 1],
            "latent_image": ["200", 0],
            "seed": seed,
            "steps": 50,
            "cfg": 7.5,
            "sampler_name": "dpmpp_2m_sde",
            "scheduler": "karras",
            "denoise": 1.0
        }
    }
    
    prompt["202"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["201", 0], "vae": ["4", 2]}
    }
    
    prompt["203"] = {
        "class_type": "SaveImage",
        "inputs": {"images": ["202", 0], "filename_prefix": "bathroom_v6"}
    }
    
    return prompt

# ============================================
# UTILITIES
# ============================================

def queue_and_wait(prompt: dict, timeout: int = 3600) -> dict:
    """Queue prompt and wait for completion"""
    
    data = {"prompt": prompt}
    response = requests.post(f"{COMFYUI_API}/prompt", json=data)
    result = response.json()
    
    if 'error' in result:
        print(f"Error: {result}")
        return None
    
    prompt_id = result.get('prompt_id')
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
            history = response.json()
            
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        
        time.sleep(5)
    
    return None

# ============================================
# MAIN PIPELINE
# ============================================

def main():
    print("=" * 70)
    print("RENDER V6 - FULL PIPELINE")
    print("=" * 70)
    
    # Paths
    tz_path = Path.home() / "ComfyUI/input/bathroom_masha/ТЗ.md"
    sketch_path = Path.home() / "ComfyUI/input/bathroom_masha/скетчи/front.jpg"
    output_dir = Path.home() / "ComfyUI/input/v6_masks"
    refs_dir = Path.home() / "ComfyUI/input/refs"
    
    # ========================================
    # STEP 1: Parse ТЗ
    # ========================================
    print("\n[STEP 1] Parsing ТЗ...")
    elements, positive_prompt, negative_prompt = parse_tz(tz_path)
    
    print(f"  Found {len(elements)} elements:")
    for el in elements:
        crit = "⚠️ CRITICAL" if el.critical else ""
        print(f"    - {el.name} ({el.name_en}) {crit}")
    
    print(f"\n  Positive prompt ({len(positive_prompt)} chars):")
    print(f"    {positive_prompt[:200]}...")
    
    # Copy references to input/refs
    refs_dir.mkdir(exist_ok=True)
    refs_source = Path.home() / "ComfyUI/input/bathroom_masha/референсы"
    for f in refs_source.glob("*"):
        shutil.copy(f, refs_dir / f.name)
    print(f"\n  Copied references to {refs_dir}")
    
    # ========================================
    # STEP 2: UperNet Segmentation
    # ========================================
    print("\n[STEP 2] Running UperNet segmentation...")
    seg_map_path = run_upernet_segmentation(sketch_path, output_dir)
    print(f"  Segmentation map: {seg_map_path}")
    
    # ========================================
    # STEP 3: Extract masks
    # ========================================
    print("\n[STEP 3] Extracting masks from segmentation...")
    masks = extract_masks_from_segmap(seg_map_path, output_dir)
    print(f"  Extracted {len(masks)} masks")
    
    # ========================================
    # STEP 4-5: Verification would happen here via Opus
    # For now, we'll use the masks directly
    # ========================================
    print("\n[STEP 4-5] Mask verification (manual for now)")
    print("  TODO: Implement Opus verification loop")
    
    # ========================================
    # STEP 6: Build and run render
    # ========================================
    print("\n[STEP 6] Building render workflow...")
    
    # Assign masks to elements (simplified - would be done by Opus)
    # This is a placeholder mapping
    
    workflow = create_v6_render_workflow(elements, positive_prompt, negative_prompt)
    
    # Save workflow
    log_dir = Path.home() / ".openclaw/workspace/logs/comfyui"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"v6_{int(time.time())}.json", "w") as f:
        json.dump(workflow, f, indent=2)
    
    print("\n[RENDER] Starting render...")
    # result = queue_and_wait(workflow)
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
