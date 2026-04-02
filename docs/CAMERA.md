# Camera Transform — SketchUp to Blender

## The Problem

SketchUp DAE exports camera position and rotation matrix.
Blender GLB uses different coordinate conventions.
Getting the camera right is critical for matching beauty.png.

## Solution (Phase B Finding)

**Don't use complex matrix transforms.** Use DAE position as-is with fixed rotation.

### Working Formula

```python
import math

# From manifest.json camera.eye (already in meters)
dae_eye = [1.147, -4.442, 1.948]

# Position: use as-is
camera.location = (dae_eye[0], dae_eye[1], dae_eye[2])

# Rotation: 90° around X axis (camera looks +Y direction)
camera.rotation_mode = 'XYZ'
camera.rotation_euler = (math.radians(90), 0, 0)

# FOV from manifest
camera.data.angle = math.radians(35.0)
```

### Why This Works

1. Both SketchUp GLB and Blender use **Z-up** coordinate system
2. Camera Y=-4.44 places it **outside** the room (in front of entrance)
3. 90° X rotation makes camera look **+Y** (into the room)

### What Doesn't Work

❌ Transform `(x, z, -y)` — puts camera outside scene bounds
❌ Using DAE rotation matrix directly — axis conventions differ
❌ Track-to constraint with DAE target — target coordinates also wrong

## Coordinate Systems

| System | X | Y | Z |
|--------|---|---|---|
| SketchUp | Right | Forward | Up |
| Blender | Right | Forward | Up |
| GLB | Right | Forward | Up |

All are Z-up! The issue is **camera facing direction**, not coordinates.

## Scene Bounds Check

Always verify camera is near the scene:

```python
# Scene bounds for bathroom_04
Y: [-0.74, 3.29]
Z: [0, 3.50]

# Camera at Y=-4.44 is OUTSIDE (correct - in front of door)
# Camera at Z=1.95 is INSIDE bounds (correct - eye height)
```

## Known Issues

1. **Narrow FOV**: DAE FOV=35° shows limited view through doorway
2. **Front wall blocking**: Need to hide front wall for wider interior view
3. **Mirror reflection**: Renders black without proper material setup
