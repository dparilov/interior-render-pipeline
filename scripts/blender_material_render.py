#!/usr/bin/env blender --background --python
"""
Blender headless material renderer for IRP.
Uses REAL mesh separation (not per-face assignment).
"""

import bpy
import bmesh
import os
import sys
import argparse
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
    
    parser = argparse.ArgumentParser(description='Render model with material textures')
    parser.add_argument('--model', '-m', required=True, help='Input GLB model')
    parser.add_argument('--camera', '-c', required=True, help='Camera JSON file')
    parser.add_argument('--floor-texture', help='Floor texture image')
    parser.add_argument('--wall-texture', help='Wall texture image')
    parser.add_argument('--floor-tile-size', default='200x200', help='Floor tile size mm')
    parser.add_argument('--wall-tile-size', default='50x200', help='Wall tile size mm')
    parser.add_argument('--output', '-o', required=True, help='Output render path')
    parser.add_argument('--resolution', '-r', default='1920x1080', help='Resolution WxH')
    parser.add_argument('--samples', '-s', type=int, default=128, help='Render samples')
    
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def apply_scene_visibility(manifest_path):
    """Hide objects that were hidden in SketchUp Scene.
    
    Uses hidden_pids from manifest.json to hide matching objects.
    PIDs are matched against object names (IRP_name_PID format).
    """
    if not os.path.exists(manifest_path):
        print(f"No manifest found at {manifest_path}, skipping visibility")
        return 0
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    visibility = manifest.get('scene_visibility', {})
    hidden_pids = set(visibility.get('hidden_pids', []))
    hidden_layers = visibility.get('hidden_layers', [])
    
    if not hidden_pids and not hidden_layers:
        print("No hidden entities in manifest")
        return 0
    
    print(f"Scene visibility: {len(hidden_pids)} hidden PIDs, {len(hidden_layers)} hidden layers")
    
    hidden_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        # Try to extract PID from object name
        # Names might be: IRP_name_12345, name.001, etc.
        name_parts = obj.name.replace('IRP_', '').replace('.', '_').split('_')
        
        should_hide = False
        for part in name_parts:
            if part.isdigit():
                pid = int(part)
                if pid in hidden_pids:
                    should_hide = True
                    break
        
        # Also check if object name matches hidden layer
        for layer_name in hidden_layers:
            if layer_name.lower() in obj.name.lower():
                should_hide = True
                break
        
        if should_hide:
            obj.hide_render = True
            obj.hide_viewport = True
            hidden_count += 1
            print(f"  Hidden: {obj.name}")
    
    print(f"Scene visibility applied: {hidden_count} objects hidden")
    return hidden_count


def import_model(filepath):
    filepath = os.path.abspath(filepath)
    ext = Path(filepath).suffix.lower()
    if ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    print(f"Imported {filepath}: {len([o for o in bpy.data.objects if o.type == 'MESH'])} meshes")


def setup_camera(camera_json_path):
    with open(camera_json_path) as f:
        data = json.load(f)
    
    cam_data = data.get('camera', data)
    eye = cam_data['eye']
    target = cam_data['target']
    fov = cam_data['fov']
    
    cam = bpy.data.cameras.new("IRPCamera")
    cam_obj = bpy.data.objects.new("IRPCamera", cam)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = Vector(eye)
    
    # Track To constraint for correct orientation
    target_empty = bpy.data.objects.new("CameraTarget", None)
    target_empty.location = Vector(target)
    bpy.context.scene.collection.objects.link(target_empty)
    
    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.target = target_empty
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    bpy.context.view_layer.update()
    cam.angle = math.radians(fov)
    bpy.context.scene.camera = cam_obj
    
    look_dir = cam_obj.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    expected_dir = (Vector(target) - Vector(eye)).normalized()
    dot = look_dir.dot(expected_dir)
    print(f"Camera: eye={eye}, target={target}, fov={fov}, dot={dot:.3f}")
    
    return cam_obj


