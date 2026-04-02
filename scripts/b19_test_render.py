#!/usr/bin/env blender --background --python
"""
B19 Test Render - DAE Camera + Fixed Visibility
Uses camera from manifest.json with proper coordinate transform.
"""

import bpy
import os
import sys
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

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


def transform_dae_to_glb(pos):
    """Transform DAE coordinates to GLB/Blender coordinates.
    
    SketchUp exports: X=right, Y=forward, Z=up (meters)
    Blender GLB: X=right, Y=back, Z=up (meters)
    
    Transform: (x, y, z) → (x, -y, z)
    Only Y needs negation because forward/back is flipped.
    """
    return (pos[0], -pos[1], pos[2])


def calculate_scene_bounds():
    """Calculate scene bounds from all mesh objects."""
    min_co = Vector((float('inf'), float('inf'), float('inf')))
    max_co = Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ Vector(corner)
            min_co.x = min(min_co.x, world_co.x)
            min_co.y = min(min_co.y, world_co.y)
            min_co.z = min(min_co.z, world_co.z)
            max_co.x = max(max_co.x, world_co.x)
            max_co.y = max(max_co.y, world_co.y)
            max_co.z = max(max_co.z, world_co.z)
    
    return min_co, max_co


def setup_camera_from_manifest(manifest):
    """Setup camera - try manifest coordinates, fallback to calculated."""
    cam = manifest['camera']
    fov = cam.get('fov', 60)
    
    # Calculate scene bounds first
    min_co, max_co = calculate_scene_bounds()
    center = (min_co + max_co) / 2
    
    print(f"Scene bounds:")
    print(f"  X: [{min_co.x:.2f}, {max_co.x:.2f}]")
    print(f"  Y: [{min_co.y:.2f}, {max_co.y:.2f}]")
    print(f"  Z: [{min_co.z:.2f}, {max_co.z:.2f}]")
    print(f"  Center: ({center.x:.2f}, {center.y:.2f}, {center.z:.2f})")
    
    # Calculate camera position: inside room near entrance, eye height 1.6m
    # Move inside a bit to avoid seeing exterior walls
    glb_eye = (center.x, min_co.y + 0.5, 1.6)  # Just inside entrance
    glb_target = (center.x, max_co.y - 0.3, 0.8)  # Looking at back wall/floor
    fov = 60  # Wider FOV to see more
    
    print(f"Calculated Camera:")
    print(f"  Eye: {glb_eye}")
    print(f"  Target: {glb_target}")
    print(f"  FOV: {fov}°")
    
    # Create camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(fov)
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Set position
    cam_obj.location = glb_eye
    
    # Point at target using Track To constraint
    target_empty = bpy.data.objects.new("CameraTarget", None)
    target_empty.location = glb_target
    bpy.context.scene.collection.objects.link(target_empty)
    
    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.target = target_empty
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    # Apply constraint
    bpy.context.view_layer.update()
    
    return cam_obj


def apply_visibility(manifest):
    """Hide objects based on manifest visibility."""
    vis = manifest.get('visibility', manifest.get('scene_visibility', {}))
    
    # Support both new and legacy format
    if 'global' in vis:
        hidden_names = set(vis.get('global', {}).get('hidden_names', []))
        hidden_names.update(vis.get('scene', {}).get('hidden_names', []))
        hidden_pids = set(vis.get('global', {}).get('hidden_pids', []))
        hidden_pids.update(vis.get('scene', {}).get('hidden_pids', []))
    else:
        hidden_names = set()
        hidden_pids = set(vis.get('hidden_pids', []))
    
    print(f"Visibility: {len(hidden_names)} names, {len(hidden_pids)} PIDs to hide")
    
    hidden_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        should_hide = False
        
        # Check by name
        if obj.name in hidden_names:
            should_hide = True
        elif obj.name.startswith('HIDDEN_S_') or obj.name.startswith('HIDDEN_G_'):
            should_hide = True
        
        # Check by PID in name
        if not should_hide:
            for part in obj.name.replace('.', '_').split('_'):
                if part.isdigit() and int(part) in hidden_pids:
                    should_hide = True
                    break
        
        if should_hide:
            obj.hide_render = True
            obj.hide_viewport = True
            hidden_count += 1
            print(f"  Hidden: {obj.name}")
    
    print(f"Hidden {hidden_count} objects")
    return hidden_count


def setup_lighting():
    """Basic 3-point lighting."""
    # Sun light
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    # Fill light
    fill_data = bpy.data.lights.new("Fill", 'AREA')
    fill_data.energy = 100
    fill_data.size = 2
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.location = (-3, -3, 2)
    bpy.context.scene.collection.objects.link(fill)
    
    # World ambient
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.8, 0.85, 0.9, 1)
    bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def render(output_path, samples=64):
    """Render with Cycles."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False  # Disabled - OpenImageDenoiser not available
    
    # Use GPU if available
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
    except:
        print("GPU not available, using CPU")
    
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = output_path
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B19 Test Render — DAE Camera + Fixed Visibility")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    manifest_path = bundle_dir / 'manifest.json'
    glb_path = bundle_dir / 'model' / 'model.glb'
    
    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"Bundle: {bundle_dir}")
    print(f"Scene: {manifest.get('scene_id', 'unknown')}")
    
    # Setup
    clear_scene()
    
    # 1. Import GLB
    print("\n=== IMPORT ===")
    import_glb(str(glb_path))
    
    # 2. Setup camera from DAE coordinates
    print("\n=== CAMERA ===")
    setup_camera_from_manifest(manifest)
    
    # 3. Apply visibility
    print("\n=== VISIBILITY ===")
    apply_visibility(manifest)
    
    # 4. Lighting
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    # 5. Render
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
