# B1-diag: Blender GLB + Camera Diagnosis

## Problem
B1 render shows only part of scene (sink/mirror), no floor visible.

## Findings

### 1. Camera Position
| Parameter | JSON Value | Blender Value | Issue |
|-----------|------------|---------------|-------|
| eye Y | -4.44 | -4.44 | **OUTSIDE scene** (scene Y: -0.74 to 3.29) |
| Look direction | towards +Y | [0, 0, -1] = DOWN | **WRONG DIRECTION** |
| Alignment to center | expected ~1.0 | 0.035 | **Camera looks perpendicular to scene** |

### 2. Scene Bounds
```
Scene X: -0.69 to 2.55 (size: 3.2m)
Scene Y: -0.74 to 3.29 (size: 4.0m)  
Scene Z:  0.00 to 3.50 (size: 3.5m)
Scene center: (0.93, 1.27, 1.75)
```

### 3. Camera JSON Interpretation
```json
"eye": [1.1475, -4.4416, 1.948],   // Camera position (X, Y, Z)
"target": [1.1621, 5.9834, 1.5976], // Look-at point
"fov": 35.0
```

The camera is at Y=-4.44, looking towards Y=+5.98. This is **in front of the bathroom**, looking in.

### 4. Root Cause
`to_track_quat('-Z', 'Y')` is not working correctly for this case.

**Expected:** Camera at Y=-4.44, looking towards Y=+5.98 (into the room)
**Actual:** Camera looking straight DOWN (Z=-1)

### 5. Coordinate System
- SketchUp: Z-up, Y-forward
- GLB export: Z-up preserved
- Floor Z range: [0.000, 0.001] ✓ (at ground level)
- No Y-up/Z-up mismatch detected

## Fix Required

The `setup_camera()` function needs to use `look_at` properly:

```python
# Instead of to_track_quat, use look_at constraint or manual rotation
direction = Vector(target) - Vector(eye)
# Calculate rotation to align -Z with direction
rot = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot.to_euler()
```

But the issue is that Blender's track_quat might need different axis parameters for this camera orientation.

## Recommendation

Replace camera setup with explicit look-at calculation or use Blender's TrackTo constraint.
