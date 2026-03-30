# Render Workflow Governance

## 10 Core Rules

1. **Workflows are immutable source-of-truth.**
   Original workflow files must never be modified.

2. **Never substitute models or change graph semantics under "adaptation".**
   sd_xl_base ≠ RealVisXL. control-lora ≠ controlnet-sdxl.

3. **Adaptation is limited to: API conversion, path fixes, mounting, setup, execution wrappers.**
   No changes to models, prompts, weights, masks, or node order.

4. **Every execution must produce a result package.**
   Output PNG, executed workflow JSON, workflow hash, experiment.json, README/verdict.

5. **Separate "execution confirmed" from "visual equivalence confirmed".**
   Running successfully ≠ matching reference output.

6. **Cross-device visual drift disqualifies workflow as trusted baseline.**
   Such workflows remain historical artifacts only.

7. **UI workflows are reference only; API workflows are executable source.**
   Always convert UI → API before execution.

8. **No quality comparison before reproducibility status is recorded.**
   First record reproducibility status, then judge output.
   Quality comparison is allowed only after reproducibility status is explicitly documented.

9. **Environment, execution, and interpretation commits must be separate.**
   Don't mix model downloads with results with analysis.

10. **Any model/prompt/mask/order/weight change creates a new workflow candidate.**
    Document as new experiment, not as "fix" or "adaptation".

---

## Allowed vs Forbidden Adaptations

### ✅ Allowed

| Action | Example |
|--------|---------|
| UI → API conversion | `convert_workflow.py workflow.json > workflow_api.json` |
| Path mounting | `ln -s /workspace/bundle ComfyUI/input/bundle` |
| Symlinks for compatibility | `ln -s irp_bundle_s1 bundle` |
| Dependency installation | `pip install -r requirements.txt` |
| Model download (exact match) | Download `sd_xl_base_1.0.safetensors` as specified |
| Execution wrappers | Scripts to queue, monitor, collect results |
| Environment setup | ComfyUI config, CUDA settings |

### ❌ Forbidden

| Action | Why |
|--------|-----|
| Model substitution | Breaks reproducibility |
| Empty placeholder masks in normal execution | Hides missing data, invalidates results |
| Changing prompts | Creates different output |

> **Note on empty masks:** Placeholder masks are acceptable *only* as explicit debug artifacts
> with `reproducibility: debug` or `reproducibility: failed` status. They must never be used
> in normal execution or quality comparison runs.
| Adjusting weights | Changes generation |
| Reordering nodes | May affect execution |
| "Fixing" workflows | Creates undocumented variants |
| Using similar model | "Similar" ≠ identical |

---

## Required Result Package

Every workflow execution must produce:

```
results/<workflow_name>/
├── <output>.png           # Generated image(s)
├── workflow_api.json      # Exact workflow executed
├── experiment.json        # Execution metadata
└── README.md              # Verdict and notes
```

### experiment.json Schema

```json
{
  "workflow": "T1-v2",
  "workflow_file": "workflow_t1_v2_api.json",
  "workflow_hash": "sha256:abc123...",
  "timestamp": "2026-03-30T22:31:00Z",
  "gpu": "RTX 4090",
  "gpu_driver": "550.54.14",
  "pod_id": "nx3fg1y33u1b80",
  "datacenter": "EU-RO-1",
  "runtime_seconds": 131,
  "outputs": ["T1_v2_rtx4090_131s.png"],
  "models_verified": true,
  "files_verified": true,
  "reproducibility": "execution_confirmed",
  "visual_equivalence": null,
  "notes": ""
}
```

### Reproducibility Status Values

| Status | Meaning |
|--------|---------|
| `execution_confirmed` | Workflow runs without errors |
| `visual_match` | Output matches reference (human verified) |
| `visual_drift` | Output differs from reference |
| `failed` | Workflow errors during execution |
| `blocked` | Missing models/files, cannot run |

---

## Workflow Lifecycle

### Phase 1: Setup

**Goal:** Prepare environment to run workflow exactly as specified.

1. Parse workflow, extract requirements:
   - Models (checkpoints, controlnets, clip, ipadapter)
   - Input files (images, masks, references)
   - Custom nodes

2. Download missing models (exact versions):
   ```bash
   wget -P models/checkpoints/ <exact_model_url>
   ```

