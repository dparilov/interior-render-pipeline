#!/usr/bin/env python3
"""Adapt workflow to use available models and paths on IRP pod."""
import json
import sys

MODEL_MAP = {
    # Checkpoints
    "sd_xl_base_1.0.safetensors": "RealVisXL_V4.0.safetensors",
    "sdXL_v10RefinerVAEFix.safetensors": "RealVisXL_V4.0.safetensors",
    
    # ControlNets
    "control-lora-canny-rank256.safetensors": "controlnet-canny-sdxl.safetensors",
    "control-lora-depth-rank256.safetensors": "controlnet-depth-sdxl.safetensors",
    "diffusers_xl_canny_full.safetensors": "controlnet-canny-sdxl.safetensors",
    "diffusers_xl_depth_full.safetensors": "controlnet-depth-sdxl.safetensors",
}

PATH_REMOVE = [
    "/workspace/irp_bundle_s1/",
    "irp_bundle_s1/",
]

def adapt_workflow(wf):
    """Adapt workflow to use available resources."""
    adapted = {}
    
    for node_id, node in wf.items():
        new_node = {"class_type": node["class_type"], "inputs": {}}
        
        for input_name, input_value in node.get("inputs", {}).items():
            if isinstance(input_value, str):
                new_val = input_value
                
                # Model substitution
                if new_val in MODEL_MAP:
                    new_val = MODEL_MAP[new_val]
                
                # Path cleanup
                for path in PATH_REMOVE:
                    new_val = new_val.replace(path, "")
                
                new_node["inputs"][input_name] = new_val
            else:
                new_node["inputs"][input_name] = input_value
        
        adapted[node_id] = new_node
    
    return adapted

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: adapt_workflow.py <input.json> [output.json]")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    if "prompt" in data:
        wf = data["prompt"]
        wrapper = {k: v for k, v in data.items() if k != "prompt"}
    else:
        wf = data
        wrapper = {}
    
    adapted = adapt_workflow(wf)
    
    if wrapper:
        output = {**wrapper, "prompt": adapted}
    else:
        output = adapted
    
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Adapted to {sys.argv[2]}")
    else:
        print(json.dumps(output, indent=2))
