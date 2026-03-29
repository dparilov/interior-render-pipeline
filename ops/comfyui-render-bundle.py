#!/usr/bin/env python3
"""
ComfyUI Bundle Render — использует authoritative маски из SketchUp
Без UperNet/SAM сегментации!

Использование:
  python3 comfyui-render-bundle.py --bundle ~/ComfyUI/input/bathroom_masha/bundle_manifest.json --steps 30
"""

import argparse
import json
import urllib.request
import time
import sys
import os
import random
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://127.0.0.1:8188"


def queue_prompt(workflow):
    """Отправляет workflow в ComfyUI"""
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read())


def build_workflow_with_masks(bundle, params):
    """
    Строит workflow с Regional IP-Adapter для каждой маски из bundle.
    
    Архитектура:
    - SDXL checkpoint
    - Canny ControlNet (структура)
    - Для каждого entity с референсом: IPAdapterAdvanced + attention mask
    """
    
    base_dir = os.path.dirname(bundle['_path'])
    
    # Проверяем скетч
    sketch_path = os.path.join(base_dir, bundle['base_image'])
    if not os.path.exists(sketch_path):
        raise FileNotFoundError(f"Скетч не найден: {sketch_path}")
    
    # Относительный путь для ComfyUI (от input/)
    comfy_input = os.path.expanduser("~/ComfyUI/input")
    sketch_rel = os.path.relpath(sketch_path, comfy_input)
    
    seed = random.randint(0, 2**32 - 1)
    
    workflow = {
        # Загрузка моделей
        "checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        "vae": {
            "class_type": "VAELoader", 
            "inputs": {"vae_name": "sdxl_vae.safetensors"}
        },
        "controlnet_canny": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        
        # Загрузка скетча
        "load_sketch": {
            "class_type": "LoadImage",
            "inputs": {"image": sketch_rel}
        },
        
        # Canny preprocessing
        "canny_preprocess": {
            "class_type": "Canny",
            "inputs": {
                "image": ["load_sketch", 0],
                "low_threshold": 0.1,
                "high_threshold": 0.4
            }
        },
        
        # Positive prompt — собираем из bundle prompts
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": build_prompt_from_bundle(bundle)
            }
        },
        
        # Negative prompt
        "negative": {
            "class_type": "CLIPTextEncode", 
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": "cartoon, anime, drawing, sketch, CGI, 3D render, low quality, blurry, distorted, deformed, watermark, text"
            }
        },
        
        # Apply Canny ControlNet
        "apply_controlnet": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["positive", 0],
                "negative": ["negative", 0],
                "control_net": ["controlnet_canny", 0],
                "image": ["canny_preprocess", 0],
                "strength": params['cn_strength'],
                "start_percent": 0.0,
                "end_percent": 0.8
            }
        },
        
        # Empty latent
        "empty_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": params['size'],
                "height": params['size'],
                "batch_size": 1
            }
        },
    }
    
    # IP-Adapter models (загружаем один раз)
    if not params['no_ipadapter']:
        workflow["ipadapter_model"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
        }
        workflow["clip_vision"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}
        }
    
    # Строим цепочку IP-Adapters с масками
    prev_model = ["checkpoint", 0]
    ip_count = 0
    
    if not params['no_ipadapter']:
        for entity in bundle['entities']:
            if 'reference' not in entity:
                continue  # Пропускаем entities без референсов
            
            name = entity['name']
            ref_path = os.path.join(base_dir, entity['reference'])
            mask_path = os.path.join(base_dir, entity['mask'])
            
            if not os.path.exists(ref_path):
                print(f"⚠️  Референс не найден: {ref_path}")
                continue
            if not os.path.exists(mask_path):
                print(f"⚠️  Маска не найдена: {mask_path}")
                continue
            
            ref_rel = os.path.relpath(ref_path, comfy_input)
            mask_rel = os.path.relpath(mask_path, comfy_input)
            
            # Load reference image
            workflow[f"load_ref_{name}"] = {
                "class_type": "LoadImage",
                "inputs": {"image": ref_rel}
            }
            
            # Load mask (as MASK type, not IMAGE)
            workflow[f"load_mask_{name}"] = {
                "class_type": "LoadImageMask",
                "inputs": {
                    "image": mask_rel,
                    "channel": "red"  # Use red channel for grayscale masks
                }
            }
            
            # IPAdapter с attention mask
            weight = 0.6 if entity.get('coverage_pct', 0) > 5 else 0.4  # Больше coverage = больше weight
            
            workflow[f"ipadapter_{name}"] = {
                "class_type": "IPAdapterAdvanced",
                "inputs": {
                    "model": prev_model,
                    "ipadapter": ["ipadapter_model", 0],
                    "clip_vision": ["clip_vision", 0],
                    "image": [f"load_ref_{name}", 0],
                    "attn_mask": [f"load_mask_{name}", 0],  # KEY: attention mask!
                    "weight": weight,
                    "weight_type": "linear",
                    "start_at": 0.0,
                    "end_at": 0.8,
                    "unfold_batch": False,
                    "combine_embeds": "concat",
                    "embeds_scaling": "V only"
                }
            }
            
            prev_model = [f"ipadapter_{name}", 0]
            ip_count += 1
            print(f"  ✅ {name}: mask={entity['coverage_pct']:.1f}%, weight={weight}")
    
    # Sampler
    workflow["sampler_base"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": prev_model,
            "positive": ["apply_controlnet", 0],
            "negative": ["apply_controlnet", 1],
            "latent_image": ["empty_latent", 0],
            "seed": seed,
            "steps": params['steps'],
            "cfg": params['cfg'],
            "sampler_name": "dpmpp_2m_sde",
            "scheduler": "karras",
            "denoise": 1.0
        }
    }
    
    # VAE Decode
    workflow["vae_decode"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["sampler_base", 0],
            "vae": ["vae", 0]
        }
    }
    
    # Save
    workflow["save"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["vae_decode", 0],
            "filename_prefix": params['output']
        }
    }
    
    return workflow, ip_count


