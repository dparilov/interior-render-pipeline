#!/usr/bin/env blender --background --python
"""
Blender headless material renderer for IRP.

Renders GLB model with PBR materials using reference textures.

Usage:
  blender --background --python scripts/blender_material_render.py -- \
    --model examples/bathroom_01/model/model.glb \
    --camera examples/bathroom_01/camera_projection_audit.json \
    --floor-texture examples/bathroom_01/references/floor_tiles.jpg \
    --wall-texture examples/bathroom_01/references/wall_tiles.png \
    --floor-tile-size 200x200 --wall-tile-size 50x200 \
    --uv-method generated \
    --output results/blender-test/B2a/render.png
"""

import bpy
import os
import sys
import argparse
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix


def parse_args():
    """Parse command line arguments after '--'."""
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
    parser.add_argument('--floor-tile-size', default='200x200', help='Floor tile size in mm (WxH)')
    parser.add_argument('--wall-tile-size', default='50x200', help='Wall tile size in mm (WxH)')
    parser.add_argument('--uv-method', default='generated', choices=['generated', 'box', 'auto'],
                        help='UV mapping method')
    parser.add_argument('--output', '-o', required=True, help='Output render path')
    parser.add_argument('--resolution', '-r', default='1920x1080', help='Resolution WxH')
    parser.add_argument('--samples', '-s', type=int, default=128, help='Render samples')
    
    return parser.parse_args(argv)


def clear_scene():
    """Clear default scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(filepath):
    """Import GLB/GLTF model."""
    ext = Path(filepath).suffix.lower()
    
    if ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")
    
    print(f"Imported {filepath}: {len(bpy.data.objects)} objects")


def look_at(eye, target, up=None):
    """Calculate rotation for camera to look at target."""
    if up is None:
        up = Vector((0, 0, 1))
    
    eye = Vector(eye)
    target = Vector(target)
    
    direction = target - eye
    
    # Use Blender's built-in track quaternion
    # Camera looks along -Z, with Y as up
    rot_quat = direction.to_track_quat('-Z', 'Y')
    
    return rot_quat.to_euler()


def setup_camera(camera_json_path):
    """Setup camera from IRP camera JSON."""
    with open(camera_json_path) as f:
        data = json.load(f)
    
    cam_data = data.get('camera', data)
    
    eye = cam_data['eye']
    target = cam_data['target']
    fov = cam_data['fov']
    
    # Create camera
    cam = bpy.data.cameras.new("IRPCamera")
    cam_obj = bpy.data.objects.new("IRPCamera", cam)
    bpy.context.scene.collection.objects.link(cam_obj)
    
    # Set position
    cam_obj.location = Vector(eye)
    
    # Create empty at target for look-at
    target_empty = bpy.data.objects.new("CameraTarget", None)
    target_empty.location = Vector(target)
    bpy.context.scene.collection.objects.link(target_empty)
    
    # Add Track To constraint
    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.target = target_empty
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    
    # Apply constraint to get final rotation
    bpy.context.view_layer.update()
    
    # Set FOV (Blender uses vertical FOV)
    cam.angle = math.radians(fov)
    
    # Set as active camera
    bpy.context.scene.camera = cam_obj
    
    # Verify direction
    look_dir = cam_obj.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    expected_dir = (Vector(target) - Vector(eye)).normalized()
    dot = look_dir.dot(expected_dir)
    
    print(f"Camera: eye={eye}, target={target}, fov={fov}")
    print(f"Look direction check: dot={dot:.3f} (should be ~1.0)")
    
    return cam_obj


def tile_scale(size_mm):
    """Calculate tile scale from size in mm (tiles per meter)."""
    parts = size_mm.lower().replace('mm', '').split('x')
    w, h = int(parts[0]), int(parts[1])
    # tiles per meter = 1000mm / tile_size_mm
    return (1000.0 / w, 1000.0 / h, 1.0)


def create_texture_material(name, texture_path, tile_size_mm, uv_method='generated'):
    """Create PBR material with texture and proper tiling."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex_image = nodes.new('ShaderNodeTexImage')
    mapping = nodes.new('ShaderNodeMapping')
    
    # Load texture
    tex_image.image = bpy.data.images.load(texture_path)
    tex_image.image.colorspace_settings.name = 'sRGB'
    
    # UV source based on method
    if uv_method == 'generated':
        tex_coord = nodes.new('ShaderNodeTexCoord')
        coord_output = tex_coord.outputs['Generated']
    elif uv_method == 'box':
        tex_coord = nodes.new('ShaderNodeTexCoord')
        coord_output = tex_coord.outputs['Object']
    else:  # auto - will use UV
        tex_coord = nodes.new('ShaderNodeTexCoord')
        coord_output = tex_coord.outputs['UV']
    
    # Calculate scale
    scale = tile_scale(tile_size_mm)
    mapping.inputs['Scale'].default_value = scale
    
    # Position nodes
    output.location = (400, 0)
    bsdf.location = (100, 0)
    tex_image.location = (-200, 0)
    mapping.location = (-450, 0)
    tex_coord.location = (-650, 0)
    
    # Link nodes
    links.new(coord_output, mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image.inputs['Vector'])
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # PBR settings
    bsdf.inputs['Roughness'].default_value = 0.3
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    
    print(f"Material '{name}': texture={Path(texture_path).name}, scale={scale}, uv={uv_method}")
    return mat


