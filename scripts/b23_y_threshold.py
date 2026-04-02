#!/usr/bin/env blender --background --python
"""
B23 — Sequential Y-threshold face hiding (STRICT)

⛔ ЗАПРЕТЫ:
- НЕ ДВИГАТЬ КАМЕРУ
- НЕ МЕНЯТЬ FOV
- НЕ СКРЫВАТЬ объекты целиком — удалять FACES по Y
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
    parser.add_argument('--output-dir', '-o', required=True, help='Output directory')
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
    """Setup camera using EXACT B21 values. NO MODIFICATIONS!"""
    # B21 EXACT values
    POSITION = (1.147482, 1.947995, 4.441579)
    ROTATION = (1.537196, -0.001400, 0.000000)  # radians
    FOV = 35.0
    
    print(f"Camera (B21 EXACT):")
    print(f"  Position: {POSITION}")
    print(f"  Rotation: {ROTATION} rad")
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


def setup_render(samples=64):
    """Setup Cycles render."""
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


def delete_faces_below_y(y_threshold):
    """Delete ALL faces with ANY vertex below y_threshold.
    
    Uses world coordinates for accurate deletion.
    Returns total faces deleted.
    """
    total_deleted = 0
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        # Work in object mode with bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        faces_to_delete = []
        
        for face in bm.faces:
            # Check all vertices in world space
            for vert in face.verts:
                world_co = obj.matrix_world @ vert.co
                if world_co.y < y_threshold:
                    faces_to_delete.append(face)
                    break  # One vertex below threshold = delete face
        
        if faces_to_delete:
            bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
            total_deleted += len(faces_to_delete)
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    
    return total_deleted


def render_to_file(filepath):
    """Render to file."""
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {filepath}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B23 — Sequential Y-threshold face hiding (STRICT)")
    print("⛔ Camera = B21 EXACT, FOV = 35°, face deletion only")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model' / 'model.glb'
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Y thresholds to test
    thresholds = [
        (0.0, "B23_y0"),      # No cutting (baseline)
        (1.0, "B23_y1"),      # Cut Y < 1.0m
        (1.5, "B23_y1.5"),    # Cut Y < 1.5m
        (2.0, "B23_y2"),      # Cut Y < 2.0m
    ]
    
    results = []
    
    for y_threshold, name in thresholds:
        print(f"\n{'='*60}")
        print(f"Threshold: Y < {y_threshold}m → {name}")
        print(f"{'='*60}")
        
        # Reload scene fresh for each threshold
        clear_scene()
        import_glb(str(glb_path))
        setup_camera_b21()
        setup_lighting()
        setup_render(args.samples)
        
        # Delete faces below Y threshold
        if y_threshold > 0:
            deleted = delete_faces_below_y(y_threshold)
            print(f"Deleted {deleted} faces with Y < {y_threshold}")
        else:
            deleted = 0
            print("Baseline render (no faces deleted)")
        
        # Render
        output_path = str(output_dir / f"{name}.png")
        render_to_file(output_path)
        
        results.append({
            "name": name,
            "y_threshold": y_threshold,
            "faces_deleted": deleted
        })
    
    # Write experiment.json
    experiment = {
        "experiment": "B23",
        "method": "Sequential Y-threshold face deletion",
        "bundle": str(bundle_dir.name),
        "camera": {
            "position": [1.147482, 1.947995, 4.441579],
            "rotation_rad": [1.537196, -0.001400, 0.000000],
            "fov": 35.0,
            "source": "B21 EXACT values"
        },
        "renders": results,
        "constraints": [
            "Camera = B21 EXACT (no modifications)",
            "FOV = 35° (no changes)",
            "Face deletion only (not object hiding)"
        ]
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(experiment, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Wrote: {exp_path}")
    print(f"Renders: {len(results)}")
    for r in results:
        print(f"  {r['name']}: Y < {r['y_threshold']}m, {r['faces_deleted']} faces deleted")
    print("=" * 60)


if __name__ == "__main__":
    main()
