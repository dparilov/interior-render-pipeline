# Experiment Tracking

> Full reproducibility for every render

## Why Track Experiments

Without tracking:
- "Which seed gave that good result?"
- "What ControlNet strength did I use?"
- "Was that before or after I changed the negative prompt?"

With tracking:
- Every render is logged with full parameters
- Compare any two experiments
- Reproduce any previous result exactly

## Structure

```
experiments/
├── exp_20260329_123456/
│   ├── experiment.json    # Metadata + params
│   ├── workflow.json      # Exact workflow used
│   ├── bundle_manifest.json  # Input bundle state
│   └── render.png         # Output image
├── exp_20260329_124512/
│   └── ...
```

## experiment.json Schema

```json
{
  "id": "exp_20260329_123456",
  "timestamp": "2026-03-29T12:34:56",
  "bundle": "/path/to/irp_bundle",
  "status": "completed",
  
  "params": {
    "seed": 42,
    "canny_strength": 0.8,
    "depth_strength": 0.9,
    "steps": 50
  },
  
  "workflow_hash": "a1b2c3d4",
  "prompt_id": "uuid-from-comfyui",
  
  "timing": {
    "start": "2026-03-29T12:34:56",
    "end": "2026-03-29T14:02:30",
    "duration_seconds": 5254,
    "duration_human": "1h 27m 34s"
  },
  
  "notes": "First test with SketchUp depth"
}
```

## Usage

### Automatic Tracking

```bash
python render/render.py /path/to/bundle
# Creates experiment automatically

python render/render.py /path/to/bundle --no-track
# Disable tracking for quick tests
```

### List Experiments

```bash
python render/experiment.py list --dir /path/to/experiments

# Output:
# ID                        Status       Duration        Workflow
# -----------------------------------------------------------------
# exp_20260329_140230       completed    1h 27m 34s      a1b2c3d4
# exp_20260329_123456       completed    1h 25m 12s      a1b2c3d4
# exp_20260329_110000       failed       -               b5c6d7e8
```

### Compare Experiments

```bash
python render/experiment.py compare --dir /path/to/experiments \
  exp_20260329_123456 exp_20260329_140230

# Output:
# {
#   "exp1": "exp_20260329_123456",
#   "exp2": "exp_20260329_140230",
#   "workflow_same": true,
#   "params_diff": {
#     "seed": {"exp1": 42, "exp2": 123}
#   }
# }
```

## Integration with render.py

```python
from experiment import create_experiment

# Create experiment
exp = create_experiment(bundle_path)

# Log parameters
exp.log_params({
    "seed": 42,
    "canny_strength": 0.8,
    "depth_strength": 0.9
})

# Log workflow
exp.log_workflow(workflow_dict)

# After render completes
exp.log_output(Path("output/render.png"))
exp.log_timing(start_time, end_time)
exp.complete(notes="Good result, keep this seed")
```

## Best Practices

1. **Always track** production renders
2. **Add notes** when you find good results
3. **Compare** when debugging issues
4. **Clean up** old failed experiments periodically
