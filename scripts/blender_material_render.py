#!/usr/bin/env blender --background --python
"""
Blender headless material renderer for IRP.
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
    parser.add_argument('--uv-method', default='box', choices=['generated', 'box', 'auto'])
    parser.add_argument('--assignment-mode', default='geometric', choices=['name', 'geometric'])
    parser.add_argument('--output', '-o', required=True, help='Output render path')
    parser.add_argument('--resolution', '-r', default='1920x1080', help='Resolution WxH')
    parser.add_argument('--samples', '-s', type=int, default=128, help='Render samples')
    
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(filepath):
    ext = Path(filepath).suffix.lower()
    if ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    print(f"Imported {filepath}: {len(bpy.data.objects)} objects")


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
    parts = size_mm.lower().replace('mm', '').split('x')
    w, h = int(parts[0]), int(parts[1])
    # Object coords are in meters, texture spans [0,1] per meter with scale 1
    # For 200mm tile, need 5 tiles per meter = scale 0.2 (each tile = 0.2m)
    # But textures tile, so we use smaller scale to see pattern
    return (0.5, 0.5, 1.0)  # Test scale - tiles visible


def create_texture_material(name, texture_path, tile_size_mm, uv_method='box'):
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
    
    tex_image.image = bpy.data.images.load(texture_path)
    tex_image.image.colorspace_settings.name = 'sRGB'
    
    # Object coords work best for 3D projection
    coord_output = tex_coord.outputs['Object']
    
    scale = tile_scale(tile_size_mm)
    mapping.inputs['Scale'].default_value = scale
    
    output.location = (400, 0)
    bsdf.location = (100, 0)
    tex_image.location = (-200, 0)
    mapping.location = (-450, 0)
    tex_coord.location = (-650, 0)
    
    links.new(coord_output, mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image.inputs['Vector'])
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Roughness'].default_value = 0.3
    
    print(f"Material '{name}': scale={scale}, uv={uv_method}")
    return mat


def is_floor_face(poly, obj):
    """Face is floor if normal points UP and Z near ground."""
    world_normal = (obj.matrix_world.to_3x3() @ poly.normal).normalized()
    if world_normal.z > 0.9:  # Normal pointing up
        # Check face center Z
        mesh = obj.data
        verts = [mesh.vertices[i].co for i in poly.vertices]
        center = sum(verts, Vector()) / len(verts)
        world_center = obj.matrix_world @ center
        if world_center.z < 0.15:  # Near ground level
            return True
    return False


def is_wall_face(poly, obj):
    """Face is wall if normal is horizontal."""
    world_normal = (obj.matrix_world.to_3x3() @ poly.normal).normalized()
    horizontal = world_normal.x**2 + world_normal.y**2
    if horizontal > 0.8 and abs(world_normal.z) < 0.3:
        return True
    return False


def assign_materials_geometric(floor_mat, wall_mat):
    """Assign materials based on face geometry (normal + position)."""
    stats = {'floor': 0, 'wall': 0, 'other': 0, 'meshes': 0}
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        mesh = obj.data
        stats['meshes'] += 1
        
        # Clear existing materials
        mesh.materials.clear()
        
        # Add our materials (index 0 = default/other, 1 = floor, 2 = wall)
        default_mat = bpy.data.materials.new(name=f"Default_{obj.name}")
        default_mat.use_nodes = True
        mesh.materials.append(default_mat)  # index 0
        
        floor_idx = -1
        wall_idx = -1
        
        if floor_mat:
            mesh.materials.append(floor_mat)
            floor_idx = len(mesh.materials) - 1
        
        if wall_mat:
            mesh.materials.append(wall_mat)
            wall_idx = len(mesh.materials) - 1
        
        # Assign per-face
        for poly in mesh.polygons:
            if floor_mat and is_floor_face(poly, obj):
                poly.material_index = floor_idx
                stats['floor'] += 1
            elif wall_mat and is_wall_face(poly, obj):
                poly.material_index = wall_idx
                stats['wall'] += 1
            else:
                poly.material_index = 0
                stats['other'] += 1
    
    print(f"Geometric assignment: {stats}")
    return stats


def assign_materials_by_name(floor_mat, wall_mat, floor_tile_size, wall_tile_size, uv_method):
    """Original name-based assignment."""
    assigned = {'floor': 0, 'wall': 0, 'other': 0}
    floor_meshes = []
    wall_meshes = []
    
    for obj in bpy.data.objects:
        name_lower = obj.name.lower()
        if 'irp_floor' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    floor_meshes.append(child)
        elif 'irp_walls' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    wall_meshes.append(child)
    
    for mesh in floor_meshes:
        if floor_mat:
            mesh.data.materials.clear()
            mesh.data.materials.append(floor_mat)
            assigned['floor'] += 1
    
    for mesh in wall_meshes:
        if wall_mat:
            mesh.data.materials.clear()
            mesh.data.materials.append(wall_mat)
            assigned['wall'] += 1
    
    print(f"Name assignment: {assigned}")
    return assigned


def setup_lighting():
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (5, -5, 10)
    light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))
    
    world = bpy.data.worlds.new("IRPWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.9, 0.92, 0.95, 1.0)
    bg.inputs['Strength'].default_value = 0.8


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
    
    print("=== Blender Material Render ===")
    print(f"Assignment mode: {args.assignment_mode}")
    print(f"UV method: {args.uv_method}")
    
    clear_scene()
    import_model(args.model)
    setup_camera(args.camera)
    
    floor_mat = None
    wall_mat = None
    
    if args.floor_texture:
        floor_mat = create_texture_material("FloorMaterial", args.floor_texture, 
                                            args.floor_tile_size, args.uv_method)
    if args.wall_texture:
        wall_mat = create_texture_material("WallMaterial", args.wall_texture,
                                           args.wall_tile_size, args.uv_method)
    
    if args.assignment_mode == 'geometric':
        stats = assign_materials_geometric(floor_mat, wall_mat)
    else:
        stats = assign_materials_by_name(floor_mat, wall_mat, 
                                         args.floor_tile_size, args.wall_tile_size,
                                         args.uv_method)
    
    setup_lighting()
    setup_render(args.resolution, args.samples)
    
    print("\nRendering...")
    render(args.output)
    
    # Save stats to experiment.json
    exp_path = str(Path(args.output).parent / "experiment.json")
    exp_data = {
        "assignment_mode": args.assignment_mode,
        "uv_method": args.uv_method,
        "floor_tile_size": args.floor_tile_size,
        "wall_tile_size": args.wall_tile_size,
        "floor_faces_count": stats.get('floor', 0),
        "wall_faces_count": stats.get('wall', 0),
        "other_faces_count": stats.get('other', 0),
        "meshes_processed": stats.get('meshes', 0)
    }
    with open(exp_path, 'w') as f:
        json.dump(exp_data, f, indent=2)
    
    print("=== Done ===")


if __name__ == "__main__":
    main()
