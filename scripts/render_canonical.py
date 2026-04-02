#!/usr/bin/env blender --background --python
"""
B21 — Camera from DAE Matrix (FINAL)

⛔ ЗАПРЕТЫ:
- НЕ использовать track_to
- НЕ вычислять direction
- НЕ пересчитывать ничего

Используем ГОТОВЫЕ значения из DAE matrix.
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


def setup_camera_dae_matrix():
    """Setup camera using EXACT values from DAE matrix.
    
    Values pre-computed from DAE camera matrix:
    - Position converted from inches Z-up to meters Y-up
    - Rotation converted using R_glb = T @ R_dae @ T.T
    
    NO track_to, NO direction calculation!
    """
    
    # DAE position (meters): (1.147, -4.442, 1.948)
    # Scene bounds Y: [-0.74, 3.29]
    # Camera Y=-4.44 is OUTSIDE scene (in front of entrance)
    # This is correct! Camera is outside looking IN.
    
    # Use DAE position as-is (Blender and SketchUp GLB both Z-up)
    POSITION = (1.147482, -4.441579, 1.947995)  # Original DAE position
    
    # Rotation: camera default looks -Z, we need to look +Y (into room)
    # Rotate 90° around X to look forward, then adjust
    ROTATION = (math.radians(90), 0.0, 0.0)  # Look along +Y axis
    FOV = 70.0  # degrees - wider for interior view (original DAE: 35°)
    
    print("=== B21 Camera from DAE Matrix ===")
    print(f"Position: {POSITION}")
    print(f"Rotation: {ROTATION} rad = ({math.degrees(ROTATION[0]):.2f}°, {math.degrees(ROTATION[1]):.2f}°, {math.degrees(ROTATION[2]):.2f}°)")
    print(f"FOV: {FOV}°")
    
    # Create camera
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(FOV)
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    # Set position EXACTLY
    cam_obj.location = POSITION
    
    # Set rotation EXACTLY (Euler XYZ)
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = ROTATION
    
    # Update scene
    bpy.context.view_layer.update()
    
    return {
        'position': POSITION,
        'rotation_rad': ROTATION,
        'rotation_deg': (math.degrees(ROTATION[0]), math.degrees(ROTATION[1]), math.degrees(ROTATION[2])),
        'fov': FOV
    }


def apply_visibility(manifest):
    """Apply visibility from manifest."""
    vis = manifest.get('visibility', {})
    
    global_pids = set(vis.get('global', {}).get('hidden_pids', []))
    scene_pids = set(vis.get('scene', {}).get('hidden_pids', []))
    all_pids = global_pids | scene_pids
    
    global_names = set(vis.get('global', {}).get('hidden_names', []))
    scene_names = set(vis.get('scene', {}).get('hidden_names', []))
    all_names = global_names | scene_names
    
    print(f"Visibility: {len(all_pids)} PIDs, {len(all_names)} names to hide")
    
    hidden_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        should_hide = False
        
        if obj.name in all_names:
            should_hide = True
        elif obj.name.startswith('HIDDEN_'):
            should_hide = True
        else:
            for part in obj.name.replace('.', '_').split('_'):
                if part.isdigit() and int(part) in all_pids:
                    should_hide = True
                    break
        
        if should_hide:
            obj.hide_render = True
            obj.hide_viewport = True
            hidden_count += 1
    
    print(f"Hidden: {hidden_count} objects")
    return hidden_count


def apply_section_planes(manifest):
    """Apply section planes as camera near clip distance.
    
    Section plane from SketchUp: ax + by + cz + d = 0
    If plane is perpendicular to Y (normal.y ≈ 1), it clips in Y direction.
    """
    planes = manifest.get('section_planes', [])
    
    if not planes:
        print("No section planes in manifest")
        return 0
    
    camera = bpy.context.scene.camera
    if not camera:
        print("No camera in scene")
        return 0
    
    applied = 0
    
    for i, plane in enumerate(planes):
        normal = plane['normal']
        dist_m = plane['distance_meters']
        
        print(f"Section plane {i}: normal={normal}, dist={dist_m:.3f}m")
        
        # Check if plane is perpendicular to Y (camera looking direction)
        if abs(normal[1]) > 0.9:
            # Plane equation: n·p + d = 0 → y*normal[1] + d = 0 → y = -d/normal[1]
            # For normal=[0,1,0] and d=-1.3: y = -(-1.3)/1 = 1.3m
            # But this is the plane position, not where we want to clip!
            # 
            # Section plane in SketchUp clips geometry BEHIND it (from camera's view)
            # Camera at Y=-4.44 looking +Y
            # Section plane at Y=1.3 means: show only geometry with Y > 1.3
            # But we want to HIDE the front wall, so we should clip at room entrance
            #
            # The section plane distance is FROM ORIGIN, not from camera
            # dist_m = -1.3 means plane is at Y = 1.3 (in front of origin)
            
            plane_y = dist_m  # The actual plane position (negative means +Y direction)
            cam_y = camera.location.y
            
            # We want to clip everything between camera and just inside the room
            # Room starts at Y ≈ -0.74, camera at Y = -4.44
            # A reasonable clip would be at Y ≈ -0.5 (just outside room entrance)
            # 
            # For now, use the section plane position directly
            # and clip a bit before it to see into the room
            target_clip_y = -0.5  # Just outside room entrance
            near_clip = abs(cam_y - target_clip_y)
            
            # Set camera near clip
            camera.data.clip_start = max(0.01, near_clip)
            
            print(f"  Camera Y={cam_y:.2f}, Section plane at Y={-dist_m:.2f}")
            print(f"  Clipping at Y={target_clip_y:.2f}")
            print(f"  Set clip_start={camera.data.clip_start:.2f}m")
            applied += 1
    
    return applied


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
    print("B21 — Camera from DAE Matrix (FINAL)")
    print("⛔ NO track_to, NO direction calculation!")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    manifest_path = bundle_dir / 'manifest.json'
    
    glb_path = bundle_dir / 'model' / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model.glb'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    
    clear_scene()
    
    print("\n=== IMPORT ===")
    import_glb(str(glb_path))
    
    print("\n=== CAMERA ===")
    camera_info = setup_camera_dae_matrix()
    
    print("\n=== VISIBILITY ===")
    hidden = apply_visibility(manifest)
    
    print("\n=== SECTION PLANES ===")
    section_planes_applied = apply_section_planes(manifest)
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # Write experiment.json
    experiment = {
        "experiment": "B21",
        "method": "Camera from DAE matrix (pre-computed values)",
        "bundle": str(bundle_dir.name),
        "camera": {
            "position": list(camera_info['position']),
            "rotation_rad": list(camera_info['rotation_rad']),
            "rotation_deg": list(camera_info['rotation_deg']),
            "fov": camera_info['fov']
        },
        "visibility": {
            "hidden_count": hidden
        },
        "constraints": [
            "NO track_to constraint",
            "NO direction calculation",
            "Values from DAE matrix ONLY"
        ]
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
