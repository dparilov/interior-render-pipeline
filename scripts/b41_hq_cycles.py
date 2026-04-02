#!/usr/bin/env blender --background --python
"""
B41 — High-quality Cycles render (CPU benchmark)

Max quality Cycles without AI. CPU timing benchmark.
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
    parser.add_argument('--samples', type=int, default=512)
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
    
    # Create world with Nishita sky
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    
    # Clear default
    nodes.clear()
    
    # Sky texture (Nishita physical sky)
    sky = nodes.new('ShaderNodeTexSky')
    sky.location = (-300, 0)
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(35)
    sky.sun_rotation = math.radians(45)
    sky.altitude = 0
    sky.air_density = 1.0
    sky.dust_density = 0.5
    sky.ozone_density = 1.0
    
    # Background
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Strength'].default_value = 0.8  # Soft ambient
    
    # Output
    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (200, 0)
    
    links.new(sky.outputs['Color'], bg.inputs['Color'])
    links.new(bg.outputs['Background'], output.inputs['Surface'])
    
    bpy.context.scene.world = world
    
    # Sun lamp for direct light
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3.0
    sun_data.angle = math.radians(0.5)  # Soft shadows
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = (5, -10, 8)
    sun.rotation_euler = (math.radians(55), math.radians(10), math.radians(30))
    bpy.context.scene.collection.objects.link(sun)
    
    # Area light for fill (window simulation)
    area_data = bpy.data.lights.new("Window", 'AREA')
    area_data.energy = 200
    area_data.size = 1.5
    area_data.size_y = 2.0
    area = bpy.data.objects.new("Window", area_data)
    area.location = (-2, 2, 2.5)
    area.rotation_euler = (math.radians(90), 0, math.radians(-90))
    bpy.context.scene.collection.objects.link(area)
    
    # Ceiling bounce light
    bounce_data = bpy.data.lights.new("Bounce", 'AREA')
    bounce_data.energy = 50
    bounce_data.size = 3
    bounce_data.size_y = 3
    bounce = bpy.data.objects.new("Bounce", bounce_data)
    bounce.location = (1, 2, 3)
    bounce.rotation_euler = (math.radians(180), 0, 0)
    bpy.context.scene.collection.objects.link(bounce)
    
    print("Lighting: Nishita sky + Sun + Window area + Bounce")


def improve_materials():
    """Enhance existing materials for better rendering."""
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        
        nodes = mat.node_tree.nodes
        
        # Find Principled BSDF
        bsdf = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if not bsdf:
            continue
        
        # Enhance based on material name
        name_lower = mat.name.lower()
        
        if 'chrome' in name_lower or 'metal' in name_lower:
            bsdf.inputs['Metallic'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.1
        elif 'mirror' in name_lower:
            bsdf.inputs['Metallic'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.01
        elif 'ceramic' in name_lower or 'porcelain' in name_lower:
            bsdf.inputs['Roughness'].default_value = 0.05
            bsdf.inputs['Specular IOR Level'].default_value = 0.5
        elif 'floor' in name_lower or 'tile' in name_lower:
            bsdf.inputs['Roughness'].default_value = 0.15
            bsdf.inputs['Specular IOR Level'].default_value = 0.4


def setup_render_settings(samples=512):
    """Configure high-quality Cycles settings."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    
    # CPU rendering
    scene.cycles.device = 'CPU'
    
    # Samples
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.01
    scene.cycles.adaptive_min_samples = 64
    
    # Denoising - try OpenImageDenoise, fallback to none
    try:
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    except:
        scene.cycles.use_denoising = False
        print("OpenImageDenoise not available")
    
    # Light paths for interior
    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 12
    scene.cycles.volume_bounces = 0
    scene.cycles.transparent_max_bounces = 8
    
    # Caustics off (faster)
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    
    # Film
    scene.render.film_transparent = False
    
    print(f"Cycles: {samples} samples, adaptive, CPU")


def render(output_path, manifest, samples=512):
    """Render with timing benchmark."""
    scene = bpy.context.scene
    
    setup_render_settings(samples)
    
    # Resolution
    viewport = manifest.get('viewport', {'width': 1066, 'height': 1239})
    scene.render.resolution_x = viewport['width']
    scene.render.resolution_y = viewport['height']
    scene.render.resolution_percentage = 100
    scene.render.filepath = output_path
    
    print(f"\nRendering {viewport['width']}x{viewport['height']} @ {samples} samples (CPU)")
    print("This may take several minutes...")
    
    # Benchmark
    start_time = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Render complete!")
    print(f"⏱️  Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"📁 Output: {output_path}")
    
    return elapsed


def main():
    args = parse_args()
    
    print("=" * 60)
    print("B41 — High-quality Cycles render (CPU benchmark)")
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
    
    print("\n=== MATERIALS ===")
    improve_materials()
    
    print("\n=== RENDER ===")
    elapsed = render(args.output, manifest, args.samples)
    
    # Save experiment
    exp = {
        "experiment": "B41",
        "method": "High-quality Cycles CPU benchmark",
        "samples": args.samples,
        "device": "CPU",
        "denoiser": "OPENIMAGEDENOISE",
        "render_time_seconds": round(elapsed, 1),
        "render_time_minutes": round(elapsed / 60, 2),
        "resolution": [manifest.get('viewport', {}).get('width', 1066),
                      manifest.get('viewport', {}).get('height', 1239)],
        "lighting": "Nishita sky + Sun + Area lights",
        "light_bounces": {
            "max": 12,
            "diffuse": 4,
            "glossy": 4,
            "transmission": 12
        }
    }
    
    exp_path = output_dir / 'experiment.json'
    with open(exp_path, 'w') as f:
        json.dump(exp, f, indent=2)
    
    print(f"\nWrote: {exp_path}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
