#!/usr/bin/env blender --background --python
"""
B32 — Correct FOV Conversion (Vertical → Horizontal)

SketchUp FOV = 35° vertical (fov_is_height = true)
For 16:9 aspect, horizontal FOV = ~58.3°
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


def convert_fov_vertical_to_horizontal(vfov_deg, aspect):
    """Convert vertical FOV to horizontal FOV.
    
    hfov = 2 * atan(tan(vfov/2) * aspect)
    """
    vfov_rad = math.radians(vfov_deg)
    hfov_rad = 2 * math.atan(math.tan(vfov_rad / 2) * aspect)
    return math.degrees(hfov_rad)


def setup_camera_correct_fov(manifest):
    """Setup camera with correct FOV conversion."""
    eye = manifest['camera']['eye']
    fov_vertical = manifest['camera']['fov']
    
    # Aspect ratio
    width = manifest.get('image_size', {}).get('width', 1920)
    height = manifest.get('image_size', {}).get('height', 1080)
    aspect = width / height
    
    # Convert vertical FOV to horizontal FOV
    fov_horizontal = convert_fov_vertical_to_horizontal(fov_vertical, aspect)
    
    print("=== CAMERA (Correct FOV) ===")
    print(f"Position: {eye}")
    print(f"FOV vertical (SketchUp): {fov_vertical}°")
    print(f"Aspect ratio: {aspect:.3f} ({width}x{height})")
    print(f"FOV horizontal (calculated): {fov_horizontal:.1f}°")
    
    cam_data = bpy.data.cameras.new("Camera")
    
    # Use HORIZONTAL sensor fit with horizontal FOV
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.angle = math.radians(fov_horizontal)
    
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Position from manifest
    cam_obj.location = (eye[0], eye[1], eye[2])
    
    # Rotation: 90° X = look along +Y
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    bpy.context.view_layer.update()
    
    return {
        'eye': eye,
        'fov_vertical': fov_vertical,
        'fov_horizontal': round(fov_horizontal, 1),
        'aspect': aspect,
        'sensor_fit': 'HORIZONTAL'
    }


def apply_section_plane_strict(manifest):
    """Apply section plane clipping mathematically."""
    planes = manifest.get('section_planes', [])
    camera = bpy.context.scene.camera
    
    if not planes or not camera:
        print("No section planes or camera")
        return None
    
    sp = planes[0]
    dist_m = sp['distance_meters']
    
    # Plane equation: y + d = 0 → y = -d
    plane_y = -dist_m
    cam_y = camera.location.y
    
    # Distance from camera to section plane
    clip_distance = abs(cam_y - plane_y)
    
    print("=== SECTION PLANE ===")
    print(f"Plane Y: {plane_y}m")
    print(f"Camera Y: {cam_y:.2f}m")
    print(f"Clip start: {clip_distance:.3f}m")
    
    camera.data.clip_start = clip_distance
    
    return {
        'plane_y': plane_y,
        'clip_start': round(clip_distance, 3)
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
    print("B32 — Correct FOV Conversion (Vertical → Horizontal)")
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
    camera_info = setup_camera_correct_fov(manifest)
    
    print("")
    section_info = apply_section_plane_strict(manifest)
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # Write experiment.json
    experiment = {
        "experiment": "B32",
        "method": "Correct FOV conversion (vertical → horizontal)",
        "bundle": str(bundle_dir.name),
        "camera": camera_info,
        "section_plane": section_info,
        "fov_formula": "hfov = 2 * atan(tan(vfov/2) * aspect)"
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
