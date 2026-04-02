# SketchUp Export Preflight Checklist

## Before Running IRP.export

### Scene Setup
- [ ] Correct Scene selected (camera angle matches desired view)
- [ ] Camera positioned correctly (inside room OR outside with front wall hidden)
- [ ] FOV appropriate for view (35° narrow, 60-70° wide interior)

### Visibility
- [ ] Front wall hidden (layer OFF) OR camera inside room
- [ ] All fixtures visible that should appear in render
- [ ] No unwanted objects in view (scale figures, construction geometry)
- [ ] Section Planes OFF or correctly positioned

### Entity Mapping
- [ ] role_map.json exists in model directory
- [ ] All important entities have PID mappings
- [ ] Names are valid (no special characters)
- [ ] Roles follow convention: `surface.*`, `fixture.*`, `opening.*`

### References
- [ ] Reference images in references/ folder
- [ ] Prompts in role_map.json match references
- [ ] Technical spec (ТЗ.md) present if available

### Plugin
- [ ] irp.rb loaded (latest version)
- [ ] No Ruby console errors

## After Export

### Quick Checks
- [ ] irp_bundle.zip created
- [ ] File size reasonable (>1MB for typical bathroom)

### beauty.png
- [ ] Shows expected camera view
- [ ] All visible entities rendered
- [ ] No clipping artifacts
- [ ] Resolution correct (1920x1080)

### manifest.json
- [ ] camera.eye values reasonable (within or near scene bounds)
- [ ] camera.fov matches SketchUp scene
- [ ] visibility.hidden_pids empty OR contains only intended hidden items
- [ ] entities list complete

### model.glb
- [ ] Opens in Blender without errors
- [ ] Geometry matches beauty.png view
- [ ] Entity names present (IRP_*, HIDDEN_*)

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Wrong scene selected | Camera in wrong position | Select correct scene before export |
| Front wall visible | Narrow doorway view | Hide front wall layer |
| Missing role_map | Empty entities in manifest | Create role_map.json |
| Old irp.rb version | Missing features | Reload latest irp.rb |
| Section plane active | Geometry cut | Deactivate section planes |
