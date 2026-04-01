# B2 Comparison: UV Methods

## Results

| Method | Floor Texture | Wall Texture | Notes |
|--------|---------------|--------------|-------|
| B2a Generated | ❌ Not visible | ❌ Not visible | Gray surfaces |
| B2b Box | ❌ Not visible | ❌ Not visible | Gray surfaces |
| B2c Auto | ❌ Not visible | ❌ Not visible | Gray surfaces |

## Camera Fix: ✅ SUCCESS
- Camera now correctly points at scene (dot=1.000)
- View shows vanity, mirror, walls as expected

## Texture Issue: UNRESOLVED

### Possible Causes:
1. **Wrong meshes assigned** — IRP_walls child meshes may not be the visible wall geometry
2. **Material slot issue** — Meshes may have multiple material slots
3. **Texture coordinates scale** — Generated/Box coords may be outside texture bounds
4. **Shader node connections** — Need to verify node tree

### Evidence:
- Material assignment reports: floor=1, wall=5 meshes
- But visible walls appear gray (default material)
- The 5 wall meshes may be different from visible geometry

## Recommendation
Need to:
1. Audit which meshes are actually VISIBLE in camera view
2. Check if visible meshes have IRP_ naming or are separate
3. Verify texture is actually loaded and connected

## Partial Success
- ✅ Camera orientation fixed (Track To constraint)
- ✅ Script runs without errors
- ✅ All 3 UV methods work (no crashes)
- ❌ Textures not appearing on geometry
