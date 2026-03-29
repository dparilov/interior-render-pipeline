#!/usr/bin/env blender --background --python
"""
Blender headless mask renderer for IRP.

Renders entity masks from GLB/FBX models without SketchUp.

Usage:
  blender --background --python blender_masks.py -- \
    --input model.glb \
    --output masks/ \
    --resolution 1024x1024 \
    --camera auto

Entity naming convention:
  Objects with "IRP_<entity>" in name are recognized as entities.
  e.g., IRP_walls, IRP_floor, Bathtub_IRP_bathtub, Mirror_IRP_mirror
"""

import bpy
import os
import sys
import argparse
import json
from pathlib import Path
from mathutils import Vector


def parse_args():
    """Parse command line arguments after '--'."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    parser = argparse.ArgumentParser(description='Render entity masks from 3D model')
    parser.add_argument('--input', '-i', required=True, help='Input model (GLB/FBX/DAE)')
    parser.add_argument('--output', '-o', required=True, help='Output directory for masks')
    parser.add_argument('--resolution', '-r', default='1024x1024', help='Resolution WxH')
    parser.add_argument('--camera', '-c', default='auto', help='Camera name or "auto"')
    parser.add_argument('--manifest', '-m', help='Output manifest.json path')
    parser.add_argument('--beauty', '-b', help='Also render beauty pass to this path')
    parser.add_argument('--depth', '-d', help='Also render depth pass to this path')
    
    return parser.parse_args(argv)


def clear_scene():
    """Clear default scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(filepath):
    """Import 3D model based on extension."""
    ext = Path(filepath).suffix.lower()
    
    if ext == '.glb' or ext == '.gltf':
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.dae':
        bpy.ops.wm.collada_import(filepath=filepath)
    elif ext == '.blend':
        bpy.ops.wm.open_mainfile(filepath=filepath)
    else:
        raise ValueError(f"Unsupported format: {ext}")
    
    print(f"Imported {filepath}: {len(bpy.data.objects)} objects")


def find_entities():
    """Find all IRP entities in scene."""
    entities = {}
    
    for obj in bpy.data.objects:
        name = obj.name
        
        # Look for IRP_ pattern
        if 'IRP_' in name:
            # Extract entity name
            parts = name.split('IRP_')
            if len(parts) >= 2:
                entity_name = parts[-1].split('_')[0].split('.')[0].lower()
                
                if entity_name not in entities:
                    entities[entity_name] = {
                        'objects': [],
                        'meshes': []
                    }
                
                entities[entity_name]['objects'].append(obj)
                
                # Find child meshes
                if obj.type == 'MESH':
                    entities[entity_name]['meshes'].append(obj)
                for child in obj.children_recursive:
                    if child.type == 'MESH':
                        entities[entity_name]['meshes'].append(child)
    
    # Deduplicate meshes
    for entity_name in entities:
        entities[entity_name]['meshes'] = list(set(entities[entity_name]['meshes']))
    
    return entities


def setup_camera(camera_name='auto', resolution=(1024, 1024)):
    """Setup camera for rendering."""
    scene = bpy.context.scene
    
    if camera_name == 'auto':
        # Find existing camera or create one
        cameras = [o for o in bpy.data.objects if o.type == 'CAMERA']
        if cameras:
            camera = cameras[0]
        else:
            # Create camera looking at scene center
            bpy.ops.object.camera_add(location=(5, -5, 3))
            camera = bpy.context.object
            camera.rotation_euler = (1.1, 0, 0.8)
    else:
        camera = bpy.data.objects.get(camera_name)
        if not camera:
            raise ValueError(f"Camera '{camera_name}' not found")
    
    scene.camera = camera
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100
    
    return camera


def setup_mask_render():
    """Configure render settings for mask output."""
    scene = bpy.context.scene
    
    # Use Cycles for better mask rendering
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1  # We only need 1 sample for masks
    scene.cycles.use_denoising = False
    
    # Create world if missing
    if not bpy.data.worlds:
        bpy.ops.world.new()
    world = bpy.data.worlds[0]
    scene.world = world
    
    # Setup white background
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (1, 1, 1, 1)
    
    # Output settings
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'


