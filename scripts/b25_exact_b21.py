#!/usr/bin/env blender --background --python
"""
B25 — ВОСПРОИЗВЕСТИ B21 ТОЧНО

Camera EXACT values from task:
camera.location = (1.147482, 1.947995, 4.441579)
camera.rotation_euler = (1.537196, -0.001400, 0.000000)
camera.data.angle = math.radians(35.0)
"""

import bpy
import os
import sys
import json
import math
from pathlib import Path


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bundle', '-b', required=True, help='Bundle directory')
    parser.add_argument('--output', '-o', required=True, help='Output image path')
    parser.add_argument('--samples', type=int, default=64, help='Render samples')
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    mesh_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
    print(f"Imported GLB: {mesh_count} meshes")
    return mesh_count


def setup_camera():
    """Setup camera EXACTLY as specified in task B25."""
    
    # EXACT values from task - DO NOT MODIFY
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # EXACT position
    cam_obj.location = (1.147482, 1.947995, 4.441579)
    
    # EXACT rotation
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (1.537196, -0.001400, 0.000000)
    
    # EXACT FOV
    cam_obj.data.angle = math.radians(35.0)
    
    # Clip settings
    cam_obj.data.clip_start = 0.1
    cam_obj.data.clip_end = 100
    
    print("Camera (EXACT from task B25):")
    print(f"  location = (1.147482, 1.947995, 4.441579)")
    print(f"  rotation_euler = (1.537196, -0.001400, 0.000000)")
    print(f"  angle = radians(35.0)")
    
    bpy.context.view_layer.update()
    return cam_obj


def setup_lighting():
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    fill_data = bpy.data.lights.new("Fill", 'AREA')
    fill_data.energy = 100
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.location = (-3, -3, 2)
    bpy.context.scene.collection.objects.link(fill)
    
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.8, 0.85, 0.9, 1)
    bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def render(output_path, samples=64):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
    except:
        pass
    
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = output_path
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B25 — ВОСПРОИЗВЕСТИ B21 ТОЧНО")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model' / 'model.glb'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    clear_scene()
    
    print("\n=== IMPORT ===")
    import_glb(str(glb_path))
    
    print("\n=== CAMERA ===")
    setup_camera()
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    experiment = {
        "experiment": "B25",
        "method": "Exact B21 camera reproduction",
        "camera": {
            "location": [1.147482, 1.947995, 4.441579],
            "rotation_euler": [1.537196, -0.001400, 0.000000],
            "angle_degrees": 35.0
        },
        "note": "Exact values from task B25, copied verbatim"
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
