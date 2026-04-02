#!/usr/bin/env blender --background --python
"""
B22 — Remove Front Wall (dirty hack)

Удаляем переднюю стену перед рендером.
В SketchUp clipping plane отсекает её, но в экспорте она есть.
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


def setup_camera():
    """Setup camera using B21 values."""
    # Interior view: camera inside room, looking down at floor
    # Position: centered X, near entrance Y, elevated Z
    POSITION = (0.93, 0.0, 2.2)  # Higher up, at entrance
    ROTATION = (math.radians(70), 0.0, 0.0)  # Look down at 70° (20° below horizontal)
    FOV = 75.0  # Wide angle to see floor and walls
    
    print(f"Camera position: {POSITION}")
    print(f"Camera rotation: 90° X (look +Y)")
    print(f"Camera FOV: {FOV}°")
    
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


def remove_front_wall():
    """Remove the ENTIRE front wall (wall with doorway) to see inside.
    
    Camera is at Y=-4.44, looking +Y into room.
    Room bounds Y: [-0.74, 3.29]
    
    Strategy: Remove ALL geometry at Y < 0 (the entrance wall and surrounding).
    This is aggressive but ensures clear view into room.
    """
    hidden_count = 0
    
    # Scene Y bounds  
    all_y = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            all_y.append((obj.matrix_world @ Vector(corner)).y)
    
    if not all_y:
        print("No mesh objects found")
        return 0
    
    scene_min_y = min(all_y)
    scene_max_y = max(all_y)
    threshold_y = 0.0  # Everything at Y < 0 is part of entrance/corridor
    
    print(f"Scene Y: [{scene_min_y:.2f}, {scene_max_y:.2f}]")
    print(f"Hiding all objects with max Y < {threshold_y}")
    
    # Hide ANY object that is entirely in front of threshold
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        obj_min_y = min((obj.matrix_world @ Vector(corner)).y for corner in obj.bound_box)
        obj_max_y = max((obj.matrix_world @ Vector(corner)).y for corner in obj.bound_box)
        
        # Object is entirely in front area (entrance/corridor walls)
        if obj_max_y < threshold_y:
            obj.hide_render = True
            obj.hide_viewport = True
            hidden_count += 1
            print(f"  Hidden: {obj.name} (Y=[{obj_min_y:.2f}, {obj_max_y:.2f}])")
    
    # For objects that SPAN the entrance, remove faces at Y < threshold
    deleted_faces = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or obj.hide_render:
            continue
        
        obj_min_y = min((obj.matrix_world @ Vector(corner)).y for corner in obj.bound_box)
        obj_max_y = max((obj.matrix_world @ Vector(corner)).y for corner in obj.bound_box)
        
        # Only process objects that span the entrance
        if not (obj_min_y < threshold_y < obj_max_y):
            continue
        
        print(f"  Processing: {obj.name} (Y spans entrance)")
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_to_delete = []
        
        for face in bm.faces:
            center_local = face.calc_center_median()
            center_world = obj.matrix_world @ center_local
            
            # Delete face if center is in front of threshold
            if center_world.y < threshold_y:
                faces_to_delete.append(face)
        
        if faces_to_delete:
            bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
            bmesh.update_edit_mesh(obj.data)
            deleted_faces += len(faces_to_delete)
            print(f"    Deleted {len(faces_to_delete)} faces")
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Total: hidden {hidden_count} objects, deleted {deleted_faces} faces")
    return hidden_count + deleted_faces


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
    print("B22 — Remove Front Wall (dirty hack)")
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
    
    print("\n=== REMOVE FRONT WALL ===")
    deleted = remove_front_wall()
    
    print("\n=== CAMERA ===")
    setup_camera()
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, args.samples)
    
    # Write experiment.json
    experiment = {
        "experiment": "B22",
        "method": "Remove front wall faces before render",
        "bundle": str(bundle_dir.name),
        "front_wall_removed": deleted,
        "camera": {
            "position": [1.147, -4.442, 1.948],
            "rotation_deg": [90, 0, 0],
            "fov": 35
        },
        "note": "Dirty hack - production solution is to hide wall in SketchUp"
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
