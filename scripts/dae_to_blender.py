#!/usr/bin/env python3
"""
Import DAE via pycollada into Blender.

This script provides DAE import functionality since Blender 4.0 removed
the built-in Collada importer. Uses pycollada to parse DAE files and
creates native Blender objects.

Usage (in Blender):
    import sys
    sys.path.insert(0, '/path/to/scripts')
    from dae_to_blender import import_dae
    
    objects, camera = import_dae('/path/to/model.dae')

Or standalone:
    blender --background --python dae_to_blender.py -- --dae model.dae
"""

import sys
import os
import argparse

# Add pycollada to path if needed
try:
    from collada import Collada
    import numpy as np
except ImportError:
    # Try user site-packages
    user_site = os.path.expanduser('~/.local/lib/python3.12/site-packages')
    if user_site not in sys.path:
        sys.path.insert(0, user_site)
    from collada import Collada
    import numpy as np

import bpy
import math
from mathutils import Matrix, Vector


def import_dae_geometry(dae_path: str, scale: float = 0.01):
    """
    Import geometry from DAE file.
    
    Args:
        dae_path: Path to DAE file
        scale: Scale factor (0.01 for cm to m conversion)
    
    Returns:
        List of created Blender objects
    """
    dae = Collada(dae_path)
    objects = []
    
    print(f"Importing geometry from {dae_path}")
    
    for bound_geom in dae.scene.objects('geometry'):
        geom_id = bound_geom.original.id if hasattr(bound_geom.original, 'id') else 'unnamed'
        mesh = bpy.data.meshes.new(geom_id)
        
        all_verts = []
        all_faces = []
        offset = 0
        
        for prim in bound_geom.primitives():
            # Get vertices (apply scale for unit conversion)
            if hasattr(prim, 'vertex') and prim.vertex is not None:
                for v in prim.vertex:
                    all_verts.append((v[0] * scale, v[1] * scale, v[2] * scale))
                
                # Get faces (triangles or polygons)
                if hasattr(prim, 'vertex_index') and prim.vertex_index is not None:
                    for tri in prim.vertex_index:
                        all_faces.append(tuple(int(i) + offset for i in tri))
                
                offset += len(prim.vertex)
        
        if all_verts and all_faces:
            mesh.from_pydata(all_verts, [], all_faces)
            mesh.update()
            
            obj = bpy.data.objects.new(geom_id, mesh)
            
            # Apply transform from scene graph
            if hasattr(bound_geom, 'matrix') and bound_geom.matrix is not None:
                # Convert numpy matrix to Blender Matrix
                m = bound_geom.matrix
                blender_matrix = Matrix([
                    [m[0, 0], m[0, 1], m[0, 2], m[0, 3] * scale],
                    [m[1, 0], m[1, 1], m[1, 2], m[1, 3] * scale],
                    [m[2, 0], m[2, 1], m[2, 2], m[2, 3] * scale],
                    [m[3, 0], m[3, 1], m[3, 2], m[3, 3]]
                ])
                obj.matrix_world = blender_matrix
            
            bpy.context.collection.objects.link(obj)
            objects.append(obj)
            print(f"  Created: {geom_id} ({len(all_verts)} verts, {len(all_faces)} faces)")
    
    print(f"Imported {len(objects)} geometry objects")
    return objects


def import_dae_camera(dae_path: str, camera_name: str = None, scale: float = 0.01):
    """
    Import camera from DAE file with full transform.
    
    Args:
        dae_path: Path to DAE file
        camera_name: Optional camera name to find (e.g., "Сцена_№1")
        scale: Scale factor for position (0.01 for cm to m)
    
    Returns:
        Created Blender camera object, or None if not found
    """
    dae = Collada(dae_path)
    
    print(f"Looking for camera in {dae_path}")
    
    for bound_cam in dae.scene.objects('camera'):
        cam_id = bound_cam.original.id if hasattr(bound_cam.original, 'id') else 'unnamed'
        
        # If specific camera requested, check name
        if camera_name and camera_name not in cam_id:
            continue
        
        print(f"  Found camera: {cam_id}")
        
        # Create Blender camera
        cam = bpy.data.cameras.new(cam_id)
        
        # Set FOV from DAE
        if hasattr(bound_cam.original, 'yfov'):
            cam.angle = math.radians(bound_cam.original.yfov)
            print(f"    FOV: {bound_cam.original.yfov}°")
        
        # Create camera object
        obj = bpy.data.objects.new(cam_id, cam)
        bpy.context.collection.objects.link(obj)
        
        # Apply transform matrix
        if hasattr(bound_cam, 'matrix') and bound_cam.matrix is not None:
            m = bound_cam.matrix
            # Position needs scale, rotation doesn't
            blender_matrix = Matrix([
                [m[0, 0], m[0, 1], m[0, 2], m[0, 3] * scale],
                [m[1, 0], m[1, 1], m[1, 2], m[1, 3] * scale],
                [m[2, 0], m[2, 1], m[2, 2], m[2, 3] * scale],
                [m[3, 0], m[3, 1], m[3, 2], m[3, 3]]
            ])
            obj.matrix_world = blender_matrix
            
            pos = obj.location
            print(f"    Position: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
        
        # Set as scene camera
        bpy.context.scene.camera = obj
        
        return obj
    
    print("  No matching camera found")
    return None


def import_dae(dae_path: str, camera_name: str = None, scale: float = 0.01):
    """
    Full DAE import: geometry + camera.
    
    Args:
        dae_path: Path to DAE file
        camera_name: Optional specific camera to import
        scale: Unit conversion scale (0.01 for cm to m)
    
    Returns:
        Tuple of (list of geometry objects, camera object or None)
    """
    objects = import_dae_geometry(dae_path, scale)
    camera = import_dae_camera(dae_path, camera_name, scale)
    
    return objects, camera


def main():
    """CLI entry point for Blender."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    parser = argparse.ArgumentParser(description='Import DAE into Blender via pycollada')
    parser.add_argument('--dae', required=True, help='Path to DAE file')
    parser.add_argument('--camera', help='Camera name to import')
    parser.add_argument('--scale', type=float, default=0.01, help='Unit scale (0.01 for cm to m)')
    parser.add_argument('--geometry-only', action='store_true', help='Import geometry only')
    parser.add_argument('--camera-only', action='store_true', help='Import camera only')
    
    args = parser.parse_args(argv)
    
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    if args.camera_only:
        camera = import_dae_camera(args.dae, args.camera, args.scale)
        print(f"Camera imported: {camera.name if camera else 'None'}")
    elif args.geometry_only:
        objects = import_dae_geometry(args.dae, args.scale)
        print(f"Geometry imported: {len(objects)} objects")
    else:
        objects, camera = import_dae(args.dae, args.camera, args.scale)
        print(f"Full import: {len(objects)} objects, camera={camera.name if camera else 'None'}")


if __name__ == "__main__":
    main()
