#!/usr/bin/env python3
"""
ComfyUI Render with Logging
Logs all parameters, models, and timing to a file for debugging.
"""
import json
import urllib.request
import time
import sys
import os
from datetime import datetime

COMFYUI_URL = "http://127.0.0.1:8188"
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs/comfyui")
os.makedirs(LOG_DIR, exist_ok=True)

def log_render(workflow: dict, metadata: dict = None):
    """Submit workflow and log everything."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{LOG_DIR}/render_{timestamp}.json"
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "status": "started",
        "metadata": metadata or {},
        "workflow_summary": extract_workflow_summary(workflow),
        "full_workflow": workflow,
        "timing": {},
        "result": None,
        "error": None
    }
    
    # Log start
    print(f"📝 Logging to: {log_file}")
    save_log(log_file, log_entry)
    
    # Submit to ComfyUI
    start_time = time.time()
    try:
        data = json.dumps({"prompt": workflow}).encode('utf-8')
        req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            prompt_id = result["prompt_id"]
            log_entry["prompt_id"] = prompt_id
            print(f"✅ Queued: {prompt_id}")
    except Exception as e:
        log_entry["status"] = "queue_failed"
        log_entry["error"] = str(e)
        save_log(log_file, log_entry)
        print(f"❌ Queue failed: {e}")
        return None
    
    # Wait for completion
    print("⏳ Waiting for completion...")
    while True:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as response:
                history = json.loads(response.read())
            
            if prompt_id in history:
                elapsed = time.time() - start_time
                log_entry["timing"]["total_seconds"] = round(elapsed, 2)
                log_entry["timing"]["total_human"] = f"{int(elapsed//60)}m {int(elapsed%60)}s"
                
                # Check for errors
                if history[prompt_id].get("status", {}).get("status_str") == "error":
                    log_entry["status"] = "failed"
                    log_entry["error"] = history[prompt_id].get("status", {}).get("messages", [])
                else:
                    log_entry["status"] = "completed"
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            log_entry["result"] = {
                                "images": [f"~/ComfyUI/output/{img['filename']}" for img in node_output["images"]]
                            }
                
                save_log(log_file, log_entry)
                print(f"✅ Done in {log_entry['timing']['total_human']}")
                print(f"📄 Log: {log_file}")
                return log_entry
                
        except Exception as e:
            pass
        
        time.sleep(5)
        elapsed = time.time() - start_time
        print(f"  {int(elapsed)}s...", end=" ", flush=True)


def extract_workflow_summary(workflow: dict) -> dict:
    """Extract key parameters from workflow for easy reading."""
    summary = {
        "models": [],
        "controlnets": [],
        "ipadapter": None,
        "parameters": {},
        "prompts": {}
    }
    
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        
        # Checkpoints
        if "CheckpointLoader" in class_type:
            summary["models"].append({
                "type": "checkpoint",
                "name": inputs.get("ckpt_name", "unknown")
            })
        
        # VAE
        if "VAELoader" in class_type:
            summary["models"].append({
                "type": "vae", 
                "name": inputs.get("vae_name", "unknown")
            })
        
        # ControlNet
        if "ControlNetLoader" in class_type or "ControlNetApply" in class_type:
            cn_info = {
                "name": inputs.get("control_net_name", "unknown"),
                "strength": inputs.get("strength", "unknown")
            }
            summary["controlnets"].append(cn_info)
        
        # IP-Adapter
        if "IPAdapter" in class_type:
            summary["ipadapter"] = {
                "weight": inputs.get("weight", inputs.get("scale", "unknown")),
                "model": inputs.get("ipadapter_file", "unknown")
            }
        
        # KSampler parameters
        if "KSampler" in class_type:
            summary["parameters"]["steps"] = inputs.get("steps")
            summary["parameters"]["cfg"] = inputs.get("cfg")
            summary["parameters"]["sampler"] = inputs.get("sampler_name")
            summary["parameters"]["scheduler"] = inputs.get("scheduler")
            summary["parameters"]["denoise"] = inputs.get("denoise")
            summary["parameters"]["seed"] = inputs.get("seed")
        
        # Latent size
        if "EmptyLatentImage" in class_type:
            summary["parameters"]["width"] = inputs.get("width")
            summary["parameters"]["height"] = inputs.get("height")
        
        # Prompts
        if "CLIPTextEncode" in class_type:
            text = inputs.get("text", "")
            if text:
                if len(summary["prompts"]) == 0:
                    summary["prompts"]["positive"] = text[:500] + "..." if len(text) > 500 else text
                else:
                    summary["prompts"]["negative"] = text[:300] + "..." if len(text) > 300 else text
    
    return summary


def save_log(path: str, data: dict):
    """Save log entry to file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def print_summary(log_entry: dict):
    """Print human-readable summary."""
    summary = log_entry.get("workflow_summary", {})
    
    print("\n" + "="*60)
    print("📊 RENDER SUMMARY")
    print("="*60)
    
    print("\n🎨 Models:")
    for m in summary.get("models", []):
        print(f"   - {m['type']}: {m['name']}")
    
    print("\n🎛️ ControlNets:")
    for cn in summary.get("controlnets", []):
        print(f"   - {cn['name']} (strength: {cn['strength']})")
    
    if summary.get("ipadapter"):
        print(f"\n🖼️ IP-Adapter: weight={summary['ipadapter']['weight']}")
    
    print("\n⚙️ Parameters:")
    params = summary.get("parameters", {})
    for k, v in params.items():
        if v is not None:
            print(f"   - {k}: {v}")
    
    print("\n📝 Prompts:")
    prompts = summary.get("prompts", {})
    if prompts.get("positive"):
        print(f"   Positive: {prompts['positive'][:100]}...")
    if prompts.get("negative"):
        print(f"   Negative: {prompts['negative'][:100]}...")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Test with a simple workflow
    print("ComfyUI Render Logger ready")
    print(f"Logs will be saved to: {LOG_DIR}/")
