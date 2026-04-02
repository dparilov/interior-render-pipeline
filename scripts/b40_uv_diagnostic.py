#!/usr/bin/env blender --background --python
"""
B40 — UV mapping diagnostic + Box projection test

Test 3 mapping variants:
- B40a: UV (original)
- B40b: Generated
- B40c: Object + Box projection
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
    parser.add_argument('--output-dir', '-o', required=True)
    parser.add_argument('--samples', type=int, default=64)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    return len([o for o in bpy.data.objects if o.type == 'MESH'])


def find_walls_object():
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'wall' in obj.name.lower():
            return obj
    return None


def diagnose_uv(walls_obj, diagnostic_file):
    """Diagnose UV mapping on walls mesh."""
    lines = []
    lines.append(f"=== UV DIAGNOSTIC for {walls_obj.name} ===\n")
    
    mesh = walls_obj.data
    lines.append(f"Vertices: {len(mesh.vertices)}")
    lines.append(f"Polygons: {len(mesh.polygons)}")
    lines.append(f"UV layers: {len(mesh.uv_layers)}")
    
    if mesh.uv_layers:
        for i, uv in enumerate(mesh.uv_layers):
            lines.append(f"  [{i}] {uv.name} (active: {uv.active})")
        
        # Check UV bounds
        uv_layer = mesh.uv_layers.active
        if uv_layer and uv_layer.data:
            uvs = [(d.uv[0], d.uv[1]) for d in uv_layer.data]
            if uvs:
                min_u = min(uv[0] for uv in uvs)
                max_u = max(uv[0] for uv in uvs)
                min_v = min(uv[1] for uv in uvs)
                max_v = max(uv[1] for uv in uvs)
                lines.append(f"\nUV bounds:")
                lines.append(f"  U: [{min_u:.4f}, {max_u:.4f}] (range: {max_u-min_u:.4f})")
                lines.append(f"  V: [{min_v:.4f}, {max_v:.4f}] (range: {max_v-min_v:.4f})")
                
                # Sample first few UVs
                lines.append(f"\nFirst 10 UV samples:")
                for j, uv in enumerate(uvs[:10]):
                    lines.append(f"  {j}: ({uv[0]:.4f}, {uv[1]:.4f})")
    else:
        lines.append("\n⚠️ NO UV LAYERS FOUND!")
    
    # Bounds
    lines.append(f"\nObject bounds:")
    lines.append(f"  Min: {[round(x, 3) for x in walls_obj.bound_box[0]]}")
    lines.append(f"  Max: {[round(x, 3) for x in walls_obj.bound_box[6]]}")
    
    text = "\n".join(lines)
    print(text)
    
    with open(diagnostic_file, 'w') as f:
        f.write(text)
    
    return text


def create_tile_material(texture_path, mapping_type='UV', scale=(10, 10)):
    """Create tiled material with specified mapping type."""
    mat_name = f"WallTiles_{mapping_type}"
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Output
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    # BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.3
    
    # Texture
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.location = (-300, 0)
    tex_node.image = bpy.data.images.load(texture_path)
    
    # Box projection for 'BOX' type
    if mapping_type == 'BOX':
        tex_node.projection = 'BOX'
        tex_node.projection_blend = 0.1
    
    # Mapping
    mapping = nodes.new('ShaderNodeMapping')
    mapping.location = (-500, 0)
    mapping.inputs['Scale'].default_value = (scale[0], scale[1], 1)
    
    # Texture coordinate
    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-700, 0)
    
    # Select coordinate output based on mapping type
    if mapping_type == 'UV':
        coord_output = texcoord.outputs['UV']
    elif mapping_type == 'Generated':
        coord_output = texcoord.outputs['Generated']
    else:  # BOX uses Object
        coord_output = texcoord.outputs['Object']
    
    # Links
    links.new(coord_output, mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_node.inputs['Vector'])
    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    return mat


def setup_camera(manifest):
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
    
    wall_geo = manifest.get('wall_geometry', {})
    if wall_geo:
        cam_obj.location.y -= wall_geo.get('wall_thickness', 0.157)
        cam_data.clip_start = abs(cam_obj.location.y - wall_geo.get('section_plane_y', 1.3))
    
    bpy.context.view_layer.update()


def setup_lighting():
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 4
    sun.location = (5, -5, 10)
    sun.rotation_euler = (math.radians(45), 0, math.radians(45))
    bpy.context.scene.collection.objects.link(sun)
    
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'AREA'))
    fill.data.energy = 100
    fill.data.size = 2
    fill.location = (-3, -3, 2)
    bpy.context.scene.collection.objects.link(fill)
    
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.85, 0.88, 0.92, 1)
    bg.inputs[1].default_value = 0.4
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
    print("B40 — UV mapping diagnostic + Box projection test")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    glb_path = bundle_dir / 'model.glb'
    texture_path = bundle_dir / 'references' / 'wall_tiles.png'
    
    with open(bundle_dir / 'manifest.json') as f:
        manifest = json.load(f)
    
    # Test variants
    variants = [
        ('B40a_uv', 'UV', (5, 5)),
        ('B40b_generated', 'Generated', (3, 3)),
        ('B40c_box', 'BOX', (3, 3)),
    ]
    
    results = {}
    
    for variant_name, mapping_type, scale in variants:
        print(f"\n{'='*60}")
        print(f"Testing: {variant_name} (mapping={mapping_type}, scale={scale})")
        print("=" * 60)
        
        clear_scene()
        import_glb(str(glb_path))
        
        walls = find_walls_object()
        if not walls:
            print("No walls found!")
            continue
        
        # Diagnostic only for first variant
        if variant_name == 'B40a_uv':
            diagnose_uv(walls, str(output_dir / 'diagnostic.txt'))
        
        # Create and apply material
        mat = create_tile_material(str(texture_path), mapping_type, scale)
        walls.data.materials.clear()
        walls.data.materials.append(mat)
        print(f"Applied {mapping_type} material to {walls.name}")
        
        setup_camera(manifest)
        setup_lighting()
        
        render_path = str(output_dir / f'{variant_name}.png')
        render(render_path, manifest, args.samples)
        
        results[variant_name] = {
            'mapping': mapping_type,
            'scale': scale,
            'output': f'{variant_name}.png'
        }
    
    # Save experiment
    exp = {
        "experiment": "B40",
        "method": "UV mapping diagnostic + variants test",
        "variants": results
    }
    with open(output_dir / 'experiment.json', 'w') as f:
        json.dump(exp, f, indent=2)
    
    print("\n=== ALL DONE ===")


if __name__ == "__main__":
    main()
