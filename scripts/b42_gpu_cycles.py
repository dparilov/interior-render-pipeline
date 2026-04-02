#!/usr/bin/env blender --background --python
"""
B42 — Cycles GPU on RunPod (high samples)

Same setup as B41 but GPU + 2048 samples + OPTIX denoiser.
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
    parser.add_argument('--samples', type=int, default=2048)
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


def setup_hq_lighting():
    """High-quality interior lighting with procedural sky."""
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    sky = nodes.new('ShaderNodeTexSky')
    sky.location = (-300, 0)
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(35)
    sky.sun_rotation = math.radians(45)
    
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Strength'].default_value = 0.8
    
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (200, 0)
    
    links.new(sky.outputs['Color'], bg.inputs['Color'])
    links.new(bg.outputs['Background'], output.inputs['Surface'])
    
    bpy.context.scene.world = world
    
    # Sun
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3.0
    sun_data.angle = math.radians(0.5)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -10, 8)
    sun.rotation_euler = (math.radians(55), math.radians(10), math.radians(30))
    bpy.context.scene.collection.objects.link(sun)
    
    # Window area light
    area_data = bpy.data.lights.new("Window", 'AREA')
    area_data.energy = 200
    area_data.size = 1.5
    area_data.size_y = 2.0
    area = bpy.data.objects.new("Window", area_data)
    area.location = (-2, 2, 2.5)
    area.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(area)
    
    # Bounce light
    bounce_data = bpy.data.lights.new("Bounce", 'AREA')
    bounce_data.energy = 50
    bounce_data.size = 3
    bounce = bpy.data.objects.new("Bounce", bounce_data)
    bounce.location = (1, 2, 3)
    bounce.rotation_euler = (math.radians(180), 0, 0)
    bpy.context.scene.collection.objects.link(bounce)


def setup_gpu_render(samples=2048):
    """Configure GPU Cycles with high quality settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    
    # GPU setup
    prefs = bpy.context.preferences.addons['cycles'].preferences
    
    # Try CUDA first, then OPTIX
    gpu_type = None
    for compute_type in ['CUDA', 'OPTIX', 'HIP', 'METAL']:
        try:
            prefs.compute_device_type = compute_type
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type != 'CPU']
            if devices:
                gpu_type = compute_type
                break
        except:
            continue
    
    if not gpu_type:
        print("⚠️ No GPU found, falling back to CPU")
        scene.cycles.device = 'CPU'
        gpu_name = "CPU (fallback)"
    else:
        # Enable all GPU devices
        gpu_names = []
        for device in prefs.devices:
            if device.type != 'CPU':
                device.use = True
                gpu_names.append(device.name)
            else:
                device.use = False
        
        scene.cycles.device = 'GPU'
        gpu_name = ", ".join(gpu_names) if gpu_names else gpu_type
        print(f"GPU: {gpu_name} ({gpu_type})")
    
    # High samples
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.005
    scene.cycles.adaptive_min_samples = 128
    
    # Denoiser - try OPTIX first (GPU), fallback to OPENIMAGEDENOISE
    denoiser_used = "None"
    try:
        scene.cycles.use_denoising = True
        if gpu_type == 'OPTIX' or gpu_type == 'CUDA':
            try:
                scene.cycles.denoiser = 'OPTIX'
                denoiser_used = "OPTIX"
            except:
                scene.cycles.denoiser = 'OPENIMAGEDENOISE'
                denoiser_used = "OPENIMAGEDENOISE"
        else:
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
            denoiser_used = "OPENIMAGEDENOISE"
    except:
        scene.cycles.use_denoising = False
        denoiser_used = "None"
    
    print(f"Denoiser: {denoiser_used}")
    
    # Light paths
    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 12
    scene.cycles.volume_bounces = 0
    
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    
    return {
        'gpu_type': gpu_type or 'CPU',
        'gpu_name': gpu_name,
        'denoiser': denoiser_used
    }


def render(output_path, manifest, samples=2048):
    """Render with GPU and timing."""
    scene = bpy.context.scene
    
    gpu_info = setup_gpu_render(samples)
    
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    print(f"\nRendering {viewport['width']}x{viewport['height']} @ {samples} samples (GPU)")
    
    start_time = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Render complete!")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    
    return elapsed, gpu_info


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B42 — Cycles GPU on RunPod (high samples)")
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
    setup_hq_lighting()
    
    print("\n=== RENDER ===")
    elapsed, gpu_info = render(args.output, manifest, args.samples)
    
    exp = {
        "experiment": "B42",
        "method": "Cycles GPU high samples",
        "device": "GPU",
        "gpu_type": gpu_info['gpu_type'],
        "gpu_name": gpu_info['gpu_name'],
        "denoiser": gpu_info['denoiser'],
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
