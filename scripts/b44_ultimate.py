#!/usr/bin/env blender --background --python
"""
B44 — Cycles Ultimate (4096 samples + Path Guiding)

Maximum quality Cycles — brute force up to 5 minutes.
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
    parser.add_argument('--samples', type=int, default=4096)
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


def setup_ultimate_lighting():
    """Ultimate quality lighting setup."""
    
    # World with Nishita sky
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    # Physical sky
    sky = nodes.new('ShaderNodeTexSky')
    sky.location = (-300, 0)
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(30)
    sky.sun_rotation = math.radians(60)
    sky.sun_intensity = 1.0
    sky.sun_disc = True
    
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Strength'].default_value = 1.0
    
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (200, 0)
    
    links.new(sky.outputs['Color'], bg.inputs['Color'])
    links.new(bg.outputs['Background'], output.inputs['Surface'])
    
    bpy.context.scene.world = world
    
    # Sun with sharp shadows
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 5.0
    sun_data.angle = 0.02  # Sharp shadows
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -10, 8)
    sun.rotation_euler = (math.radians(50), math.radians(15), math.radians(35))
    bpy.context.scene.collection.objects.link(sun)
    
    # Window area light (soft fill from window)
    window_data = bpy.data.lights.new("Window", 'AREA')
    window_data.energy = 300
    window_data.size = 1.2
    window_data.size_y = 1.8
    window_data.color = (1.0, 0.98, 0.95)  # Warm daylight
    window = bpy.data.objects.new("Window", window_data)
    window.location = (-2.5, 2, 2.2)
    window.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(window)
    
    # Ceiling bounce
    bounce_data = bpy.data.lights.new("Bounce", 'AREA')
    bounce_data.energy = 80
    bounce_data.size = 4
    bounce_data.size_y = 4
    bounce_data.color = (1.0, 0.99, 0.97)
    bounce = bpy.data.objects.new("Bounce", bounce_data)
    bounce.location = (1, 2.5, 3.2)
    bounce.rotation_euler = (math.radians(180), 0, 0)
    bpy.context.scene.collection.objects.link(bounce)
    
    print("Lighting: Nishita sky + Sun (sharp) + Window area + Ceiling bounce")


def setup_ultimate_render(samples=4096):
    """Configure ultimate quality Cycles settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    
    # GPU setup
    prefs = bpy.context.preferences.addons['cycles'].preferences
    gpu_type = None
    
    for compute_type in ['CUDA', 'OPTIX', 'HIP']:
        try:
            prefs.compute_device_type = compute_type
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type != 'CPU']
            if devices:
                gpu_type = compute_type
                break
        except:
            continue
    
    gpu_name = "CPU"
    if gpu_type:
        for device in prefs.devices:
            if device.type != 'CPU':
                device.use = True
                gpu_name = device.name
            else:
                device.use = False
        scene.cycles.device = 'GPU'
        print(f"GPU: {gpu_name} ({gpu_type})")
    else:
        scene.cycles.device = 'CPU'
        print("GPU not available, using CPU")
    
    # Ultimate samples
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.001  # Very strict
    scene.cycles.adaptive_min_samples = 256
    
    # Path Guiding (Blender 4.x feature)
    try:
        scene.cycles.use_guiding = True
        scene.cycles.guiding_training_samples = 128
        print("Path Guiding: Enabled")
    except:
        print("Path Guiding: Not available")
    
    # Denoiser - try OPTIX first
    denoiser = "None"
    try:
        scene.cycles.use_denoising = True
        if gpu_type in ['CUDA', 'OPTIX']:
            try:
                scene.cycles.denoiser = 'OPTIX'
                denoiser = "OPTIX"
            except:
                scene.cycles.denoiser = 'OPENIMAGEDENOISE'
                denoiser = "OPENIMAGEDENOISE"
        else:
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
            denoiser = "OPENIMAGEDENOISE"
    except:
        scene.cycles.use_denoising = False
    
    print(f"Denoiser: {denoiser}")
    
    # Maximum light paths
    scene.cycles.max_bounces = 16
    scene.cycles.diffuse_bounces = 8
    scene.cycles.glossy_bounces = 8
    scene.cycles.transmission_bounces = 16
    scene.cycles.volume_bounces = 2
    scene.cycles.transparent_max_bounces = 16
    
    # Caustics ON (for glass/water)
    scene.cycles.caustics_reflective = True
    scene.cycles.caustics_refractive = True
    
    print(f"Samples: {samples}, adaptive threshold: 0.001")
    print("Light bounces: max=16, diffuse=8, glossy=8, transmission=16")
    print("Caustics: Enabled")
    
    return {
        'gpu_type': gpu_type or 'CPU',
        'gpu_name': gpu_name,
        'denoiser': denoiser,
        'samples': samples
    }


def render(output_path, manifest, samples=4096):
    """Render with ultimate quality."""
    scene = bpy.context.scene
    
    render_info = setup_ultimate_render(samples)
    
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    print(f"\nRendering {viewport['width']}x{viewport['height']} @ {samples} samples")
    print("Target: < 5 minutes")
    
    start_time = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Render complete!")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.2f} min)")
    
    return elapsed, render_info


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B44 — Cycles Ultimate (4096 samples + Path Guiding)")
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
    setup_ultimate_lighting()
    
    print("\n=== RENDER SETTINGS ===")
    # Settings will be printed in render()
    
    print("\n=== RENDER ===")
    elapsed, render_info = render(args.output, manifest, args.samples)
    
    exp = {
        "experiment": "B44",
        "method": "Cycles Ultimate (4096 samples + Path Guiding)",
        "gpu_type": render_info['gpu_type'],
        "gpu_name": render_info['gpu_name'],
        "denoiser": render_info['denoiser'],
        "samples": args.samples,
        "adaptive_threshold": 0.001,
        "path_guiding": True,
        "caustics": True,
        "light_bounces": {"max": 16, "diffuse": 8, "glossy": 8, "transmission": 16},
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