def render_entity_mask(entity_name, meshes, output_path):
    """Render mask for single entity."""
    scene = bpy.context.scene
    
    # Hide all objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = True
    
    # Show only entity meshes with black material
    mask_material = bpy.data.materials.new(name="MaskMaterial")
    mask_material.use_nodes = True
    mask_material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0, 0, 0, 1)
    mask_material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    
    for mesh in meshes:
        mesh.hide_render = False
        # Apply mask material
        if mesh.data.materials:
            mesh.data.materials[0] = mask_material
        else:
            mesh.data.materials.append(mask_material)
    
    # Render
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    
    print(f"  Rendered {entity_name} mask: {output_path}")
    
    # Restore visibility
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = False


def render_all_masks(entities, output_dir):
    """Render masks for all entities."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    setup_mask_render()
    
    masks = {}
    for entity_name, data in entities.items():
        if not data['meshes']:
            print(f"  Skipping {entity_name}: no meshes")
            continue
        
        output_path = output_dir / f"{entity_name}.png"
        render_entity_mask(entity_name, data['meshes'], output_path)
        masks[entity_name] = str(output_path)
    
    return masks


def setup_beauty_render():
    """Configure render settings for beauty pass."""
    scene = bpy.context.scene
    
    # Use EEVEE for faster headless rendering (no GPU required)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 64
    
    # Transparent background for compositing
    scene.render.film_transparent = True
    
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'


def render_beauty(output_path):
    """Render beauty pass with all objects visible."""
    scene = bpy.context.scene
    
    setup_beauty_render()
    
    # Show all meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = False
    
    # Add lighting if none exists
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
    if not lights:
        # Add sun light
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
        sun = bpy.context.object
        sun.data.energy = 3.0
        
        # Add fill light
        bpy.ops.object.light_add(type='AREA', location=(-3, -3, 5))
        fill = bpy.context.object
        fill.data.energy = 100.0
    
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    
    print(f"  Rendered beauty: {output_path}")


def setup_depth_render():
    """Configure render settings for depth pass."""
    scene = bpy.context.scene
    
    # Use EEVEE for depth - faster and works without GPU
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 1
    
    # Enable Z pass
    scene.view_layers["ViewLayer"].use_pass_z = True
    
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'BW'
    scene.render.image_settings.color_depth = '16'


def render_depth(output_path):
    """Render depth pass using compositor."""
    scene = bpy.context.scene
    
    setup_depth_render()
    
    # Show all meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_render = False
    
    # Setup compositor for depth output
    scene.use_nodes = True
    tree = scene.node_tree
    
    # Clear existing nodes
    for node in tree.nodes:
        tree.nodes.remove(node)
    
    # Create nodes
    render_layers = tree.nodes.new('CompositorNodeRLayers')
    normalize = tree.nodes.new('CompositorNodeNormalize')
    invert = tree.nodes.new('CompositorNodeInvert')
    composite = tree.nodes.new('CompositorNodeComposite')
    
    # Position nodes
    render_layers.location = (0, 0)
    normalize.location = (200, 0)
    invert.location = (400, 0)
    composite.location = (600, 0)
    
    # Link nodes: Depth -> Normalize -> Invert -> Output
    tree.links.new(render_layers.outputs['Depth'], normalize.inputs[0])
    tree.links.new(normalize.outputs[0], invert.inputs['Color'])
    tree.links.new(invert.outputs[0], composite.inputs['Image'])
    
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    
    # Cleanup compositor
    scene.use_nodes = False
    
    print(f"  Rendered depth: {output_path}")


def validate_blender_output(masks_dir, beauty_path, depth_path, manifest):
    """Validate generated output for contract compliance."""
    errors = []
    
    masks_dir = Path(masks_dir)
    
    # Check beauty exists
    if beauty_path and not Path(beauty_path).exists():
        errors.append(f"Beauty not found: {beauty_path}")
    
    # Check depth exists
    if depth_path and not Path(depth_path).exists():
        errors.append(f"Depth not found: {depth_path}")
    
    # Check all entity masks exist
    for entity in manifest.get('entities', []):
        mask_path = masks_dir / f"{entity['name']}.png"
        if not mask_path.exists():
            errors.append(f"Mask not found: {mask_path}")
    
    # Check resolution consistency (if PIL available)
    try:
        from PIL import Image
        
        expected_res = tuple(manifest.get('resolution', [0, 0]))
        
        if beauty_path and Path(beauty_path).exists():
            img = Image.open(beauty_path)
            if img.size != expected_res:
                errors.append(f"Beauty size mismatch: {img.size} vs {expected_res}")
        
        if depth_path and Path(depth_path).exists():
            img = Image.open(depth_path)
            if img.size != expected_res:
                errors.append(f"Depth size mismatch: {img.size} vs {expected_res}")
        
        for entity in manifest.get('entities', []):
            mask_path = masks_dir / f"{entity['name']}.png"
            if mask_path.exists():
                img = Image.open(mask_path)
                if img.size != expected_res:
                    errors.append(f"Mask {entity['name']} size mismatch: {img.size} vs {expected_res}")
    except ImportError:
        errors.append("PIL not available for size validation")
    
    return errors


def main():
    args = parse_args()
    
    # Parse resolution
    w, h = map(int, args.resolution.split('x'))
    
    print(f"=== Blender Mask Renderer ===")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Resolution: {w}x{h}")
    
    # Setup
    clear_scene()
    import_model(args.input)
    
    # Find entities
    entities = find_entities()
    print(f"\nFound {len(entities)} entities:")
    for name, data in entities.items():
        print(f"  {name}: {len(data['meshes'])} meshes")
    
    if not entities:
        print("ERROR: No IRP entities found in model")
        sys.exit(1)
    
    # Setup camera
    setup_camera(args.camera, (w, h))
    
    # Render beauty pass if requested
    if args.beauty:
        print("\nRendering beauty pass...")
        render_beauty(args.beauty)
    
    # Render depth pass if requested
    if args.depth:
        print("\nRendering depth pass...")
        render_depth(args.depth)
    
    # Render masks
    print("\nRendering masks...")
    masks = render_all_masks(entities, args.output)
    
    # Save manifest if requested
    if args.manifest:
        manifest = {
            'version': '1.0',
            'generator': 'blender_masks.py',
            'blender_version': bpy.app.version_string,
            'source': args.input,
            'resolution': [w, h],
            'base_image': args.beauty if args.beauty else None,
            'depth_map': args.depth if args.depth else None,
            'depth_type': 'normalized_inverted',
            'entities': [
                {
                    'name': name,
                    'mask': f"masks/{name}.png",
                    'mesh_count': len(entities[name]['meshes']),
                    'reference': None,  # Manual addition required
                    'ipadapter_weight': 0.5,  # Default, adjust manually
                    'role': 'surface' if name in ['walls', 'floor', 'ceiling'] else 'fixture',
                    'critical': name in ['walls', 'floor', 'bathtub', 'vanity'],
                    'render_mode': 'regional_texture'
                }
                for name in sorted(entities.keys())
            ],
            'requires_enrichment': [
                'references/ directory with reference images',
                'technical_spec.md',
                'ipadapter_weight calibration per entity'
            ]
        }
        with open(args.manifest, 'w') as f:
            json.dump(manifest, f, indent=2)
        print(f"\nManifest saved: {args.manifest}")
        
        # Validate output
        print("\nValidating output...")
        validation_errors = validate_blender_output(args.output, args.beauty, args.depth, manifest)
        if validation_errors:
            print("⚠️  Validation warnings:")
            for err in validation_errors:
                print(f"  - {err}")
        else:
            print("✅ Output validation passed")
    
    print(f"\n=== Done: {len(masks)} masks rendered ===")


if __name__ == "__main__":
    main()
