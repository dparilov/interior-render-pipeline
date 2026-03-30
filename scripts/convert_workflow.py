#!/usr/bin/env python3
"""Convert ComfyUI UI workflow format to API format.

UI format: {"node_name": {"class_type": ..., "inputs": ...}}
API format: {"1": {"class_type": ..., "inputs": ...}}

Links in inputs change from ["node_name", slot] to ["node_id", slot]
"""
import json
import sys

def convert_workflow(ui_workflow):
    """Convert named-key workflow to numeric-key API format."""
    if not ui_workflow:
        return {}
    
    # Check if already in API format (numeric keys)
    first_key = list(ui_workflow.keys())[0]
    if first_key.isdigit():
        return ui_workflow  # Already API format
    
    # Create name -> id mapping
    name_to_id = {}
    for i, name in enumerate(ui_workflow.keys(), start=1):
        name_to_id[name] = str(i)
    
    # Convert nodes
    api_workflow = {}
    for name, node in ui_workflow.items():
        node_id = name_to_id[name]
        new_node = {
            "class_type": node.get("class_type"),
            "inputs": {}
        }
        
        # Convert inputs, updating references
        for input_name, input_value in node.get("inputs", {}).items():
            if isinstance(input_value, list) and len(input_value) == 2:
                ref_name, slot = input_value
                if isinstance(ref_name, str) and ref_name in name_to_id:
                    # Convert node reference
                    new_node["inputs"][input_name] = [name_to_id[ref_name], slot]
                else:
                    new_node["inputs"][input_name] = input_value
            else:
                new_node["inputs"][input_name] = input_value
        
        api_workflow[node_id] = new_node
    
    return api_workflow

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: convert_workflow.py <input.json> [output.json]")
        sys.exit(1)
    
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    # Handle wrapped format
    if "prompt" in data:
        workflow = data["prompt"]
        wrapper = {k: v for k, v in data.items() if k != "prompt"}
    else:
        workflow = data
        wrapper = {}
    
    converted = convert_workflow(workflow)
    
    # Output
    if wrapper:
        output = {**wrapper, "prompt": converted}
    else:
        output = converted
    
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Converted to {sys.argv[2]}")
    else:
        print(json.dumps(output))
