#!/usr/bin/env blender --background --python
"""
B27 — B26 Camera + Front Wall Removal by Y

Camera: B26/B21 working values
Front wall: Remove faces with Y < 0 (entrance area)
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


def setup_camera_b26():
    """B26/B21 working camera values."""
    POSITION = (1.147482, -4.441579, 1.947995)
    ROTATION = (math.radians(90), 0.0, 0.0)
    FOV = 35.0
    
    print(f"Camera (B26/B21):")
    print(f"  Position: {POSITION}")
    print(f"  Rotation: 90° X")
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


def remove_front_wall_by_y(y_threshold=0.0):
    """Remove faces with Y < threshold (entrance wall).
    
    Camera at Y=-4.44, looking +Y into room.
    Room starts at Y ~ 0.
    Remove faces at Y < 0 to clear the entrance wall.
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
            # Check if ANY vertex is below Y threshold (world space)
            for vert in face.verts:
                world_co = obj.matrix_world @ vert.co
                if world_co.y < y_threshold:
                    faces_to_delete.append(face)
                    break
        
        if faces_to_delete:
            bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
            total_deleted += len(faces_to_delete)
            print(f"  {obj.name}: {len(faces_to_delete)} faces deleted")
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    
    print(f"Total: {total_deleted} faces with Y < {y_threshold}")
    return total_deleted


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
    print("B27 — B26 Camera + Front Wall Removal (Y < 0)")
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
    
    print("\n=== REMOVE FRONT WALL (Y < 0) ===")
    deleted = remove_front_wall_by_y(y_threshold=0.0)
    
    print("\n=== CAMERA ===")
    setup_camera_b26()
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    experiment = {
        "experiment": "B27",
        "method": "B26 camera + remove faces with Y < 0",
        "camera": {
            "position": [1.147482, -4.441579, 1.947995],
            "rotation_deg": [90, 0, 0],
            "fov": 35
        },
        "front_wall_removal": {
            "threshold": "Y < 0",
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
