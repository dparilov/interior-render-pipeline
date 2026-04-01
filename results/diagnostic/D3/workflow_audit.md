# Workflow Graph Audit (D3)

## Node Inventory

### CLIPTextEncode
- positive
- negative

### CLIPVisionLoader
- clip_vision

### Canny
- canny_preprocess

### CheckpointLoaderSimple
- checkpoint

### ControlNetApplyAdvanced
- apply_controlnet_canny

### ControlNetLoader
- controlnet_canny

### EmptyLatentImage
- empty_latent

### IPAdapterAdvanced
- entity_0_floor_apply
- entity_1_walls_tile_apply

### IPAdapterModelLoader
- ipadapter_model

### KSampler
- sampler

### LoadImage
- load_beauty
- entity_0_floor_ref
- entity_1_walls_tile_ref
- load_boundary_image

### LoadImageMask
- load_boundary
- entity_0_floor_mask
- entity_1_walls_tile_mask

### SaveImage
- save_image

### SetLatentNoiseMask
- set_latent_mask

### VAEDecode
- vae_decode

## Critical Connections Check

### 1. IPAdapter → Model Chain

**entity_0_floor_apply**:
- model input: ['checkpoint', 0]
- ipadapter input: ['ipadapter_model', 0]
- image (reference): ['entity_0_floor_ref', 0]
- attn_mask: ['entity_0_floor_mask', 0]
- weight: 0.55
- end_at: 1.0

**entity_1_walls_tile_apply**:
- model input: ['entity_0_floor_apply', 0]
- ipadapter input: ['ipadapter_model', 0]
- image (reference): ['entity_1_walls_tile_ref', 0]
- attn_mask: ['entity_1_walls_tile_mask', 0]
- weight: 0.55
- end_at: 1.0

### 2. Reference Images Loading
- entity_0_floor_ref: bathroom_01_surface_only/references/floor_tiles.jpg
- entity_1_walls_tile_ref: bathroom_01_surface_only/references/wall_tiles.png

### 3. Masks Loading
- load_boundary: bathroom_01_surface_only/boundary_mask.png
- entity_0_floor_mask: bathroom_01_surface_only/masks/floor.png
- entity_1_walls_tile_mask: bathroom_01_surface_only/masks/walls_tile.png

### 4. ControlNet Chain
- controlnet_canny (ControlNetLoader): strength=N/A
- apply_controlnet_canny (ControlNetApplyAdvanced): strength=0.8

### 5. Sampler Connections
- positive: ['apply_controlnet_canny', 0]
- negative: ['apply_controlnet_canny', 1]
- latent_image: ['set_latent_mask', 0]
- model: ['entity_1_walls_tile_apply', 0]

## Diagnosis

### Issue Found:
The IPAdapter nodes receive their `model` input from the PREVIOUS IPAdapter node
(entity_0 → entity_1 chain), which is correct.

BUT: The final IPAdapter output goes to... **nothing that connects to sampler!**

The sampler gets its conditioning from ControlNet, NOT from IPAdapter model output.

### Correct Flow Should Be:
1. checkpoint.model → ipadapter_0.model
2. ipadapter_0.model_out → ipadapter_1.model  
3. ipadapter_1.model_out → **sampler.model** (or via ControlNet)

### Current (Broken?) Flow:
- sampler.positive ← apply_controlnet_canny
- sampler.model ← ??? (need to check)


**Sampler model input:** ['entity_1_walls_tile_apply', 0]
Model comes from: entity_1_walls_tile_apply
Source node class: IPAdapterAdvanced
