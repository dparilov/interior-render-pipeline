#!/usr/bin/env blender --background --python
"""
B43 — LuxCoreRender GPU test

Alternative physically-based renderer comparison with Cycles.
"""

import bpy
import sys
import json
import math
import time
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
    parser.add_argument('--samples', type=int, default=2000)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(filepath):
    bpy.ops.import_scene.gltf(filepath=filepath)
    return len([o for o in bpy.data.objects if o.type == 'MESH'])


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
    return fov_adjusted


def setup_lighting_cycles():
    """Setup Cycles lighting first (will be converted or recreated for LuxCore)."""
    # Sun
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -10, 8)
    sun.rotation_euler = (math.radians(55), math.radians(10), math.radians(30))
    bpy.context.scene.collection.objects.link(sun)
    
    # Area light
    area_data = bpy.data.lights.new("Window", 'AREA')
    area_data.energy = 200
    area_data.size = 1.5
    area = bpy.data.objects.new("Window", area_data)
    area.location = (-2, 2, 2.5)
    area.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(area)
    
    # World
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    bg = nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0.8, 0.85, 0.9, 1)
        bg.inputs['Strength'].default_value = 0.5
    bpy.context.scene.world = world


def enable_luxcore():
    """Enable LuxCore addon and set as render engine."""
    # Try to enable the addon
    try:
        bpy.ops.preferences.addon_enable(module='BlendLuxCore')
        print("LuxCore addon enabled")
        return True
    except Exception as e:
        print(f"Failed to enable LuxCore: {e}")
        
        # Try alternative module names
        for module_name in ['blendluxcore', 'luxcore', 'BlendLuxCore']:
            try:
                bpy.ops.preferences.addon_enable(module=module_name)
                print(f"LuxCore addon enabled as '{module_name}'")
                return True
            except:
                continue
        
        return False


def setup_luxcore_render(samples=2000):
    """Configure LuxCore render settings."""
    scene = bpy.context.scene
    
    # Set render engine
    scene.render.engine = 'LUXCORE'
    
    # LuxCore config
    try:
        # Path tracing engine
        scene.luxcore.config.engine = 'PATH'
        
        # GPU rendering via OpenCL
        scene.luxcore.config.device = 'OCL'
        
        # Halt conditions
        scene.luxcore.halt.use_samples = True
        scene.luxcore.halt.samples = samples
        
        # Denoiser
        if hasattr(scene.luxcore, 'denoiser'):
            scene.luxcore.denoiser.enabled = True
            scene.luxcore.denoiser.type = 'OIDN'
        
        print(f"LuxCore: PATH engine, OpenCL GPU, {samples} samples")
        return True
        
    except AttributeError as e:
        print(f"LuxCore config error: {e}")
        return False


def render(output_path, manifest, samples=2000):
    """Render with LuxCore."""
    scene = bpy.context.scene
    
    # Enable LuxCore
    if not enable_luxcore():
        print("⚠️ LuxCore not available, falling back to Cycles")
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = samples
        scene.cycles.device = 'GPU'
    else:
        if not setup_luxcore_render(samples):
            print("⚠️ LuxCore config failed, falling back to Cycles")
            scene.render.engine = 'CYCLES'
            scene.cycles.samples = samples
            scene.cycles.device = 'GPU'
    
    # Resolution
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    engine = scene.render.engine
    print(f"\nRendering with {engine}...")
    print(f"Resolution: {viewport['width']}x{viewport['height']}")
    
    start_time = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Render complete!")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    
    return elapsed, engine


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B43 — LuxCoreRender GPU test")
    print("=" * 60)
    
    bundle_dir = Path(args.bundle)
    glb_path = bundle_dir / 'model.glb'
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(bundle_dir / 'manifest.json') as f:
        manifest = json.load(f)
    
    print(f"\nBundle: {bundle_dir}")
    
    clear_scene()
    
    print("\n=== IMPORT ===")
    mesh_count = import_glb(str(glb_path))
    print(f"Meshes: {mesh_count}")
    
    print("\n=== CAMERA ===")
    fov = setup_camera(manifest)
    print(f"FOV: {fov:.1f}°")
    
    print("\n=== LIGHTING ===")
    setup_lighting_cycles()
    
    print("\n=== RENDER ===")
    elapsed, engine = render(args.output, manifest, args.samples)
    
    exp = {
        "experiment": "B43",
        "method": "LuxCoreRender GPU test",
        "engine": engine,
        "samples": args.samples,
        "render_time_seconds": round(elapsed, 1),
        "render_time_minutes": round(elapsed / 60, 2),
        "resolution": [manifest.get('viewport', {}).get('width', 1066),
                      manifest.get('viewport', {}).get('height', 1239)]
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(exp, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
