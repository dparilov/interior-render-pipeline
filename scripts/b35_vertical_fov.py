#!/usr/bin/env blender --background --python
"""
B35 — Vertical FOV (sensor_fit = VERTICAL)

SketchUp cam.fov_is_height? = true → vertical FOV = 35°
Test: Apply vertical FOV directly instead of converting to horizontal.
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


def setup_camera_vertical_fov(manifest):
    """Setup camera with vertical FOV directly from SketchUp."""
    eye = manifest['camera']['eye']
    fov_vertical = manifest['camera']['fov']  # 35° vertical
    
    print("=== CAMERA (Vertical FOV) ===")
    print(f"Position: {eye}")
    print(f"FOV: {fov_vertical}° vertical (direct from SketchUp)")
    print(f"sensor_fit: VERTICAL")
    
    cam_data = bpy.data.cameras.new("Camera")
    
    # Use VERTICAL sensor fit with vertical FOV directly
    cam_data.sensor_fit = 'VERTICAL'
    cam_data.angle = math.radians(fov_vertical)  # 35° as-is
    
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    cam_obj.location = (eye[0], eye[1], eye[2])
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    bpy.context.view_layer.update()
    
    return {
        'eye': eye,
        'fov_vertical': fov_vertical,
        'sensor_fit': 'VERTICAL',
        'original_y': eye[1]
    }


def apply_wall_offset_and_clip():
    """Apply wall offset and clip_start (same as B34)."""
    camera = bpy.context.scene.camera
    
    # Wall geometry (hardcoded, same as B34)
    section_plane_y = 1.3
    walls_outer_y = 1.143
    wall_thickness = section_plane_y - walls_outer_y  # 0.157m
    
    original_y = camera.location.y
    
    # Offset camera back by wall thickness
    camera.location.y -= wall_thickness
    adjusted_y = camera.location.y
    
    # Calculate clip_start
    clip_start = abs(adjusted_y - section_plane_y)
    camera.data.clip_start = clip_start
    
    print("\n=== WALL OFFSET (same as B34) ===")
    print(f"Wall thickness: {wall_thickness:.3f}m")
    print(f"Camera Y: {original_y:.3f} → {adjusted_y:.3f}m")
    print(f"clip_start: {clip_start:.3f}m")
    
    bpy.context.view_layer.update()
    
    return {
        'wall_thickness': round(wall_thickness, 3),
        'camera_y_original': round(original_y, 3),
        'camera_y_adjusted': round(adjusted_y, 3),
        'clip_start': round(clip_start, 3)
    }


def setup_lighting():
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    fill_data = bpy.data.lights.new("Fill", 'AREA')
    fill_data.energy = 100
    fill_data.size = 2
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
    print("B35 — Vertical FOV (sensor_fit = VERTICAL)")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    manifest_path = bundle_dir / 'manifest.json'
    
    glb_path = bundle_dir / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model' / 'model.glb'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    
    clear_scene()
    
    print("\n=== IMPORT ===")
    import_glb(str(glb_path))
    
    print("")
    camera_info = setup_camera_vertical_fov(manifest)
    
    offset_info = apply_wall_offset_and_clip()
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    experiment = {
        "experiment": "B35",
        "method": "Vertical FOV directly from SketchUp",
        "bundle": str(bundle_dir.name),
        "camera": camera_info,
        "offset": offset_info,
        "comparison": {
            "B34": "sensor_fit=HORIZONTAL, angle=58.5° (converted)",
            "B35": "sensor_fit=VERTICAL, angle=35° (direct)"
        }
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
