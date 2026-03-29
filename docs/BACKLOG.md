# IRP Backlog

## Epic 1: Multi-View Camera Automation

### Goal

Автоматическое создание камер и multi-view рендеринг из одной 3D сцены.

### Architecture

```
Scene (GLB/FBX)
    │
    ├── Camera Generator
    │   ├── Auto-placement (room corners, center, etc.)
    │   ├── Named camera import from model
    │   └── External camera config (JSON)
    │
    └── Multi-View Renderer
        ├── Per-camera beauty/depth/masks
        ├── Consistent entity naming across views
        └── Combined manifest with view index
```

### Levels

| Level | Scope | Deliverable |
|-------|-------|-------------|
| 0 | Single camera (current) | ✅ Done |
| 1 | Named cameras from model | Import existing cameras |
| 2 | Auto-placement | Corner + center cameras |
| 3 | Full automation | Config-driven multi-view |

### Tasks

#### Level 1: Named Cameras

- [ ] C1-1: Parse camera objects from GLB/FBX
- [ ] C1-2: Iterate cameras and render per-camera outputs
- [ ] C1-3: Output structure: `views/<camera_name>/beauty.png`
- [ ] C1-4: Manifest includes `views[]` array

#### Level 2: Auto-placement

- [ ] C2-1: Bounding box calculation for scene
- [ ] C2-2: Corner camera positions (4 corners + center)
- [ ] C2-3: Auto look-at center of scene
- [ ] C2-4: Configurable FOV and height

#### Level 3: Full Automation

- [ ] C3-1: Camera config JSON schema
- [ ] C3-2: Custom camera positions/rotations
- [ ] C3-3: Per-camera render settings override
- [ ] C3-4: Batch CLI: `--views all` or `--views config.json`

### Experiments

| ID | Test | Purpose |
|----|------|---------|
| C0 | Current single camera | Baseline |
| C1 | 4-corner auto cameras | Coverage test |
| C2 | Named cameras from model | Import test |
| C3 | Config-driven custom views | Flexibility test |

### Acceptance Criteria

- [ ] All views share same entity masks (by name)
- [ ] Manifest links views to shared entities
- [ ] workflow_builder accepts multi-view bundles
- [ ] Renderer produces one output per view

---

## Epic 2: Blender-First Pipeline

### Goal

Постепенный переход от SketchUp к Blender как primary bundle generator.

### Strategy

**⚠️ НЕ убивать SketchUp сразу.**

1. Достичь измеримой parity с SketchUp path
2. Документировать gaps и workarounds
3. Переключаться только после validated parity

### Levels

| Level | Scope | SketchUp Status |
|-------|-------|-----------------|
| 0 | Fallback only (current) | Primary |
| 1 | Parity achieved | Equivalent |
| 2 | Blender preferred | Deprecated |
| 3 | Blender only | Removed |

### Tasks

#### Level 1: Parity

- [ ] BF1-1: Side-by-side comparison (same scene)
- [ ] BF1-2: Mask alignment validation
- [ ] BF1-3: Depth map comparison
- [ ] BF1-4: Entity coverage parity (100%)
- [ ] BF1-5: Render quality comparison (visual)
- [ ] BF1-6: Document remaining gaps

#### Level 2: Preference

- [ ] BF2-1: Default to Blender in CI/CD
- [ ] BF2-2: SketchUp as manual fallback only
- [ ] BF2-3: Migration guide for existing projects
- [ ] BF2-4: Remove SketchUp from required tools

#### Level 3: Removal

- [ ] BF3-1: Archive SketchUp scripts
- [ ] BF3-2: Update all documentation
- [ ] BF3-3: Remove SketchUp from ARCHITECTURE.md
- [ ] BF3-4: Final cleanup

### Parity Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Entity detection | 100% | ~90% |
| Mask accuracy | 95%+ | Unknown |
| Depth quality | Comparable | Different (normalized) |
| Reference support | Automatic | Manual |
| Tech spec export | Automatic | Manual |
| Camera scenes | Multiple | Single |

### Experiments

| ID | Test | Purpose |
|----|------|---------|
| BF0 | Current Blender flow | Baseline |
| BF1 | Same scene comparison | Measure gaps |
| BF2 | Full pipeline run | End-to-end validation |
| BF3 | Production render | Quality check |

### Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing workflows | Keep SketchUp until Level 1 complete |
| Quality regression | Side-by-side comparison before switch |
| Entity naming differences | Strict IRP_ convention |
| Depth interpretation | Document both modes |

### Acceptance Criteria (Level 1 → Level 2)

- [ ] B4 parity test passes
- [ ] All entity masks align within 5% IoU
- [ ] Pipeline produces equivalent renders
- [ ] No manual intervention for standard scenes
- [ ] Documentation complete

---

## Priority

| Epic | Priority | Reason |
|------|----------|--------|
| Epic 2 Level 1 | HIGH | Enables CI/CD, reduces toolchain |
| Epic 1 Level 1 | MEDIUM | Nice-to-have for coverage |
| Epic 2 Level 2 | MEDIUM | After parity proven |
| Epic 1 Level 2-3 | LOW | Future automation |
| Epic 2 Level 3 | LOW | Only after full migration |

## Recommended Order

1. **BF1-1 → BF1-6**: Achieve and document parity
2. **Block B tests**: Validate Blender flow
3. **C1-1 → C1-4**: Named camera support
4. **BF2-***: Switch default to Blender
5. **C2-*, C3-***: Full camera automation
