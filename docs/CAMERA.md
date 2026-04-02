# Camera Pipeline: SketchUp → Blender

## Coordinate Transform

- **DAE**: inches, Z-up
- **GLB**: meters, Y-up
- **Formula**: `glb_pos = (dae_x * 0.0254, dae_z * 0.0254, -dae_y * 0.0254)`

## FOV Conversion

SketchUp `fov_is_height? = true` → vertical FOV

### Formula for portrait aspect (< 1):

```python
fov_adjusted = fov_sketchup / aspect
```

**Example:**
- SketchUp FOV: 35°
- Viewport: 1066 x 1239 (aspect = 0.86)
- Blender FOV: 35 / 0.86 = **40.7°**

### Formula for landscape aspect (> 1):

```python
# Convert vertical to horizontal
hfov = 2 * atan(tan(vfov/2) * aspect)
```

## Resolution

Use exact viewport dimensions from SketchUp:

```python
scene.render.resolution_x = manifest['viewport']['width']
scene.render.resolution_y = manifest['viewport']['height']
scene.render.resolution_percentage = 100  # No scaling!
```

## Camera Offset (Wall Thickness)

Section plane clips at inner wall face. To see fixtures at outer wall:

```python
wall_thickness = section_plane_y - walls_outer_y
camera.location.y -= wall_thickness
```

## Clip Start

Apply section plane as near clip:

```python
clip_start = abs(camera_y_adjusted - section_plane_y)
camera.data.clip_start = clip_start
```

## Complete Pipeline

```python
# 1. Load manifest
manifest = json.load('manifest.json')

# 2. Camera position
eye = manifest['camera']['eye']
camera.location = (eye[0], eye[1], eye[2])

# 3. Camera rotation (look +Y)
camera.rotation_euler = (radians(90), 0, 0)

# 4. FOV adjustment
aspect = manifest['viewport']['width'] / manifest['viewport']['height']
fov_adjusted = manifest['camera']['fov'] / aspect
camera.data.angle = radians(fov_adjusted)

# 5. Wall offset
wall_geo = manifest['wall_geometry']
camera.location.y -= wall_geo['wall_thickness']

# 6. Clip start
clip_start = abs(camera.location.y - wall_geo['section_plane_y'])
camera.data.clip_start = clip_start

# 7. Render resolution
scene.render.resolution_x = manifest['viewport']['width']
scene.render.resolution_y = manifest['viewport']['height']
```

## Manifest Fields

```json
{
  "camera": {
    "eye": [1.147, -4.442, 1.948],
    "fov": 35.0
  },
  "viewport": {
    "width": 1066,
    "height": 1239,
    "aspect": 0.86
  },
  "wall_geometry": {
    "section_plane_y": 1.3,
    "walls_outer_y": 1.143,
    "wall_thickness": 0.157
  },
  "section_planes": [{
    "normal": [0, 1, 0],
    "distance_meters": -1.3
  }]
}
```
