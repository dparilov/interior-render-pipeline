#!/usr/bin/env blender --background --python
"""
render_golden.py — Canonical render script with all fixes

✅ FOV / aspect correction
✅ Viewport resolution
✅ Wall thickness offset
✅ Section plane clip_start

Usage:
    blender --background --python scripts/render_golden.py -- \
        --bundle examples/bathroom_05 \
        --output results/render.png
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
    parser.add_argument('--bundle', '-b', required=True, help='Bundle directory')
    parser.add_argument('--output', '-o', required=True, help='Output image path')
    parser.add_argument('--samples', type=int, default=128, help='Render samples')
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    mesh_count = len([o for o in bpy.data.objects if o.type == 'MESH'])
    print(f"Imported: {mesh_count} meshes")
    return mesh_count


def setup_camera(manifest):
    """Setup camera with all corrections."""
    eye = manifest['camera']['eye']
    fov_sketchup = manifest['camera']['fov']
    
    # Viewport from manifest (or defaults)
    viewport = manifest.get('viewport', {'width': 1920, 'height': 1080})
    width = viewport['width']
    height = viewport['height']
    aspect = width / height
    
    # FOV correction for portrait aspect
    if aspect < 1:
        fov_adjusted = fov_sketchup / aspect
    else:
        # Landscape: convert vertical to horizontal
        fov_adjusted = 2 * math.degrees(
            math.atan(math.tan(math.radians(fov_sketchup / 2)) * aspect)
        )
    
    print(f"Camera: {eye}")
    print(f"FOV: {fov_sketchup}° → {fov_adjusted:.1f}° (aspect={aspect:.3f})")
    
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.angle = math.radians(fov_adjusted)
    cam_data.clip_end = 100
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    
    cam_obj.location = (eye[0], eye[1], eye[2])
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = (math.radians(90), 0, 0)
    
    # Wall thickness offset
    wall_geo = manifest.get('wall_geometry')
    if wall_geo:
        thickness = wall_geo['wall_thickness']
        cam_obj.location.y -= thickness
        print(f"Wall offset: -{thickness}m → Y={cam_obj.location.y:.3f}m")
        
        # Clip start from section plane
        section_y = wall_geo['section_plane_y']
        clip_start = abs(cam_obj.location.y - section_y)
        cam_data.clip_start = clip_start
        print(f"Clip start: {clip_start:.3f}m")
    else:
        cam_data.clip_start = 0.1
    
    bpy.context.view_layer.update()
    
    return {
        'fov_sketchup': fov_sketchup,
        'fov_adjusted': round(fov_adjusted, 1),
        'resolution': [width, height]
    }


def setup_lighting():
    """Basic interior lighting."""
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 3
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
    bg.inputs[0].default_value = (0.8, 0.85, 0.9, 1)
    bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def render(output_path, manifest, samples=128):
    """Render with exact viewport resolution."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    
    # GPU if available
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except:
        pass
    
    # Exact viewport resolution
    viewport = manifest.get('viewport', {'width': 1920, 'height': 1080})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    
    scene.render.filepath = output_path
    
    print(f"Rendering: {viewport['width']}x{viewport['height']} @ {samples} samples")
    bpy.ops.render.render(write_still=True)
    print(f"Output: {output_path}")


def main():
    args = parse_args()
    
    print("=" * 60)
    print("render_golden.py — Canonical Render")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    if not glb_path.exists():
        glb_path = bundle_dir / 'model' / 'model.glb'
    
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(bundle_dir / 'manifest.json') as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    
    clear_scene()
    import_glb(str(glb_path))
    camera_info = setup_camera(manifest)
    setup_lighting()
    render(args.output, manifest, args.samples)
    
    # Write experiment.json
    exp = {
        "script": "render_golden.py",
        "bundle": str(bundle_dir.name),
        "camera": camera_info,
        "samples": args.samples
    }
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(exp, f, indent=2)
    
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