3. Copy/mount input files:
   ```bash
   scp -r examples/bathroom_01 pod:/workspace/irp_bundle_s1
   ln -s /workspace/irp_bundle_s1 ComfyUI/input/irp_bundle_s1
   ```

4. Verify all dependencies:
   ```bash
   python3 scripts/verify_workflow.py workflow_api.json
   ```

**Commit type:** `chore: setup environment for <workflow>`

### Phase 2: Execution

**Goal:** Run workflow and capture results.

1. Start ComfyUI
2. Convert workflow if needed (UI → API)
3. Submit to ComfyUI API
4. Monitor until completion
5. Collect outputs
6. Generate experiment.json
7. Calculate workflow hash

```bash
sha256sum workflow_api.json | cut -d' ' -f1
```

**Commit type:** `test: execute <workflow> on <gpu>`

### Phase 3: Reproducibility Check (Repro)

**Goal:** Verify workflow produces consistent results.

1. Run same workflow multiple times
2. Compare outputs (SSIM, perceptual hash)
3. Run on different hardware if available
4. Document any variance

**Commit type:** `test: reproducibility check for <workflow>`

### Phase 4: Verdict

**Goal:** Record final assessment.

1. Update experiment.json with status
2. Write README.md with:
   - Pass/fail
   - Runtime
   - Output quality notes
   - Any issues encountered

3. If visual equivalence needed:
   - Compare to reference image
   - Document differences
   - Human sign-off

**Commit type:** `docs: verdict for <workflow>`

### Phase 5: Quality Comparison (Only after repro confirmed)

**Goal:** Evaluate output quality.

1. Only proceed if `reproducibility: execution_confirmed` or better
2. Compare against baseline/reference
3. Document quality metrics
4. Flag for human review if needed

**Commit type:** `docs: quality analysis for <workflow>`

---

---

## Source-of-Truth Verification

### Before Declaring Semantic Data Unavailable

**You cannot conclude that semantic split is unavailable by checking only downstream artifacts.**

#### Verification Order (mandatory)

1. **Upstream source-of-truth** (SKP file, original scene file)
   - Check for separate objects/groups/components
   - Check material assignments
   - Check layer structure
   
2. **Export pipeline** (if SKP unavailable)
   - How was GLB/FBX generated?
   - Were semantic tags preserved or flattened?
   - Can re-export with different settings recover semantics?

3. **Intermediate artifacts** (GLB, FBX, manifest)
   - Only check these AFTER upstream is verified unavailable
   - Document WHY upstream was not checked

4. **Derived fallback**
   - Only use if upstream AND intermediate both lack semantics
   - Must document full verification chain

#### Required Documentation

When using derived fallback masks:

```json
{
  "mask_source": "derived_fallback",
  "mask_derivation": "brightness_threshold",
  "upstream_verification": {
    "skp_checked": false,
    "skp_unavailable_reason": "File not in repository, only GLB export available",
    "glb_checked": true,
    "glb_has_semantic_split": false,
    "manifest_checked": true,
    "manifest_has_semantic_split": false
  }
}
```

#### ❌ Invalid Reasoning

> "GLB has only one 'walls' node, therefore semantic split is unavailable"

This is insufficient — the SKP source may have separate objects that were merged during export.

#### ✅ Valid Reasoning

> "SKP source file not available in repository (only GLB export). GLB has one 'walls' node. 
> Re-export from SKP would require access to original file. Using brightness-derived fallback
> as interim solution. TODO: obtain SKP and re-export with semantic preservation."

---

## Quick Reference

### When Model is Missing

```bash
# ❌ WRONG
# Use RealVisXL instead of sd_xl_base

# ✅ RIGHT
wget -P models/checkpoints/ \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

### When File is Missing

```bash
# ❌ WRONG
# Create empty mask
python3 -c 'Image.new("L", (1024,1024), 0).save("mask.png")'

# ✅ RIGHT
# Find original source
scp source:/path/to/original/mask.png ./masks/
```

### When Workflow Fails

```bash
# ❌ WRONG
# "Fix" the workflow by changing models

# ✅ RIGHT
# Document failure, investigate root cause
echo "blocked: missing control-lora-canny-rank256" >> experiment.json
```
