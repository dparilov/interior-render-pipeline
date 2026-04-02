#!/usr/bin/env blender --background --python
"""
B33 — clip_start from Walls Y, not Section Plane

Section plane Y = 1.3m, but walls Y min = 1.143m.
Gap = 16 cm — this clips bathtub edge!

clip_start = |cam_y - walls_y| = |-4.44 - 1.143| = 5.58m
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
    """Convert vertical FOV to horizontal FOV."""
    vfov_rad = math.radians(vfov_deg)
    hfov_rad = 2 * math.atan(math.tan(vfov_rad / 2) * aspect)
    return math.degrees(hfov_rad)


def setup_camera_correct_fov(manifest):
    """Setup camera with correct FOV conversion."""
    eye = manifest['camera']['eye']
    fov_vertical = manifest['camera']['fov']
    
    width = manifest.get('image_size', {}).get('width', 1920)
    height = manifest.get('image_size', {}).get('height', 1080)
    aspect = width / height
    
    fov_horizontal = convert_fov_vertical_to_horizontal(fov_vertical, aspect)
    
    print("=== CAMERA ===")
    print(f"Position: {eye}")
    print(f"FOV: {fov_vertical}° vertical → {fov_horizontal:.1f}° horizontal")
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.angle = math.radians(fov_horizontal)
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
        'fov_horizontal': round(fov_horizontal, 1)
    }


def apply_walls_clip(manifest):
    """Apply clip_start from walls Y min, not section plane.
    
    Walls Y min = 1.143m (from SketchUp)
    Section plane Y = 1.3m
    Gap = 16 cm — clips bathtub edge!
    """
    camera = bpy.context.scene.camera
    
    if not camera:
        print("No camera in scene")
        return None
    
    # Walls Y min from SketchUp analysis
    walls_y_min = 1.143  # meters
    
    # Compare with section plane
    planes = manifest.get('section_planes', [])
    section_plane_y = -planes[0]['distance_meters'] if planes else None
    
    cam_y = camera.location.y
    
    # Calculate clip_start from walls, not section plane
    clip_start = abs(cam_y - walls_y_min)
    
    print("=== CLIP START (from Walls Y) ===")
    print(f"Walls Y min: {walls_y_min}m")
    if section_plane_y:
        print(f"Section plane Y: {section_plane_y}m")
        print(f"Gap: {abs(section_plane_y - walls_y_min)*100:.0f} cm")
    print(f"Camera Y: {cam_y:.2f}m")
    print(f"Clip start: {clip_start:.2f}m")
    
    camera.data.clip_start = clip_start
    
    return {
        'walls_y_min': walls_y_min,
        'section_plane_y': section_plane_y,
        'gap_cm': round(abs(section_plane_y - walls_y_min) * 100, 1) if section_plane_y else None,
        'clip_start': round(clip_start, 2)
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
    print("B33 — clip_start from Walls Y, not Section Plane")
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
    clip_info = apply_walls_clip(manifest)
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    experiment = {
        "experiment": "B33",
        "method": "clip_start from Walls Y, not Section Plane",
        "bundle": str(bundle_dir.name),
        "camera": camera_info,
        "clip": clip_info,
        "note": "Section plane creates 16cm gap that clips bathtub edge"
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