def tile_scale(size_mm):
    """Calculate texture scale based on tile size."""
    parts = size_mm.lower().replace('mm', '').split('x')
    w, h = int(parts[0]), int(parts[1])
    # For 200mm tiles: scale = 0.3 gives good density
    # For 50x200mm tiles: scale = 0.5
    base_scale = 1000.0 / max(w, h) * 0.06
    return (base_scale, base_scale, 1.0)


def create_texture_material(name, texture_path, tile_size_mm):
    """Create a textured material using Object coordinates."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex_image = nodes.new('ShaderNodeTexImage')
    mapping = nodes.new('ShaderNodeMapping')
    tex_coord = nodes.new('ShaderNodeTexCoord')
    
    texture_path = os.path.abspath(texture_path)
    tex_image.image = bpy.data.images.load(texture_path)
    tex_image.image.colorspace_settings.name = 'sRGB'
    
    scale = tile_scale(tile_size_mm)
    mapping.inputs['Scale'].default_value = scale
    
    # Use Object coordinates for 3D projection (works without UVs)
    links.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image.inputs['Vector'])
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.3
    
    print(f"Material '{name}': texture={Path(texture_path).name}, scale={scale}")
    return mat


def create_color_material(name, color):
    """Create a simple colored material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = color
    return mat


def separate_geometry():
    """
    REAL mesh separation - creates separate objects for floor/walls/other.
    This is required because per-face material assignment doesn't work
    with texture coordinates in Cycles.
    """
    # Get all meshes
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if not meshes:
        print("No meshes to separate")
        return {'floor': 0, 'wall': 0, 'other': 0}
    
    # Join all meshes into one
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    
    combined = bpy.context.active_object
    combined.name = "Combined"
    total_faces = len(combined.data.polygons)
    print(f"Combined {len(meshes)} meshes: {total_faces} faces")
    
    # === SEPARATE FLOOR ===
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    
    bm = bmesh.from_edit_mesh(combined.data)
    bm.faces.ensure_lookup_table()
    
    floor_count = 0
    for face in bm.faces:
        center = combined.matrix_world @ face.calc_center_median()
        normal = (combined.matrix_world.to_3x3() @ face.normal).normalized()
        
        # Floor: normal pointing up (z > 0.9) AND near ground (z < 0.15)
        if center.z < 0.15 and normal.z > 0.9:
            face.select = True
            floor_count += 1
    
    bmesh.update_edit_mesh(combined.data)
    print(f"Selected {floor_count} floor faces")
    
    # Separate floor into new object
    if floor_count > 0:
        bpy.ops.mesh.separate(type='SELECTED')
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Rename floor object (it gets ".001" suffix)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.startswith("Combined."):
            obj.name = "IRP_Floor"
            print(f"Created IRP_Floor: {len(obj.data.polygons)} faces")
            break
    
    # === SEPARATE WALLS ===
    combined = bpy.data.objects.get("Combined")
    if not combined:
        print("Warning: Combined object not found after floor separation")
        return {'floor': floor_count, 'wall': 0, 'other': 0}
    
    bpy.context.view_layer.objects.active = combined
    combined.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    
    bm = bmesh.from_edit_mesh(combined.data)
    bm.faces.ensure_lookup_table()
    
    wall_count = 0
    for face in bm.faces:
        normal = (combined.matrix_world.to_3x3() @ face.normal).normalized()
        horizontal = normal.x**2 + normal.y**2
        
        # Wall: horizontal normal (facing sideways)
        if horizontal > 0.8 and abs(normal.z) < 0.3:
            face.select = True
            wall_count += 1
    
    bmesh.update_edit_mesh(combined.data)
    print(f"Selected {wall_count} wall faces")
    
    # Separate walls into new object
    if wall_count > 0:
        bpy.ops.mesh.separate(type='SELECTED')
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Rename wall object
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.startswith("Combined.") and obj.name != "IRP_Floor":
            obj.name = "IRP_Walls"
            print(f"Created IRP_Walls: {len(obj.data.polygons)} faces")
            break
    
    # Rename remaining as Other (fixtures, furniture, etc.)
    other_count = 0
    if bpy.data.objects.get("Combined"):
        bpy.data.objects["Combined"].name = "IRP_Other"
        other_count = len(bpy.data.objects["IRP_Other"].data.polygons)
        print(f"Created IRP_Other: {other_count} faces")
    
    # Verify
    mesh_objects = [o.name for o in bpy.data.objects if o.type == 'MESH']
    print(f"Separated objects: {mesh_objects}")
    
    return {'floor': floor_count, 'wall': wall_count, 'other': other_count}