def build_prompt_from_bundle(bundle):
    """Собирает промпт из промптов всех entities"""
    
    base_prompt = """ULTRA HIGH QUALITY photorealistic interior photograph. 
Professional architectural photography, 8K resolution, tack sharp details.
Natural soft daylight, warm ambient lighting, gentle shadows.
Magazine editorial quality, Architectural Digest style."""
    
    # Добавляем промпты элементов
    element_prompts = []
    for entity in bundle['entities']:
        if entity.get('prompt'):
            element_prompts.append(entity['prompt'])
    
    if element_prompts:
        base_prompt += "\n\nELEMENTS:\n" + "\n".join(f"- {p}" for p in element_prompts)
    
    return base_prompt


def main():
    parser = argparse.ArgumentParser(description='ComfyUI Bundle Render')
    parser.add_argument('--bundle', required=True, help='Path to bundle_manifest.json')
    parser.add_argument('--output', default='bundle_render', help='Output filename prefix')
    parser.add_argument('--steps', type=int, default=30)
    parser.add_argument('--cfg', type=float, default=7.5)
    parser.add_argument('--cn-strength', type=float, default=0.5, help='Canny ControlNet strength')
    parser.add_argument('--size', type=int, default=1024)
    parser.add_argument('--no-ipadapter', action='store_true', help='Disable IP-Adapter (prompt + ControlNet only)')
    
    args = parser.parse_args()
    
    # Загружаем bundle
    print(f"📦 Loading bundle: {args.bundle}")
    with open(args.bundle) as f:
        bundle = json.load(f)
    bundle['_path'] = args.bundle
    
    print(f"   Version: {bundle.get('version', 'unknown')}")
    print(f"   Source: {bundle.get('source', 'unknown')}")
    print(f"   Entities: {len(bundle['entities'])}")
    print(f"   Base image: {bundle.get('base_image', 'N/A')}")
    
    # Параметры
    params = {
        'output': args.output,
        'steps': args.steps,
        'cfg': args.cfg,
        'cn_strength': args.cn_strength,
        'size': args.size,
        'no_ipadapter': args.no_ipadapter,
    }
    
    # Проверяем ComfyUI
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        print("✅ ComfyUI доступен")
    except:
        print("❌ ComfyUI не доступен", file=sys.stderr)
        sys.exit(1)
    
    # Строим workflow
    print(f"\n🔨 Building workflow with regional IP-Adapters...")
    workflow, ip_count = build_workflow_with_masks(bundle, params)
    
    print(f"\n📊 Workflow summary:")
    print(f"   Steps: {params['steps']}")
    print(f"   Size: {params['size']}x{params['size']}")
    print(f"   ControlNet strength: {params['cn_strength']}")
    print(f"   IP-Adapters with masks: {ip_count}")
    
    # Отправляем
    print(f"\n📤 Sending to ComfyUI...")
    result = queue_prompt(workflow)
    prompt_id = result.get('prompt_id', 'unknown')
    print(f"🆔 Prompt ID: {prompt_id}")
    
    # ETA
    eta_min = params['steps'] * 50 / 60  # ~50 sec/step on CPU
    print(f"⏱️  ETA: ~{eta_min:.0f} minutes on CPU")
    print(f"\n💡 Check progress: curl -s http://127.0.0.1:8188/queue")
    print(f"💡 Output: ~/ComfyUI/output/{params['output']}_*.png")


if __name__ == '__main__':
    main()
