#!/usr/bin/env blender --background --python
"""
B20 STRICT Camera + Visibility Test

⛔ ЗАПРЕТЫ:
1. НЕ ПЕРЕСЧИТЫВАТЬ камеру — ТОЛЬКО из manifest
2. НЕ ИСПОЛЬЗОВАТЬ calculate_scene_bounds()
3. НЕ МЕНЯТЬ FOV

Transform: DAE (Z-up) → GLB (Y-up)
(x, y, z) → (x, z, -y)
"""

import bpy
import os
import sys
import json
import math
from pathlib import Path
from mathutils import Vector


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


def dae_to_glb(coords):
    """Transform DAE coordinates (Z-up) to GLB (Y-up).
    
    DAE (Z-up): X=right, Y=forward, Z=up
    GLB (Y-up): X=right, Y=up, Z=back
    
    Transform: (x, y, z) → (x, z, -y)
    As specified in task B20.
    """
    x, y, z = coords
    return [x, z, -y]


def setup_camera_strict(manifest, debug_file):
    """Setup camera using EXACT values from manifest. No calculations!"""
    cam = manifest['camera']
    
    # Get DAE coordinates
    dae_eye = cam['eye']
    dae_target = cam['target']
    dae_fov = cam['fov']
    
    # Transform to GLB coordinates: (x, z, -y) as per task B20
    glb_eye = dae_to_glb(dae_eye)
    glb_target = dae_to_glb(dae_target)
    
    # Debug output
    debug_lines = [
        "=== B20 STRICT Camera Debug ===",
        "",
        "DAE (from manifest):",
        f"  eye:    {dae_eye}",
        f"  target: {dae_target}",
        f"  fov:    {dae_fov}°",
        "",
        "GLB (after transform x,z,-y):",
        f"  eye:    {glb_eye}",
        f"  target: {glb_target}",
        f"  fov:    {dae_fov}° (unchanged)",
        ""
    ]
    
    print("\n".join(debug_lines))
    
    # Write debug file
    with open(debug_file, 'w') as f:
        f.write("\n".join(debug_lines))
    
    # Create camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(dae_fov)  # EXACT FOV from manifest
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
    
    return {
        'dae_eye': dae_eye,
        'dae_target': dae_target,
        'glb_eye': glb_eye,
        'glb_target': glb_target,
        'fov': dae_fov
    }


def apply_visibility_strict(manifest):
    """Apply visibility from manifest. No modifications."""
    vis = manifest.get('visibility', {})
    
    # Get hidden info
    global_hidden = vis.get('global', {}).get('hidden_pids', [])
    scene_hidden = vis.get('scene', {}).get('hidden_pids', [])
    global_names = vis.get('global', {}).get('hidden_names', [])
    scene_names = vis.get('scene', {}).get('hidden_names', [])
    
    all_pids = set(global_hidden + scene_hidden)
    all_names = set(global_names + scene_names)
    
    print(f"Visibility from manifest:")
    print(f"  global.hidden_pids: {global_hidden}")
    print(f"  scene.hidden_pids: {scene_hidden}")
    print(f"  Total to hide: {len(all_pids)} PIDs, {len(all_names)} names")
    
    hidden_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        should_hide = False
        
        # Check by exact name
        if obj.name in all_names:
            should_hide = True
        
        # Check by HIDDEN_ prefix
        if obj.name.startswith('HIDDEN_S_') or obj.name.startswith('HIDDEN_G_'):
            should_hide = True
        
        # Check by PID in name
        for part in obj.name.replace('.', '_').split('_'):
            if part.isdigit() and int(part) in all_pids:
                should_hide = True
                break
        
        if should_hide:
            obj.hide_render = True
            obj.hide_viewport = True
            hidden_count += 1
            print(f"  Hidden: {obj.name}")
    
    return {
        'global_hidden_pids': global_hidden,
        'scene_hidden_pids': scene_hidden,
        'hidden_count': hidden_count
    }


def setup_lighting():
    """Basic lighting."""
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
    """Render with Cycles."""
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
        print("GPU not available, using CPU")
    
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = output_path
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B20 STRICT Camera + Visibility Test")
    print("⛔ No calculate_scene_bounds! Using manifest ONLY!")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    manifest_path = bundle_dir / 'manifest.json'
    
    # Try both locations for GLB
    glb_path = bundle_dir / 'model' / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model.glb'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_file = output_dir / 'camera_debug.txt'
    experiment_file = output_dir / 'experiment.json'
    
    # Load manifest
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    print(f"Scene: {manifest.get('scene_id', 'unknown')}")
    
    # Setup
    clear_scene()
    
    # 1. Import GLB
    print("\n=== IMPORT ===")
    import_glb(str(glb_path))
    
    # 2. Setup camera STRICTLY from manifest
    print("\n=== CAMERA (STRICT) ===")
    camera_info = setup_camera_strict(manifest, str(debug_file))
    
    # 3. Apply visibility from manifest
    print("\n=== VISIBILITY ===")
    visibility_info = apply_visibility_strict(manifest)
    
    # 4. Lighting
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    # 5. Render
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # 6. Write experiment.json
    experiment = {
        "experiment": "B20",
        "method": "STRICT camera from manifest (no calculations)",
        "bundle": str(bundle_dir.name),
        "camera": {
            "dae_eye": camera_info['dae_eye'],
            "dae_target": camera_info['dae_target'],
            "glb_eye": camera_info['glb_eye'],
            "glb_target": camera_info['glb_target'],
            "fov": camera_info['fov'],
            "transform": "(x, y, z) → (x, z, -y)"
        },
        "visibility": visibility_info,
        "constraints": [
            "NO calculate_scene_bounds()",
            "FOV from manifest only",
            "Camera from manifest only"
        ]
    }
    
    with open(experiment_file, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {experiment_file}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
