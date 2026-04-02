# End-to-End Workflow

## Phase 1: SketchUp Preparation

### 1.1 Setup Scene
```
1. Open model in SketchUp
2. Create/select Scene (camera angle)
3. Verify front wall is hidden OR camera inside room
4. Check layer visibility for desired view
```

### 1.2 Create role_map.json
```json
{
  "36696": {"name": "walls", "role": "surface.walls"},
  "36828": {"name": "floor", "role": "surface.floor"},
  "43754": {"name": "bathtub", "role": "fixture.bathtub"}
}
```

### 1.3 Export Bundle
```ruby
load 'irp.rb'
IRP.export
# Output: irp_bundle.zip
```

### 1.4 Verify Export
```
- beauty.png matches expected view
- manifest.json has correct camera values
- model.glb contains all geometry
```

## Phase 2: Blender Render

### 2.1 Import Model
```bash
blender --background --python scripts/render_canonical.py -- \
    --bundle path/to/bundle/ \
    --output render.png
```

### 2.2 Manual Adjustments (if needed)
```python
# Wider FOV for interior view
camera.data.angle = math.radians(70)

# Move camera inside room
camera.location = (0.93, 0.0, 1.6)
```

### 2.3 Material Setup
```python
# Apply textures from references/
# Setup floor/wall materials
# Configure mirror reflection
```

## Phase 3: ComfyUI Render (TODO)

### 3.1 Prepare Workflow
```
- Load workflow JSON
- Set input images (beauty, depth, masks)
- Configure prompts from manifest
```

### 3.2 Execute Render
```bash
python scripts/pod_render.sh <pod_ip> <pod_port> --bundle path/
```

## File Flow

```
SketchUp (.skp)
    ↓ IRP.export
irp_bundle.zip
    ├── manifest.json
    ├── beauty.png
    ├── depth.png
    ├── model.glb
    ├── model.dae
    └── masks/*.png
    ↓ Blender
render.png (test)
    ↓ ComfyUI
final_render.png
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Gray render | Check camera position vs scene bounds |
| Black mirrors | Add reflection material |
| Missing geometry | Verify GLB import, check hidden layers |
| Wrong textures | Adjust texture_scale in materials |
