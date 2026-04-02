# Phase B Summary — Blender Pipeline

**Status:** CAMERA WORKING ✅ | FRONT WALL BLOCKING ⚠️
**Date:** 2026-04-02
**Commits:** B1-B27 (27 experiments)

---

## ✅ SOLVED

### 1. Camera Transform (DAE → Blender)

**Canonical approach (B21/B26):**
```python
# Read from manifest.json camera.eye (meters, SketchUp Z-up)
# Use directly in Blender (also Z-up for GLB import)

POSITION = (1.147482, -4.441579, 1.947995)  # (x, y, z) from DAE
ROTATION = (math.radians(90), 0.0, 0.0)     # 90° X = look along +Y
FOV = 35.0                                   # from DAE <yfov>

camera.location = POSITION
camera.rotation_mode = 'XYZ'
camera.rotation_euler = ROTATION
camera.data.angle = math.radians(FOV)
```

**Key insight:** SketchUp DAE and Blender GLB both use Z-up. No axis swap needed. Just apply position directly and rotate 90° around X to look forward (+Y).

### 2. Visibility System (B18)

**Working:** `irp.rb` correctly exports:
- `visibility.global.hidden_pids` — entities with `entity.hidden? = true`
- `visibility.scene.hidden_pids` — entities on hidden layers for current scene
- `visibility.scene.hidden_layers` — layer names

**Logic:**
```ruby
LAYER_HIDDEN_BY_DEFAULT = 0x0001

def layer_visible_in_scene?(layer, page)
  in_page_layers = page.layers.include?(layer)
  default_hidden = (layer.page_behavior & LAYER_HIDDEN_BY_DEFAULT) != 0
  
  if in_page_layers
    return default_hidden  # XOR: opposite of default
  else
    return !default_hidden  # Use default
  end
end
```

### 3. Entity Naming

```
IRP_{name}         — Mapped entities (walls, floor, bathtub...)
HIDDEN_S_{pid}     — Scene-hidden entities
HIDDEN_G_{pid}     — Global-hidden entities
EXCLUDED_{name}    — Excluded entities
```

### 4. Tile Scaling

Tile UV scale = 5.0 works for quatrefoil pattern visibility.

---

## ⚠️ BLOCKING ISSUE

### Front Wall / Clipping Plane

**Problem:** SketchUp uses viewport clipping ("ползунок") to hide front wall. This is NOT exported to DAE/GLB.

**Symptoms:**
- Camera at Y=-4.44 (outside room)
- Looking through door opening
- Front wall geometry blocks wider view
- `IRP_walls` is single mesh — can't hide selectively

**Attempted solutions (failed):**
- B22-B27: Delete faces by Y/Z coordinate — doesn't isolate front wall
- Face normals — mixed results
- Object hiding — `IRP_walls` is one object

**Possible solutions:**
1. **SketchUp:** Manually hide front wall faces before export (break group, hide, update scene)
2. **SketchUp:** Use Section Plane (exports to DAE?)
3. **Ruby:** Detect clipping plane distance and export
4. **Blender:** Camera near-clip plane to match SketchUp

---

## 📁 Canonical Files

### Bundles
- `examples/bathroom_04/` — Latest with B18 visibility fix
- `examples/bathroom_01/` — Original (no visibility data)

### Scripts (Working)
- `scripts/b21_dae_matrix_render.py` — **CANONICAL** camera setup
- `scripts/b26_exact_copy.py` — Copy of B21

### Scripts (Diagnostic/Failed)
- B19, B20, B22-B25, B27 — Various camera/wall experiments

### irp.rb
- **Version:** 1.1
- **Yandex:** https://yadi.sk/d/lUplRGTb_uydGQ
- **Features:** scene visibility, entity naming, coordinate transform

---

## 📋 Cleanup TODO

- [ ] Delete diagnostic scripts (B19, B20, B22-B25, B27)
- [ ] Keep only B21 as canonical render script
- [ ] Update CAMERA.md with final transform formula
- [ ] Document clipping plane issue
- [ ] Add pre-flight checklist for SketchUp export

---

## 🎯 Next Steps

1. **Research:** SketchUp Ruby API for clipping plane / near clip distance
2. **Alternative:** Camera inside room (requires different scene setup in SketchUp)
3. **Workaround:** Manual front wall hiding in SketchUp before export
