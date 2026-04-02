#!/usr/bin/env blender --background --python
"""
B45 — Blender 3.6 LTS + LuxCoreRender

LuxCore — physically accurate renderer, known for interior quality.
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
    parser.add_argument('--time-limit', type=int, default=300)
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


def setup_lighting():
    """Setup lighting for LuxCore."""
    
    # World with sky
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    # Simple sky background
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Color'].default_value = (0.8, 0.9, 1.0, 1.0)  # Light blue sky
    bg.inputs['Strength'].default_value = 1.5
    
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (200, 0)
    
    links.new(bg.outputs['Background'], output.inputs['Surface'])
    
    bpy.context.scene.world = world
    
    # Sun light
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 5.0
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -10, 8)
    sun.rotation_euler = (math.radians(50), math.radians(15), math.radians(35))
    bpy.context.scene.collection.objects.link(sun)
    
    # Window area light
    window_data = bpy.data.lights.new("Window", 'AREA')
    window_data.energy = 300
    window_data.size = 1.2
    window_data.size_y = 1.8
    window = bpy.data.objects.new("Window", window_data)
    window.location = (-2.5, 2, 2.2)
    window.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(window)
    
    print("Lighting: Sky background + Sun + Window area")


def setup_luxcore(time_limit=300):
    """Configure LuxCore render settings."""
    scene = bpy.context.scene
    
    # Check if LuxCore is available
    try:
        scene.render.engine = 'LUXCORE'
        print("LuxCore engine enabled!")
    except Exception as e:
        print(f"LuxCore not available: {e}")
        print("Falling back to Cycles")
        return setup_cycles_fallback()
    
    try:
        # Path tracing with GPU
        scene.luxcore.config.engine = 'PATH'
        scene.luxcore.config.device = 'OCL'  # OpenCL GPU
        
        # Time-based halt
        scene.luxcore.halt.use_time = True
        scene.luxcore.halt.time = time_limit
        
        # Denoiser
        scene.luxcore.denoiser.enabled = True
        scene.luxcore.denoiser.type = 'OIDN'
        
        # Light path depths
        scene.luxcore.config.path.depth_total = 16
        scene.luxcore.config.path.depth_diffuse = 8
        scene.luxcore.config.path.depth_glossy = 8
        
        print(f"LuxCore: PATH engine, OCL device")
        print(f"Time limit: {time_limit}s")
        print(f"Denoiser: OIDN")
        
        # Convert materials to LuxCore
        try:
            bpy.ops.luxcore.convert_materials()
            print("Materials converted to LuxCore")
        except Exception as e:
            print(f"Material conversion: {e}")
        
        return {
            'engine': 'LUXCORE',
            'config': 'PATH',
            'device': 'OCL',
            'time_limit': time_limit,
            'denoiser': 'OIDN'
        }
    except Exception as e:
        print(f"LuxCore config error: {e}")
        print("Falling back to Cycles")
        return setup_cycles_fallback()


def setup_cycles_fallback():
    """Fallback to Cycles if LuxCore fails."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    
    # GPU setup
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for compute_type in ['CUDA', 'OPTIX', 'HIP']:
        try:
            prefs.compute_device_type = compute_type
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type != 'CPU']
            if devices:
                for device in prefs.devices:
                    device.use = device.type != 'CPU'
                scene.cycles.device = 'GPU'
                print(f"Cycles GPU: {compute_type}")
                break
        except:
            continue
    
    scene.cycles.samples = 2048
    scene.cycles.use_denoising = True
    
    return {
        'engine': 'CYCLES',
        'samples': 2048,
        'fallback': True
    }


def render(output_path, manifest, time_limit=300):
    """Render the scene."""
    scene = bpy.context.scene
    
    render_info = setup_luxcore(time_limit)
    
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    print(f"\nRendering {viewport['width']}x{viewport['height']}")
    if render_info.get('engine') == 'LUXCORE':
        print(f"Max time: {time_limit}s")
    
    start_time = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Render complete!")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.2f} min)")
    
    return elapsed, render_info


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B45 — Blender 3.6 LTS + LuxCoreRender")
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
    setup_lighting()
    
    print("\n=== RENDER SETTINGS ===")
    
    print("\n=== RENDER ===")
    elapsed, render_info = render(args.output, manifest, args.time_limit)
    
    exp = {
        "experiment": "B45",
        "method": "LuxCoreRender" if render_info.get('engine') == 'LUXCORE' else "Cycles (fallback)",
        "engine": render_info.get('engine', 'UNKNOWN'),
        "render_time_seconds": round(elapsed, 1),
        "render_time_minutes": round(elapsed / 60, 2),
        "resolution": [manifest.get('viewport', {}).get('width', 1066),
                      manifest.get('viewport', {}).get('height', 1239)]
    }
    exp.update(render_info)
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(exp, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
