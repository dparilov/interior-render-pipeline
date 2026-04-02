#!/usr/bin/env blender --background --python
"""B37 — FOV 40° test"""

import bpy
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
    parser.add_argument('--bundle', '-b', required=True)
    parser.add_argument('--output', '-o', required=True)
    parser.add_argument('--samples', type=int, default=64)
    return parser.parse_args(argv)

def main():
    args = parse_args()
    
    print("=" * 60)
    print("B37 — FOV 40° test")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(bundle_dir / 'manifest.json') as f:
        manifest = json.load(f)
    
    # Clear and import
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    print(f"Imported GLB")
    
    # Camera
    eye = manifest['camera']['eye']
    fov_vertical = 40  # TEST VALUE (not 35!)
    width, height = 1066, 1239
    aspect = width / height
    fov_horizontal = 2 * math.degrees(math.atan(math.tan(math.radians(fov_vertical / 2)) * aspect))
    
    print(f"\nFOV: {fov_vertical}° vertical → {fov_horizontal:.1f}° horizontal")
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.angle = math.radians(fov_horizontal)
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    cam_obj.location = (eye[0], eye[1], eye[2])
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Wall offset (same as B34)
    wall_thickness = 0.157
    cam_obj.location.y -= wall_thickness
    clip_start = abs(cam_obj.location.y - 1.3)
    cam_data.clip_start = clip_start
    
    print(f"Camera Y: {cam_obj.location.y:.3f}m, clip_start: {clip_start:.3f}m")
    
    bpy.context.view_layer.update()
    
    # Lighting
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'AREA'))
    fill.data.energy = 100
    fill.data.size = 2
    fill.location = (-3, -3, 2)
    bpy.context.scene.collection.objects.link(fill)
    
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.85, 0.9, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    bpy.context.scene.world = world
    
    # Render
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = False
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for d in prefs.devices: d.use = True
        scene.cycles.device = 'GPU'
    except: pass
    
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = args.output
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {args.output}")
    
    # Experiment
    exp = {
        "experiment": "B37",
        "method": "FOV 40° test",
        "fov_vertical": fov_vertical,
        "fov_horizontal": round(fov_horizontal, 1),
        "resolution": [width, height],
        "clip_start": round(clip_start, 3)
    }
    with open(output_dir / 'experiment.json', 'w') as f:
        json.dump(exp, f, indent=2)
    
    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
