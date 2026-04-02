#!/usr/bin/env blender --background --python
"""
B39 — Wall tiles texture

Add white glossy subway tile texture to walls.
Tile size: 50x200mm
"""

import bpy
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
    parser.add_argument('--bundle', '-b', required=True)
    parser.add_argument('--output', '-o', required=True)
    parser.add_argument('--samples', type=int, default=64)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    mesh_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
    print(f"Imported: {mesh_count} meshes")
    return mesh_count


def find_walls_objects():
    """Find wall meshes in scene."""
    walls = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            name_lower = obj.name.lower()
            if 'wall' in name_lower or 'стен' in name_lower:
                walls.append(obj)
    return walls


def create_wall_tile_material(texture_path, tile_size_mm=(50, 200)):
    """Create glossy tiled material for walls."""
    mat = bpy.data.materials.new("WallTiles")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.2  # Glossy
    bsdf.inputs['Specular IOR Level'].default_value = 0.5
    
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.location = (-400, 0)
    tex_node.image = bpy.data.images.load(texture_path)
    
    mapping = nodes.new('ShaderNodeMapping')
    mapping.location = (-600, 0)
    
    # Calculate UV scale based on tile size
    # Tile: 50x200mm = 0.05 x 0.2m
    # Assume wall is ~3m wide x 1.5m high (visible part)
    tile_w = tile_size_mm[0] / 1000  # 0.05m
    tile_h = tile_size_mm[1] / 1000  # 0.2m
    
    wall_width = 3.0  # estimated
    wall_height = 1.5  # visible part
    
    uv_scale_x = wall_width / tile_w  # ~60 tiles
    uv_scale_y = wall_height / tile_h  # ~7.5 tiles
    
    # Adjust for reasonable appearance (tiles should be visible)
    # Scale down to show fewer, larger tiles
    scale_factor = 0.15
    mapping.inputs['Scale'].default_value = (uv_scale_x * scale_factor, uv_scale_y * scale_factor, 1)
    
    print(f"Tile size: {tile_size_mm[0]}x{tile_size_mm[1]}mm")
    print(f"UV scale: ({uv_scale_x * scale_factor:.1f}, {uv_scale_y * scale_factor:.1f})")
    
    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-800, 0)
    
    # Link nodes
    links.new(texcoord.outputs['UV'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])
    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat


def apply_material_to_walls(walls, material):
    """Apply material to wall objects."""
    for wall in walls:
        # Clear existing materials
        wall.data.materials.clear()
        wall.data.materials.append(material)
        print(f"Applied tile material to: {wall.name}")


def setup_camera(manifest):
    """Setup camera (same as GOLDEN_B38)."""
    eye = manifest['camera']['eye']
    fov_sketchup = manifest['camera']['fov']
    
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    aspect = viewport['width'] / viewport['height']
    fov_adjusted = fov_sketchup / aspect
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(fov_adjusted)
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    cam_obj.location = (eye[0], eye[1], eye[2])
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Wall offset
    wall_geo = manifest.get('wall_geometry', {})
    if wall_geo:
        cam_obj.location.y -= wall_geo.get('wall_thickness', 0.157)
        section_y = wall_geo.get('section_plane_y', 1.3)
        cam_data.clip_start = abs(cam_obj.location.y - section_y)
    
    bpy.context.view_layer.update()
    return fov_adjusted


def setup_lighting():
    """Enhanced lighting for tile visibility."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 4
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    # Side light to show tile texture
    side = bpy.data.objects.new("Side", bpy.data.lights.new("Side", 'AREA'))
    side.data.energy = 150
    side.data.size = 2
    side.location = (3, 0, 2)
    side.rotation_euler = (math.radians(60), 0, math.radians(-45))
    bpy.context.scene.collection.objects.link(side)
    
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'AREA'))
    fill.data.energy = 80
    fill.data.size = 2
    fill.location = (-3, -3, 2)
    bpy.context.scene.collection.objects.link(fill)
    
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.9, 0.92, 0.95, 1)
    bg.inputs[1].default_value = 0.3
    bpy.context.scene.world = world


def render(output_path, manifest, samples=64):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except:
        pass
    
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B39 — Wall tiles texture")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    texture_path = bundle_dir / 'references' / 'wall_tiles.png'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(bundle_dir / 'manifest.json') as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    
    clear_scene()
    import_glb(str(glb_path))
    
    # Find and texture walls
    print("\n=== WALLS ===")
    walls = find_walls_objects()
    print(f"Found {len(walls)} wall objects")
    
    if walls and texture_path.exists():
        print(f"\nTexture: {texture_path}")
        mat = create_wall_tile_material(str(texture_path))
        apply_material_to_walls(walls, mat)
    else:
        print("No walls found or texture missing")
        # List all objects for debugging
        print("\nAll objects:")
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                print(f"  {obj.name}")
    
    print("\n=== CAMERA ===")
    fov = setup_camera(manifest)
    print(f"FOV: {fov:.1f}°")
    
    print("\n=== LIGHTING ===")
    setup_lighting()
    
    print("\n=== RENDER ===")
    render(args.output, manifest, args.samples)
    
    # Experiment
    exp = {
        "experiment": "B39",
        "method": "Wall tiles texture",
        "texture": "wall_tiles.png",
        "tile_size_mm": [50, 200],
        "walls_found": len(walls),
        "wall_names": [w.name for w in walls]
    }
    with open(output_dir / 'experiment.json', 'w') as f:
        json.dump(exp, f, indent=2)
    
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
