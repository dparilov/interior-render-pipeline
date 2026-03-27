#!/usr/bin/env python3
"""Quick test render via ComfyUI API."""
import json
import urllib.request
import time

COMFYUI_URL = "http://127.0.0.1:8188"

workflow = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 42,
            "steps": 20,
            "cfg": 7.5,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "RealVisXL_V4.0.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": 1024,
            "height": 768,
            "batch_size": 1
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "photorealistic interior photograph, modern bathroom, white vertical tile walls, navy blue geometric floor tiles, dark gray vanity cabinet with white sink, chrome faucet, large mirror with warm LED backlight, bathtub with shower, warm diffused sunlight through window, high-end interior design magazine style, sharp details, professional photography, 8k uhd",
            "clip": ["4", 1]
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "cartoon, anime, drawing, sketch, low quality, blurry, distorted, deformed, watermark, text, oversaturated, ugly, bad anatomy",
            "clip": ["4", 1]
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "test_bathroom",
            "images": ["8", 0]
        }
    }
}

print("Queuing prompt...")
data = json.dumps({"prompt": workflow}).encode('utf-8')
req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data)
req.add_header('Content-Type', 'application/json')

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    prompt_id = result["prompt_id"]
    print(f"Prompt ID: {prompt_id}")

print("Waiting for completion (CPU mode, ~5-10 min)...")
start = time.time()
while True:
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
        history = json.loads(response.read())
    if prompt_id in history:
        elapsed = time.time() - start
        print(f"Done in {elapsed:.1f}s!")
        outputs = history[prompt_id].get("outputs", {})
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    print(f"Output: ~/ComfyUI/output/{img['filename']}")
        break
    time.sleep(5)
    print(f"  {int(time.time()-start)}s...", end=" ", flush=True)
