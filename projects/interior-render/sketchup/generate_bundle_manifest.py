#!/usr/bin/env python3
"""
Generate bundle manifest from scene_graph.json + ТЗ
Maps entities to material references
"""

import json
import os
import argparse
from pathlib import Path

# Entity classes for routing
CLASS_SURFACE = 'surface'
CLASS_FIXTURE = 'fixture'

# Render modes (current = same flow, future = different pipelines)
RENDER_REGIONAL_IPADAPTER = 'regional_ipadapter'  # current unified flow
RENDER_PROJECTION_TILING = 'projection_tiling'    # future: large surfaces
RENDER_LOCAL_INPAINT = 'local_inpaint'            # future: fixture editing

# Entity → reference mapping (from ТЗ analysis)
ENTITY_REFERENCES = {
    # ═══════════════════════════════════════════════════════════
    # SURFACES — large areas, tileable/projectable
    # ═══════════════════════════════════════════════════════════
    'floor': {
        'class': CLASS_SURFACE,
        'surface_kind': 'floor',
        'reference': 'floor_tiles.jpg',
        'description': 'Напольная плитка Equipe Rivoli Blue 15x15',
        'material_in_model': 'Материал',  # Bergen-Azul
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'wall_tiles': {
        'class': CLASS_SURFACE,
        'surface_kind': 'wall',
        'reference': 'wall_tiles.png',
        'description': 'Настенная плитка Costa Nova Onda White 5x20',
        'material_in_model': 'Материал1',  # White-Glossy
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'wall_paint': {
        'class': CLASS_SURFACE,
        'surface_kind': 'wall',
        'reference': None,  # цвет, не текстура
        'description': 'Краска Lanors Mons №176 Portland',
        'color': '#818181',
        'material_in_model': '[0131_Silver]',
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'bathtub_screen': {
        'class': CLASS_SURFACE,
        'surface_kind': 'bathtub_screen',
        'reference': 'wall_tiles.png',  # тот же что стены
        'description': 'Экран ванны - плитка Costa Nova',
        'material_in_model': 'Материал1',
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    
    # ═══════════════════════════════════════════════════════════
    # FIXTURES — discrete objects, locally editable
    # ═══════════════════════════════════════════════════════════
    'vanity': {
        'class': CLASS_FIXTURE,
        'reference': 'vanity.jpg',
        'description': 'Тумба 114см тёмно-серая',
        'material_in_model': '[0134_DimGray]',
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'mirror': {
        'class': CLASS_FIXTURE,
        'reference': 'mirror.jpg',
        'description': 'Зеркало 80×100см с подсветкой',
        'material_in_model': '[Mirror 01]',
        'critical': False,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'bathtub': {
        'class': CLASS_FIXTURE,
        'reference': 'bathtub.jpg',
        'description': 'Ванна Volle 170×70',
        'material_in_model': None,  # default white
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'shower': {
        'class': CLASS_FIXTURE,
        'reference': None,
        'description': 'Душевая штора + карниз',
        'material_in_model': None,
        'critical': False,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'rainshower': {
        'class': CLASS_FIXTURE,
        'reference': 'rainshower.jpg',
        'description': 'Душевая система IDDIS',
        'material_in_model': 'Chrome1',
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'towel_warmer': {
        'class': CLASS_FIXTURE,
        'reference': 'towel_warmer.jpg',
        'description': 'Полотенцесушитель Маргроид 50×80',
        'material_in_model': '[0128_White]',
        'critical': False,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'basket': {
        'class': CLASS_FIXTURE,
        'reference': 'basket.jpg',
        'description': 'Корзина AM.PM Raga',
        'material_in_model': 'мяг',  # ротанг
        'critical': False,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'window': {
        'class': CLASS_FIXTURE,
        'reference': None,
        'description': 'Окно с матовым стеклом',
        'material_in_model': 'Материал57',  # стекло
        'critical': False,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    },
    'faucet': {
        'class': CLASS_FIXTURE,
        'reference': 'faucet.jpg',
        'description': 'Смеситель IDDIS Shelfy черный',
        'material_in_model': 'black',
        'critical': True,
        'render_mode': RENDER_REGIONAL_IPADAPTER
    }
}


def generate_manifest(masks_dir: str, references_dir: str, output_path: str, scene_name: str = 'Сцена №1'):
    """Generate bundle manifest JSON"""
    
    masks_path = Path(masks_dir)
    refs_path = Path(references_dir)
    
    manifest = {
        'version': '1.0',
        'scene': scene_name,
        'generated': True,
        'entities': {}
    }
    
    for entity_name, info in ENTITY_REFERENCES.items():
        mask_file = masks_path / f'mask_{entity_name}.png'
        
        entity_data = {
            'class': info.get('class'),
            'description': info['description'],
            'mask_path': str(mask_file) if mask_file.exists() else None,
            'mask_exists': mask_file.exists(),
            'material_in_model': info.get('material_in_model'),
            'critical': info.get('critical', False),
            'render_mode': info.get('render_mode', RENDER_REGIONAL_IPADAPTER)
        }
        
        # Surface-specific fields
        if info.get('surface_kind'):
            entity_data['surface_kind'] = info['surface_kind']
        
        # Reference image
        if info.get('reference'):
            ref_file = refs_path / info['reference']
            entity_data['reference_path'] = str(ref_file) if ref_file.exists() else info['reference']
            entity_data['reference_exists'] = ref_file.exists()
        
        # Color (for paint surfaces without texture)
        if info.get('color'):
            entity_data['color'] = info['color']
        
        manifest['entities'][entity_name] = entity_data
    
    # Summary with class breakdown
    entities = manifest['entities']
    surfaces = {k: v for k, v in entities.items() if v.get('class') == CLASS_SURFACE}
    fixtures = {k: v for k, v in entities.items() if v.get('class') == CLASS_FIXTURE}
    
    manifest['summary'] = {
        'total_entities': len(entities),
        'surfaces': len(surfaces),
        'fixtures': len(fixtures),
        'masks_found': sum(1 for e in entities.values() if e.get('mask_exists')),
        'references_found': sum(1 for e in entities.values() if e.get('reference_exists')),
        'critical_entities': sum(1 for e in entities.values() if e.get('critical')),
        'ready_for_render': sum(1 for e in entities.values() if e.get('mask_exists')) > 0
    }
    
    # Write
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Generated: {output_path}")
    print(f"  Entities: {total}")
    print(f"  Masks found: {with_masks}/{total}")
    print(f"  References found: {with_refs}/{total}")
    
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate bundle manifest')
    parser.add_argument('--masks', required=True, help='Directory with mask_*.png files')
    parser.add_argument('--references', required=True, help='Directory with reference images from ТЗ')
    parser.add_argument('--output', default='bundle_manifest.json', help='Output manifest path')
    parser.add_argument('--scene', default='Сцена №1', help='Scene name')
    
    args = parser.parse_args()
    generate_manifest(args.masks, args.references, args.output, args.scene)