def assign_materials_by_name(floor_texture, wall_texture, floor_tile_size, wall_tile_size, uv_method):
    """Assign materials to objects based on IRP entity hierarchy."""
    floor_mat = None
    wall_mat = None
    
    if floor_texture:
        floor_mat = create_texture_material("FloorMaterial", floor_texture, floor_tile_size, uv_method)
    if wall_texture:
        wall_mat = create_texture_material("WallMaterial", wall_texture, wall_tile_size, uv_method)
    
    assigned = {'floor': 0, 'wall': 0, 'other': 0}
    
    # Find IRP parent objects and collect their mesh children
    floor_meshes = []
    wall_meshes = []
    
    for obj in bpy.data.objects:
        name_lower = obj.name.lower()
        
        if 'irp_floor' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    floor_meshes.append(child)
            if obj.type == 'MESH':
                floor_meshes.append(obj)
        
        elif 'irp_walls' in name_lower or 'irp_wall' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    wall_meshes.append(child)
            if obj.type == 'MESH':
                wall_meshes.append(obj)
    
    # Also check direct mesh naming
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        name_lower = obj.name.lower()
        
        if floor_mat and 'floor' in name_lower and obj not in floor_meshes:
            floor_meshes.append(obj)
        elif wall_mat and ('wall' in name_lower or 'irp_walls' in name_lower) and obj not in wall_meshes:
            wall_meshes.append(obj)
    
    # Apply auto UV if needed
    if uv_method == 'auto':
        all_meshes = floor_meshes + wall_meshes
        for mesh in all_meshes:
            bpy.context.view_layer.objects.active = mesh
            mesh.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh.select_set(False)
        print(f"Auto UV applied to {len(all_meshes)} meshes")
    
    # Assign materials
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
    
    # Count other
    all_assigned = set(floor_meshes + wall_meshes)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj not in all_assigned:
            assigned['other'] += 1
    
    print(f"Material assignment: {assigned}")
    return assigned


def setup_lighting():
    """Setup lighting."""
    # Sun lamp
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (5, -5, 10)
    light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))
    
    # World ambient
    world = bpy.data.worlds.new("IRPWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.9, 0.92, 0.95, 1.0)
    bg.inputs['Strength'].default_value = 0.8


def setup_render(resolution, samples):
    """Configure render settings."""
    scene = bpy.context.scene
    
    w, h = map(int, resolution.split('x'))
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    
    scene.render.engine = 'CYCLES'
    
    # Try GPU
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
        print("Render: Cycles GPU")
    except:
        scene.cycles.device = 'CPU'
        print("Render: Cycles CPU")
    
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'


def render(output_path):
    """Execute render."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=== Blender Material Render ===")
    print(f"Model: {args.model}")
    print(f"UV method: {args.uv_method}")
    print(f"Floor tile: {args.floor_tile_size}, Wall tile: {args.wall_tile_size}")
    
    clear_scene()
    import_model(args.model)
    setup_camera(args.camera)
    
    assign_materials_by_name(
        args.floor_texture, args.wall_texture,
        args.floor_tile_size, args.wall_tile_size,
        args.uv_method
    )
    
    setup_lighting()
    setup_render(args.resolution, args.samples)
    
    print("\nRendering...")
    render(args.output)
    print("=== Done ===")


if __name__ == "__main__":
    main()
