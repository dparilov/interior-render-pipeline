#!/usr/bin/env python3
"""Extract camera data from Collada (DAE) files using pycollada."""

from collada import Collada
import numpy as np
import json
import argparse


def find_camera_nodes(node, parent_matrix=None, cameras=None):
    """Recursively find camera nodes and their accumulated matrices."""
    if cameras is None:
        cameras = []
    if parent_matrix is None:
        parent_matrix = np.eye(4)
    
    # Get this node's matrix
    if hasattr(node, 'matrix') and node.matrix is not None:
        current_matrix = parent_matrix @ node.matrix
    else:
        current_matrix = parent_matrix
    
    # Check if this node has a camera
    if hasattr(node, 'camera') and node.camera is not None:
        cam = node.camera
        cam_id = cam.id if hasattr(cam, 'id') else 'unknown'
        cameras.append({
            'camera_id': cam_id,
            'matrix': current_matrix.copy(),
            'fov': cam.yfov if hasattr(cam, 'yfov') else 35.0
        })
    
    # Process children
    if hasattr(node, 'children'):
        for child in node.children:
            find_camera_nodes(child, current_matrix, cameras)
    
    return cameras


def extract_camera(dae_path, camera_name=None, camera_index=0):
    """Extract camera from DAE file.
    
    Args:
        dae_path: Path to DAE file
        camera_name: Optional camera ID to find (e.g. "ID2" or "Сцена")
        camera_index: If no name given, use this index (0-based)
    
    Returns:
        dict with camera data for Blender
    """
    dae = Collada(dae_path)
    
    cameras = []
    for scene in dae.scenes:
        for node in scene.nodes:
            find_camera_nodes(node, cameras=cameras)
    
    if not cameras:
        raise ValueError(f"No cameras found in {dae_path}")
    
    # Find camera by name or index
    cam = None
    if camera_name:
        for c in cameras:
            if camera_name in c['camera_id']:
                cam = c
                break
        if not cam:
            print(f"Warning: Camera '{camera_name}' not found, using index {camera_index}")
    
    if cam is None:
        if camera_index >= len(cameras):
            camera_index = 0
        cam = cameras[camera_index]
    
    m = cam['matrix']
    
    # Position: convert cm to meters
    position_m = (m[:3, 3] / 100.0).tolist()
    
    # Rotation matrix (3x3)
    rot = m[:3, :3]
    
    # Forward direction: -Z column (Collada cameras look -Z)
    forward = (-rot[:, 2]).tolist()
    
    # Up direction: Y column
    up = rot[:, 1].tolist()
    
    return {
        'camera_id': cam['camera_id'],
        'dae_matrix': m.tolist(),
        'position_m': position_m,
        'rotation_3x3': rot.tolist(),
        'forward': forward,
        'up': up,
        'fov_deg': cam['fov']
    }


def main():
    parser = argparse.ArgumentParser(description='Extract camera from DAE file')
    parser.add_argument('dae_path', help='Path to DAE file')
    parser.add_argument('--camera', '-c', help='Camera ID to find')
    parser.add_argument('--index', '-i', type=int, default=0, help='Camera index')
    parser.add_argument('--output', '-o', help='Output JSON file')
    args = parser.parse_args()
    
    result = extract_camera(args.dae_path, args.camera, args.index)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
