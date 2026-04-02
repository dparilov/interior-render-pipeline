#!/usr/bin/env blender --background --python
"""
B24 — B21 Camera + Remove Front Wall by Z

Camera at Z=4.44, looking -Z
Remove faces with high Z (closest to camera = front wall)
"""

import bpy
import bmesh
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


def setup_camera_b21():
    """Setup camera using B21 values with Y inverted.
    
    B21 position (1.15, 1.95, 4.44) puts camera INSIDE scene looking +Y
    but scene is at Y=[0, 3.3]. Camera looks at Y=134 (way beyond).
    
    Try: Invert Y to put camera at Y=-1.95 (outside scene, looking +Y into it)
    """
    # Original DAE: (1.147, -4.442, 1.948) in SketchUp Z-up
    # GLB: both are Z-up, just negate Y for forward/back flip
    # Position: (x, -y, z) = (1.147, 4.442, 1.948)
    POSITION = (1.147482, 4.441579, 1.947995)  # (x, -y, z) from DAE
    ROTATION = (1.537196, -0.001400, 0.000000)  # 88° X = look +Y
    FOV = 35.0
    
    print(f"Camera (B21 EXACT):")
    print(f"  Position: {POSITION}")
    print(f"  Rotation: {ROTATION} rad = ({math.degrees(ROTATION[0]):.1f}°, {math.degrees(ROTATION[1]):.1f}°, {math.degrees(ROTATION[2]):.1f}°)")
    print(f"  FOV: {FOV}°")
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(FOV)
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    cam_obj.location = POSITION
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = ROTATION
    
    bpy.context.view_layer.update()
    return cam_obj


def remove_front_wall_by_z(z_threshold=2.5):
    """Remove faces with Z > threshold (closest to camera).
    
    Camera at Z=4.44 looking -Z, so high Z faces are the front wall.
    """
    total_deleted = 0
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_to_delete = []
        
        for face in bm.faces:
            # Check max Z of face vertices in world space
            max_z = max((obj.matrix_world @ v.co).z for v in face.verts)
            if max_z > z_threshold:
                faces_to_delete.append(face)
        
        if faces_to_delete:
            bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
            total_deleted += len(faces_to_delete)
            print(f"  {obj.name}: deleted {len(faces_to_delete)} faces with Z > {z_threshold}")
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    
    print(f"Total deleted: {total_deleted} faces")
    return total_deleted


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
        pass
    
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.filepath = output_path
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B24 — B21 Camera + Remove Front Wall by Z")
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
    
    print("\n=== REMOVE FRONT WALL (Z > 2.5) ===")
    deleted = remove_front_wall_by_z(z_threshold=2.5)
    
    print("\n=== CAMERA ===")
    setup_camera_b21()
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # Write experiment.json
    experiment = {
        "experiment": "B24",
        "method": "B21 camera + remove faces with Z > 2.5",
        "bundle": str(bundle_dir.name),
        "camera": {
            "position": [1.147482, 1.947995, 4.441579],
            "rotation_rad": [1.537196, -0.001400, 0.000000],
            "fov": 35.0,
            "source": "B21 EXACT"
        },
        "front_wall_removal": {
            "threshold": "Z > 2.5m",
            "faces_deleted": deleted
        }
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
