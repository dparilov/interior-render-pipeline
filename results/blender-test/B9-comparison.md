# B9 Camera Comparison

## Reference: beauty.png
- Frontal view of bathroom
- Floor with blue geometric tiles visible from edge to edge
- Sink centered with mirror above
- Tub on right (blue)
- Basket on left
- Wide FOV, standing at doorway

## B9a: Wider FOV (65°)
- Same camera position from JSON (eye=[1.15, -4.44, 1.95])
- FOV increased from 35° to 65°
- **Result:** Still too far/outside, sees external walls
- Floor barely visible

## B9b: Manual Camera
- Position: (0.9, -0.5, 2.0) - at entrance, looking in
- Target: (0.9, 1.5, 0.5) - floor level
- FOV: 55°
- **Result:** Floor with blue stripes clearly visible!
- Shows entire floor area
- Wall texture visible

## Acceptance Check
| Criterion | B9a | B9b |
|-----------|-----|-----|
| Floor visible | Partial | ✅ YES |
| Walls visible | ✅ YES | ✅ YES |
| Composition like ref | ❌ NO | ✅ Closer |

## Conclusion
B9b manual camera better matches reference intent.
Original JSON camera is positioned OUTSIDE the room.
