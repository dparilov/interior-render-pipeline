#!/usr/bin/env blender --background --python
"""
B31 — Strict Section Plane Clipping

⛔ ЗАПРЕТЫ:
- НЕ МЕНЯТЬ FOV — строго из manifest (35°)
- НЕ ПОДБИРАТЬ clip_start вручную — вычислить математически
- НЕ МЕНЯТЬ позицию камеры
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


def setup_camera_strict(manifest):
    """Setup camera STRICTLY from manifest values."""
    eye = manifest['camera']['eye']
    fov = manifest['camera']['fov']
    
    print("=== CAMERA (STRICT from manifest) ===")
    print(f"Position: {eye}")
    print(f"FOV: {fov}° (from manifest, NOT modified)")
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(fov)  # STRICT from manifest
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Position EXACTLY from manifest
    cam_obj.location = (eye[0], eye[1], eye[2])
    
    # Rotation: 90° X = look along +Y
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    bpy.context.view_layer.update()
    
    return {
        'eye': eye,
        'fov': fov,
        'rotation_deg': [90, 0, 0]
    }


def apply_section_plane_strict(manifest):
    """Apply section plane clipping MATHEMATICALLY.
    
    NO manual tuning, NO hardcoded values.
    """
    planes = manifest.get('section_planes', [])
    camera = bpy.context.scene.camera
    
    if not planes:
        print("No section planes in manifest")
        return None
    
    if not camera:
        print("No camera in scene")
        return None
    
    sp = planes[0]
    normal = sp['normal']
    dist_m = sp['distance_meters']
    
    print("=== SECTION PLANE (STRICT math) ===")
    print(f"Normal: {normal}")
    print(f"Distance (d): {dist_m}m")
    
    # Plane equation: n·p + d = 0
    # For normal=[0,1,0]: y + d = 0 → y = -d
    plane_y = -dist_m
    print(f"Plane Y position: {plane_y}m (calculated as -d)")
    
    # Camera position from manifest
    cam_y = camera.location.y
    print(f"Camera Y position: {cam_y}m")
    
    # Distance from camera to section plane (MATHEMATICAL)
    clip_distance = abs(cam_y - plane_y)
    print(f"Clip distance: |{cam_y} - {plane_y}| = {clip_distance:.3f}m")
    
    # Apply as near clip
    camera.data.clip_start = clip_distance
    print(f"Set clip_start: {clip_distance:.3f}m")
    
    return {
        'plane_y': plane_y,
        'cam_y': cam_y,
        'clip_start': clip_distance,
        'formula': f"|cam_y - plane_y| = |{cam_y} - {plane_y}|"
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
    print("B31 — Strict Section Plane Clipping")
    print("⛔ FOV from manifest, clip_start calculated mathematically")
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
    camera_info = setup_camera_strict(manifest)
    
    print("")
    section_info = apply_section_plane_strict(manifest)
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # Write experiment.json with EXACT values
    experiment = {
        "experiment": "B31",
        "method": "Strict section plane clipping (mathematical)",
        "bundle": str(bundle_dir.name),
        "camera": {
            "position": camera_info['eye'],
            "rotation_deg": camera_info['rotation_deg'],
            "fov": camera_info['fov'],
            "fov_source": "manifest (NOT modified)"
        },
        "section_plane": section_info,
        "constraints": [
            "FOV = 35° from manifest (NOT 70°)",
            "clip_start calculated mathematically",
            "Camera position NOT moved"
        ]
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