def assign_materials_to_separated(floor_mat, wall_mat):
    """
    Assign materials to WHOLE OBJECTS (not per-face).
    This works correctly with texture coordinates.
    """
    stats = {'floor': 0, 'wall': 0, 'other': 0}
    
    floor_obj = bpy.data.objects.get("IRP_Floor")
    wall_obj = bpy.data.objects.get("IRP_Walls")
    other_obj = bpy.data.objects.get("IRP_Other")
    
    # Create default material for other objects
    other_mat = create_color_material("OtherMaterial", (0.7, 0.7, 0.7, 1.0))
    
    if floor_obj and floor_mat:
        floor_obj.data.materials.clear()
        floor_obj.data.materials.append(floor_mat)
        stats['floor'] = len(floor_obj.data.polygons)
        print(f"Assigned floor material: {stats['floor']} faces")
    
    if wall_obj and wall_mat:
        wall_obj.data.materials.clear()
        wall_obj.data.materials.append(wall_mat)
        stats['wall'] = len(wall_obj.data.polygons)
        print(f"Assigned wall material: {stats['wall']} faces")
    
    if other_obj:
        other_obj.data.materials.clear()
        other_obj.data.materials.append(other_mat)
        stats['other'] = len(other_obj.data.polygons)
        print(f"Assigned other material: {stats['other']} faces")
    
    return stats


def setup_lighting():
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 5.0
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.rotation_euler = (0.7, 0, 0.4)
    
    world = bpy.data.worlds.new("IRPWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.9, 0.92, 0.95, 1.0)
    bg.inputs['Strength'].default_value = 0.3


def setup_render(resolution, samples):
    scene = bpy.context.scene
    w, h = map(int, resolution.split('x'))
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.engine = 'CYCLES'
    
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
    except:
        scene.cycles.device = 'CPU'
    
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = 'PNG'


def render(output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=== Blender Material Render (B8: Real Mesh Separation) ===")
    
    clear_scene()
    import_model(args.model)
    
    # Apply scene visibility from manifest (hide entities hidden in SketchUp)
    manifest_path = Path(args.model).parent.parent / 'manifest.json'
    hidden_count = apply_scene_visibility(str(manifest_path))
    
    # CRITICAL: Separate geometry BEFORE material assignment
    # Per-face assignment doesn't work with textures in Cycles
    sep_stats = separate_geometry()
    
    setup_camera(args.camera)
    
    # Create materials
    floor_mat = None
    wall_mat = None
    
    if args.floor_texture:
        floor_mat = create_texture_material("FloorMaterial", args.floor_texture, 
                                            args.floor_tile_size)
    if args.wall_texture:
        wall_mat = create_texture_material("WallMaterial", args.wall_texture,
                                           args.wall_tile_size)
    
    # Assign materials to WHOLE OBJECTS (not per-face)
    mat_stats = assign_materials_to_separated(floor_mat, wall_mat)
    
    setup_lighting()
    setup_render(args.resolution, args.samples)
    
    print("\nRendering...")
    render(args.output)
    
    # Save experiment.json
    exp_path = str(Path(args.output).parent / "experiment.json")
    exp_data = {
        "experiment": "B8",
        "method": "Real mesh separation (bpy.ops.mesh.separate)",
        "objects_created": ["IRP_Floor", "IRP_Walls", "IRP_Other"],
        "floor_faces": mat_stats.get('floor', 0),
        "wall_faces": mat_stats.get('wall', 0),
        "other_faces": mat_stats.get('other', 0),
        "hidden_objects": hidden_count,
        "floor_tile_size": args.floor_tile_size,
        "wall_tile_size": args.wall_tile_size,
        "resolution": args.resolution,
        "samples": args.samples
    }
    with open(exp_path, 'w') as f:
        json.dump(exp_data, f, indent=2)
    
    print("=== Done ===")


if __name__ == "__main__":
    main()
