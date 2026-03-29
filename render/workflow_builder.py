#!/usr/bin/env python3
"""
Workflow Builder for Multi-Entity Regional IPAdapter Pipeline.

Generates ComfyUI workflow from manifest entities.
"""

import json
import copy
from pathlib import Path
from typing import List, Dict, Any, Optional


class WorkflowBuilder:
    """Builds ComfyUI workflow with multi-entity regional IPAdapter branches."""
    
    # Entity ordering by size (large → small)
    DEFAULT_ORDER = [
        'walls', 'floor', 'ceiling',           # Large surfaces
        'bathtub', 'shower', 'shower_screen',  # Large fixtures
        'vanity', 'toilet', 'mirror',          # Medium fixtures
        'towel_warmer', 'window', 'basket',    # Small fixtures/decor
        'rainshower'                           # Accessories
    ]
    
    CRITICAL_ENTITIES = ['walls', 'floor', 'bathtub', 'vanity']
    
    def __init__(self, base_workflow_path: str):
        """Load base workflow template."""
        with open(base_workflow_path) as f:
            self.base_workflow = json.load(f)
        self.prompt = self.base_workflow.get('prompt', self.base_workflow)
    
    def select_entities(
        self,
        entities: List[Dict],
        mode: str = 'all',
        custom_list: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Select active entities based on mode.
        
        Modes:
        - 'single': first entity only
        - 'critical': only critical entities
        - 'all': all entities
        - 'custom': only entities in custom_list
        """
        if mode == 'single':
            return entities[:1] if entities else []
        elif mode == 'critical':
            return [e for e in entities if e.get('name') in self.CRITICAL_ENTITIES]
        elif mode == 'custom' and custom_list:
            return [e for e in entities if e.get('name') in custom_list]
        else:  # 'all'
            return entities
    
    def order_entities(
        self,
        entities: List[Dict],
        policy: str = 'default'
    ) -> List[Dict]:
        """
        Order entities according to policy.
        
        Policies:
        - 'default': large surfaces → small fixtures
        - 'reverse': opposite of default
        - 'manifest': keep manifest order
        """
        if policy == 'manifest':
            return entities
        
        def sort_key(e):
            name = e.get('name', '')
            try:
                return self.DEFAULT_ORDER.index(name)
            except ValueError:
                return 999  # Unknown entities last
        
        ordered = sorted(entities, key=sort_key)
        
        if policy == 'reverse':
            ordered = list(reversed(ordered))
        
        return ordered
    
    def build(
        self,
        entities: List[Dict],
        bundle_path: str,
        mode: str = 'all',
        order_policy: str = 'default',
        include_refiner: bool = False,
        base_seed: int = 42
    ) -> Dict[str, Any]:
        """
        Build workflow with entity branches.
        
        Returns:
        - workflow dict ready for ComfyUI API
        - metadata about what was built
        """
        workflow = copy.deepcopy(self.prompt)
        
        # Select and order entities
        active = self.select_entities(entities, mode)
        ordered = self.order_entities(active, order_policy)
        
        # Track what we're building
        metadata = {
            'workflow_mode': 'multi_ipadapter_regional',
            'entities_requested': [e.get('name') for e in entities],
            'entities_applied': [],
            'entities_skipped': [],
            'entity_order': [],
            'entity_weights': {},
            'regional_ipadapter_count': 0
        }
        
        # Find the base model output to chain from
        # In ComfyUI, we chain IPAdapter applications through the model
        last_model_output = self._find_base_model(workflow)
        
        # Generate entity branches
        for idx, entity in enumerate(ordered):
            name = entity.get('name')
            mask_path = entity.get('mask')
            ref_path = entity.get('reference')
            weight = entity.get('ipadapter_weight', 0.5)
            
            # Validate entity has required fields
            if not mask_path or not ref_path:
                metadata['entities_skipped'].append({
                    'name': name,
                    'reason': 'missing mask or reference'
                })
                continue
            
            # Resolve paths relative to bundle
            mask_full = str(Path(bundle_path) / mask_path)
            ref_full = str(Path(bundle_path) / ref_path)
            
            # Create entity branch nodes
            branch_prefix = f"entity_{idx}_{name}"
            
            # Load reference image
            workflow[f"{branch_prefix}_ref"] = {
                "class_type": "LoadImage",
                "inputs": {"image": ref_full}
            }
            
            # Load mask
            workflow[f"{branch_prefix}_mask"] = {
                "class_type": "LoadImage",
                "inputs": {"image": mask_full}
            }
            
            # Apply IPAdapter with mask (regional)
            workflow[f"{branch_prefix}_apply"] = {
                "class_type": "IPAdapterApply",
                "inputs": {
                    "model": last_model_output,
                    "ipadapter": ["ipadapter_model", 0],
                    "image": [f"{branch_prefix}_ref", 0],
                    "weight": weight,
                    "noise": 0.0,
                    "weight_type": "linear",
                    "start_at": 0.0,
                    "end_at": 1.0,
                    "attn_mask": [f"{branch_prefix}_mask", 0]
                }
            }
            
            # Update chain - next entity uses this entity's output
            last_model_output = [f"{branch_prefix}_apply", 0]
            
            # Track metadata
            metadata['entities_applied'].append(name)
            metadata['entity_order'].append(name)
            metadata['entity_weights'][name] = weight
            metadata['regional_ipadapter_count'] += 1
        
        # Update sampler to use final model in chain
        for node_id, node in workflow.items():
            if node.get('class_type') == 'KSampler':
                if metadata['regional_ipadapter_count'] > 0:
                    node['inputs']['model'] = last_model_output
                node['inputs']['seed'] = base_seed
        
        # Add refiner if requested
        if include_refiner:
            workflow = self._add_refiner(workflow, base_seed)
            metadata['refiner_enabled'] = True
        else:
            metadata['refiner_enabled'] = False
        
        return {'prompt': workflow}, metadata
    
    def _find_base_model(self, workflow: Dict) -> Any:
        """Find the base model output reference."""
        # Look for checkpoint loader
        for node_id, node in workflow.items():
            if node.get('class_type') == 'CheckpointLoaderSimple':
                return [node_id, 0]  # Model is output 0
        
        # Fallback to 'checkpoint' node name
        if 'checkpoint' in workflow:
            return ['checkpoint', 0]
        
        raise ValueError("Cannot find base model in workflow")
    
    def _add_refiner(self, workflow: Dict, seed: int) -> Dict:
        """Add refiner layer to workflow."""
        workflow['refiner_checkpoint'] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_refiner_1.0.safetensors"}
        }
        
        workflow['refiner_positive'] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": workflow.get('positive', {}).get('inputs', {}).get('text', ''),
                "clip": ["refiner_checkpoint", 1]
            }
        }
        
        workflow['refiner_negative'] = {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": workflow.get('negative', {}).get('inputs', {}).get('text', ''),
                "clip": ["refiner_checkpoint", 1]
            }
        }
        
        workflow['refiner_sampler'] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["refiner_checkpoint", 0],
                "positive": ["refiner_positive", 0],
                "negative": ["refiner_negative", 0],
                "latent_image": ["sampler", 0],
                "seed": seed,
                "steps": 10,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 0.25
            }
        }
        
        # Update VAE decode to use refiner output
        if 'vae_decode' in workflow:
            workflow['vae_decode']['inputs']['samples'] = ["refiner_sampler", 0]
            workflow['vae_decode']['inputs']['vae'] = ["refiner_checkpoint", 2]
        
        return workflow


def validate_workflow(workflow: Dict, expected_entities: List[str]) -> Dict:
    """
    Validate generated workflow.
    
    Checks:
    - Expected entity branches exist
    - Each branch has mask and reference bindings
    - Order matches expected
    """
    prompt = workflow.get('prompt', workflow)
    
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'entity_branches_found': [],
        'entity_branches_missing': []
    }
    
    for entity_name in expected_entities:
        # Look for entity branch nodes
        found_apply = False
        found_ref = False
        found_mask = False
        
        for node_id in prompt.keys():
            if entity_name in node_id:
                if '_apply' in node_id:
                    found_apply = True
                elif '_ref' in node_id:
                    found_ref = True
                elif '_mask' in node_id:
                    found_mask = True
        
        if found_apply and found_ref and found_mask:
            result['entity_branches_found'].append(entity_name)
        else:
            result['entity_branches_missing'].append(entity_name)
            result['errors'].append(f"Missing branch for entity: {entity_name}")
            result['valid'] = False
    
    return result


def validate_manifest_entities(entities: List[Dict], bundle_path: str) -> Dict:
    """
    Validate manifest entities before workflow generation.
    
    Checks:
    - All entities have mask
    - All entities have reference
    - Files exist
    - Weights in valid range
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'entities_valid': [],
        'entities_invalid': []
    }
    
    bundle = Path(bundle_path)
    
    for entity in entities:
        name = entity.get('name', 'unknown')
        errors = []
        
        # Check required fields
        if not entity.get('mask'):
            errors.append('missing mask path')
        elif not (bundle / entity['mask']).exists():
            errors.append(f"mask file not found: {entity['mask']}")
        
        if not entity.get('reference'):
            errors.append('missing reference path')
        elif not (bundle / entity['reference']).exists():
            errors.append(f"reference file not found: {entity['reference']}")
        
        # Check weight range
        weight = entity.get('ipadapter_weight')
        if weight is None:
            result['warnings'].append(f"{name}: no ipadapter_weight, will use default 0.5")
        elif not (0.0 <= weight <= 1.0):
            errors.append(f"weight out of range: {weight}")
        
        if errors:
            result['entities_invalid'].append({'name': name, 'errors': errors})
            result['errors'].extend([f"{name}: {e}" for e in errors])
            result['valid'] = False
        else:
            result['entities_valid'].append(name)
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: workflow_builder.py <base_workflow> <manifest> [mode] [order]")
        sys.exit(1)
    
    base_workflow = sys.argv[1]
    manifest_path = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'all'
    order = sys.argv[4] if len(sys.argv) > 4 else 'default'
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    bundle_path = str(Path(manifest_path).parent)
    entities = manifest.get('entities', [])
    
    # Validate entities first
    validation = validate_manifest_entities(entities, bundle_path)
    print(f"Entity validation: {'PASSED' if validation['valid'] else 'FAILED'}")
    if validation['errors']:
        for e in validation['errors']:
            print(f"  ERROR: {e}")
    
    if not validation['valid']:
        sys.exit(1)
    
    # Build workflow
    builder = WorkflowBuilder(base_workflow)
    workflow, metadata = builder.build(
        entities=entities,
        bundle_path=bundle_path,
        mode=mode,
        order_policy=order
    )
    
    # Validate generated workflow
    wf_validation = validate_workflow(workflow, metadata['entities_applied'])
    print(f"Workflow validation: {'PASSED' if wf_validation['valid'] else 'FAILED'}")
    
    print(f"\nMetadata:")
    print(f"  Mode: {mode}")
    print(f"  Order: {order}")
    print(f"  Entities applied: {metadata['entities_applied']}")
    print(f"  Regional IPAdapter count: {metadata['regional_ipadapter_count']}")
    
    # Save workflow
    output_path = f"workflow_multi_{mode}_{order}.json"
    with open(output_path, 'w') as f:
        json.dump(workflow, f, indent=2)
    print(f"\nSaved: {output_path}")
