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
    --output results/blender-test/B1/render.png \
    --resolution 1920x1080
"""

import bpy
import os
import sys
import argparse
import json
import math
from pathlib import Path
from mathutils import Vector


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
    parser.add_argument('--output', '-o', required=True, help='Output render path')
    parser.add_argument('--resolution', '-r', default='1920x1080', help='Resolution WxH')
    parser.add_argument('--samples', '-s', type=int, default=128, help='Render samples')
    parser.add_argument('--manifest', help='Manifest JSON for entity mapping')
    
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
    
    # List all objects
    for obj in bpy.data.objects:
        print(f"  - {obj.name} ({obj.type})")


def setup_camera(camera_json_path):
    """Setup camera from IRP camera JSON."""
    with open(camera_json_path) as f:
        data = json.load(f)
    
    cam_data = data.get('camera', data)  # Handle nested or flat structure
    
    eye = cam_data['eye']
    target = cam_data['target']
    fov = cam_data['fov']
    viewport = cam_data.get('viewport', [1920, 1080])
    
    # Create camera
    cam = bpy.data.cameras.new("IRPCamera")
    cam_obj = bpy.data.objects.new("IRPCamera", cam)
    bpy.context.scene.collection.objects.link(cam_obj)
    
    # Set position
    cam_obj.location = Vector(eye)
    
    # Point at target
    direction = Vector(target) - Vector(eye)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    # Set FOV (vertical in Blender)
    cam.angle = math.radians(fov)
    
    # Set as active camera
    bpy.context.scene.camera = cam_obj
    
    print(f"Camera: eye={eye}, target={target}, fov={fov}")
    return cam_obj


def create_texture_material(name, texture_path):
    """Create PBR material with texture."""
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
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    
    # Load texture
    tex_image.image = bpy.data.images.load(texture_path)
    tex_image.image.colorspace_settings.name = 'sRGB'
    
    # Position nodes
    output.location = (400, 0)
    bsdf.location = (100, 0)
    tex_image.location = (-300, 0)
    mapping.location = (-500, 0)
    tex_coord.location = (-700, 0)
    
    # Link nodes
    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image.inputs['Vector'])
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Set some PBR defaults
    bsdf.inputs['Roughness'].default_value = 0.3
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    
    print(f"Created material '{name}' with texture: {texture_path}")
    return mat


def assign_materials_by_name(floor_texture, wall_texture):
    """Assign materials to objects based on IRP entity hierarchy."""
    floor_mat = None
    wall_mat = None
    
    if floor_texture:
        floor_mat = create_texture_material("FloorMaterial", floor_texture)
    if wall_texture:
        wall_mat = create_texture_material("WallMaterial", wall_texture)
    
    assigned = {'floor': 0, 'wall': 0, 'other': 0}
    
    # First pass: find IRP_ parent objects and collect their mesh children
    floor_meshes = []
    wall_meshes = []
    
    for obj in bpy.data.objects:
        name_lower = obj.name.lower()
        
        # IRP_floor parent
        if 'irp_floor' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    floor_meshes.append(child)
            if obj.type == 'MESH':
                floor_meshes.append(obj)
        
        # IRP_walls parent (walls_tile in surface render)
        elif 'irp_walls' in name_lower or 'irp_wall' in name_lower:
            for child in obj.children_recursive:
                if child.type == 'MESH':
                    wall_meshes.append(child)
            if obj.type == 'MESH':
                wall_meshes.append(obj)
    
    # Second pass: also check direct mesh naming
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        name_lower = obj.name.lower()
        
        if floor_mat and 'floor' in name_lower and obj not in floor_meshes:
            floor_meshes.append(obj)
        elif wall_mat and ('wall' in name_lower or 'irp_walls' in name_lower) and obj not in wall_meshes:
            wall_meshes.append(obj)
    
    # Assign materials
    for mesh in floor_meshes:
        if floor_mat:
            mesh.data.materials.clear()
            mesh.data.materials.append(floor_mat)
            assigned['floor'] += 1
            print(f"  Assigned FloorMaterial to: {mesh.name}")
    
    for mesh in wall_meshes:
        if wall_mat:
            mesh.data.materials.clear()
            mesh.data.materials.append(wall_mat)
            assigned['wall'] += 1
            print(f"  Assigned WallMaterial to: {mesh.name}")
    
    # Count other meshes
    all_assigned = set(floor_meshes + wall_meshes)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj not in all_assigned:
            assigned['other'] += 1
    
    print(f"Material assignment: {assigned}")
    return assigned


def setup_lighting():
    """Setup basic lighting."""
    # Create sun lamp
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(name="SunLight", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (5, -5, 10)
    light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))
    
    # Add ambient light via world
    world = bpy.data.worlds.new("IRPWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.8, 0.85, 0.9, 1.0)  # Soft blue-gray
    bg.inputs['Strength'].default_value = 0.5
    
    print("Lighting setup: Sun + ambient")


def setup_render(resolution, samples):
    """Configure render settings."""
    scene = bpy.context.scene
    
    # Parse resolution
    w, h = map(int, resolution.split('x'))
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    
    # Render engine
    scene.render.engine = 'CYCLES'
    
    # Try GPU, fallback to CPU
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
        print("Render: Cycles GPU (CUDA)")
    except:
        scene.cycles.device = 'CPU'
        print("Render: Cycles CPU")
    
    # Quality
    scene.cycles.samples = samples
    # Disable denoising (may not be available in all builds)
    scene.cycles.use_denoising = False
    print("Denoising disabled")
    
    # Output
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    
    print(f"Resolution: {w}x{h}, Samples: {samples}")


def render(output_path):
    """Execute render."""
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=== Blender Material Render ===")
    print(f"Model: {args.model}")
    print(f"Camera: {args.camera}")
    print(f"Output: {args.output}")
    
    # Setup
    clear_scene()
    import_model(args.model)
    setup_camera(args.camera)
    
    # Materials
    print("\nAssigning materials...")
    assign_materials_by_name(args.floor_texture, args.wall_texture)
    
    # Lighting
    setup_lighting()
    
    # Render settings
    setup_render(args.resolution, args.samples)
    
    # Render
    print("\nRendering...")
    render(args.output)
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
