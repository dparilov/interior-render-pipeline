# Camera Transform — SketchUp → Blender

## Canonical Formula

SketchUp exports camera in DAE with:
- Position in **inches**, Z-up coordinate system
- 4x4 transformation matrix

Blender GLB import uses **Z-up** (same as SketchUp).

### Step 1: Read from manifest.json

```python
import json

with open('manifest.json') as f:
    m = json.load(f)

# Position already in meters (irp.rb converts)
eye = m['camera']['eye']      # [x, y, z] meters
target = m['camera']['target'] # [x, y, z] meters
fov = m['camera']['fov']       # degrees
```

### Step 2: Apply in Blender

```python
import bpy
import math

camera = bpy.data.objects['Camera']

# Position: use directly (both Z-up)
camera.location = (eye[0], eye[1], eye[2])

# Rotation: 90° around X to look along +Y
camera.rotation_mode = 'XYZ'
camera.rotation_euler = (math.radians(90), 0.0, 0.0)

# FOV
camera.data.angle = math.radians(fov)
```

### Why 90° Rotation?

- Blender camera default: looks along **-Z**
- SketchUp camera: looks along **+Y** (into room)
- Rotate 90° around X: -Z becomes +Y ✓

---

## Verified Values (bathroom_04)

```python
# From DAE matrix decomposition
POSITION = (1.147482, -4.441579, 1.947995)  # meters
ROTATION = (math.radians(90), 0.0, 0.0)     # radians
FOV = 35.0                                   # degrees
```

**Result:** Camera outside room at Y=-4.44m, looking through door into bathroom.

---

## Known Issues

### Clipping Plane Not Exported

SketchUp viewport clipping ("ползунок") hides geometry in front of camera. This is **NOT** exported to DAE/GLB.

**Workaround:** Manually hide front-facing geometry in SketchUp before export.

---

## Reference

- B21 commit: `7ed7a45`
- B26 commit: `24baa12` (exact copy, verified)
- Script: `scripts/b21_dae_matrix_render.py`
