#!/usr/bin/env python3
"""Compare DAE and GLB imports to check for data loss."""

import bpy
import sys
import json
from pathlib import Path

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def get_mesh_stats():
    """Get vertex/face/object counts."""
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    verts = sum(len(o.data.vertices) for o in meshes)
    faces = sum(len(o.data.polygons) for o in meshes)
    return {
        'objects': len(meshes),
        'vertices': verts,
        'faces': faces
    }

def get_bounds():
    """Get scene bounds."""
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for v in obj.data.vertices:
            co = obj.matrix_world @ v.co
            min_x = min(min_x, co.x)
            max_x = max(max_x, co.x)
            min_y = min(min_y, co.y)
            max_y = max(max_y, co.y)
            min_z = min(min_z, co.z)
            max_z = max(max_z, co.z)
    
    return {
        'x': [round(min_x, 3), round(max_x, 3)],
        'y': [round(min_y, 3), round(max_y, 3)],
        'z': [round(min_z, 3), round(max_z, 3)]
    }

def compare_imports(bundle_path):
    """Compare GLB and DAE imports."""
    results = {}
    
    # 1. Import GLB
    print("\n=== GLB Import ===")
    clear_scene()
    glb_path = f"{bundle_path}/model/model.glb"
    bpy.ops.import_scene.gltf(filepath=glb_path)
    
    results['glb'] = get_mesh_stats()
    results['glb']['bounds'] = get_bounds()
    print(f"Objects: {results['glb']['objects']}")
    print(f"Vertices: {results['glb']['vertices']}")
    print(f"Faces: {results['glb']['faces']}")
    print(f"Bounds: {results['glb']['bounds']}")
    
    # 2. Import DAE
    print("\n=== DAE Import ===")
    clear_scene()
    
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from dae_to_blender import import_dae_geometry
    
    dae_path = f"{bundle_path}/model/model.dae"
    import_dae_geometry(dae_path)
    
    results['dae'] = get_mesh_stats()
    results['dae']['bounds'] = get_bounds()
    print(f"Objects: {results['dae']['objects']}")
    print(f"Vertices: {results['dae']['vertices']}")
    print(f"Faces: {results['dae']['faces']}")
    print(f"Bounds: {results['dae']['bounds']}")
    
    # 3. Compare
    print("\n=== Comparison ===")
    diff_verts = results['dae']['vertices'] - results['glb']['vertices']
    diff_faces = results['dae']['faces'] - results['glb']['faces']
    diff_objs = results['dae']['objects'] - results['glb']['objects']
    
    print(f"Objects diff: {diff_objs:+d} ({results['dae']['objects']} vs {results['glb']['objects']})")
    print(f"Vertices diff: {diff_verts:+d} ({results['dae']['vertices']} vs {results['glb']['vertices']})")
    print(f"Faces diff: {diff_faces:+d} ({results['dae']['faces']} vs {results['glb']['faces']})")
    
    results['comparison'] = {
        'objects_diff': diff_objs,
        'vertices_diff': diff_verts,
        'faces_diff': diff_faces,
        'glb_preferred': diff_faces < 0  # If DAE has fewer faces, prefer GLB
    }
    
    if diff_faces < -1000:
        print("\n⚠️ WARNING: DAE has significantly fewer faces!")
        print("Recommendation: Use GLB for geometry, DAE only for camera")
    elif diff_faces > 1000:
        print("\n✓ DAE has more geometry (might include hidden elements)")
    else:
        print("\n✓ Geometry is similar")
    
    return results

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    
    bundle_path = argv[0] if argv else "/tmp/irp-delta/examples/bathroom_01"
    
    results = compare_imports(bundle_path)
    
    # Save results
    output_path = f"{bundle_path}/dae_glb_comparison.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {output_path}")

if __name__ == "__main__":
    main()
