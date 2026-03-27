#!/usr/bin/env python3
"""
Generate bundle manifest from scene_graph.json + ТЗ
Maps entities to material references
"""

import json
import os
import argparse
from pathlib import Path

# Entity → reference mapping (from ТЗ analysis)
ENTITY_REFERENCES = {
    'floor': {
        'reference': 'floor_tiles.jpg',
        'description': 'Напольная плитка Equipe Rivoli Blue 15x15',
        'material_in_model': 'Материал'  # Bergen-Azul
    },
    'wall_tiles': {
        'reference': 'wall_tiles.png',
        'description': 'Настенная плитка Costa Nova Onda White 5x20',
        'material_in_model': 'Материал1'  # White-Glossy
    },
    'wall_paint': {
        'reference': None,  # цвет, не текстура
        'description': 'Краска Lanors Mons №176 Portland',
        'color': '#818181',
        'material_in_model': '[0131_Silver]'
    },
    'vanity': {
        'reference': 'vanity.jpg',
        'description': 'Тумба Тумба 114см тёмно-серая',
        'material_in_model': '[0134_DimGray]'
    },
    'mirror': {
        'reference': 'mirror.jpg',
        'description': 'Зеркало 80×100см с подсветкой',
        'material_in_model': '[Mirror 01]'
    },
    'bathtub': {
        'reference': 'bathtub.jpg',
        'description': 'Ванна Volle 170×70',
        'material_in_model': None  # default white
    },
    'bathtub_screen': {
        'reference': 'wall_tiles.png',  # тот же что стены
        'description': 'Экран ванны - плитка Costa Nova',
        'material_in_model': 'Материал1'
    },
    'shower': {
        'reference': None,
        'description': 'Душевая штора + карниз',
        'material_in_model': None
    },
    'rainshower': {
        'reference': 'rainshower.jpg',
        'description': 'Душевая система IDDIS',
        'material_in_model': 'Chrome1'
    },
    'towel_warmer': {
        'reference': 'towel_warmer.jpg',
        'description': 'Полотенцесушитель Маргроид 50×80',
        'material_in_model': '[0128_White]'
    },
    'basket': {
        'reference': 'basket.jpg',
        'description': 'Корзина AM.PM Raga',
        'material_in_model': 'мяг'  # ротанг
    },
    'window': {
        'reference': None,
        'description': 'Окно с матовым стеклом',
        'material_in_model': 'Материал57'  # стекло
    },
    'faucet': {
        'reference': 'faucet.jpg',
        'description': 'Смеситель IDDIS Shelfy черный',
        'material_in_model': 'black'
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
            'description': info['description'],
            'mask': str(mask_file) if mask_file.exists() else None,
            'mask_exists': mask_file.exists(),
            'material_in_model': info.get('material_in_model')
        }
        
        # Reference image
        if info.get('reference'):
            ref_file = refs_path / info['reference']
            entity_data['reference'] = str(ref_file) if ref_file.exists() else info['reference']
            entity_data['reference_exists'] = ref_file.exists()
        
        # Color (for paint)
        if info.get('color'):
            entity_data['color'] = info['color']
        
        manifest['entities'][entity_name] = entity_data
    
    # Summary
    total = len(manifest['entities'])
    with_masks = sum(1 for e in manifest['entities'].values() if e.get('mask_exists'))
    with_refs = sum(1 for e in manifest['entities'].values() if e.get('reference_exists'))
    
    manifest['summary'] = {
        'total_entities': total,
        'masks_found': with_masks,
        'references_found': with_refs,
        'ready_for_render': with_masks > 0
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
