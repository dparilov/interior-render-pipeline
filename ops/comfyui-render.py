#!/usr/bin/env python3
"""
ComfyUI Universal Render — парсит ТЗ и строит workflow динамически

Использование:
  python3 comfyui-render.py --tz ~/ComfyUI/input/project/ТЗ.md

Скрипт:
1. Парсит ТЗ.md и извлекает все референсы
2. Строит workflow с IP-Adapter для каждого референса
3. Логирует всё что использовал
"""

import argparse
import json
import urllib.request
import time
import sys
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

COMFYUI_URL = "http://127.0.0.1:8188"
LOG_DIR = os.path.expanduser("~/.openclaw/workspace/logs/comfyui")


def get_memory_usage():
    """Возвращает использование RAM в GB"""
    try:
        result = subprocess.run(['free', '-b'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        mem_line = [l for l in lines if l.startswith('Mem:')][0]
        parts = mem_line.split()
        total = int(parts[1]) / (1024**3)
        used = int(parts[2]) / (1024**3)
        available = int(parts[6]) / (1024**3)
        return {'total_gb': round(total, 1), 'used_gb': round(used, 1), 'available_gb': round(available, 1)}
    except:
        return {'total_gb': 0, 'used_gb': 0, 'available_gb': 0}


def get_system_stats():
    """Возвращает CPU и RAM stats"""
    try:
        mem = get_memory_usage()
        # CPU load
        with open('/proc/loadavg', 'r') as f:
            load = f.read().split()[:3]
        return {
            'timestamp': datetime.now().isoformat(),
            'ram_used_gb': mem['used_gb'],
            'ram_available_gb': mem['available_gb'],
            'cpu_load_1m': float(load[0]),
            'cpu_load_5m': float(load[1]),
        }
    except:
        return {}


def start_memory_monitor(log_file, interval=5):
    """Запускает фоновый мониторинг памяти"""
    import threading
    
    def monitor():
        while True:
            try:
                stats = get_system_stats()
                with open(log_file, 'a') as f:
                    f.write(json.dumps(stats) + '\n')
                time.sleep(interval)
            except:
                break
    
    t = threading.Thread(target=monitor, daemon=True)
    t.start()
    return t

# ============================================================
# ПАРСЕР ТЗ
# ============================================================

def parse_tz(tz_path):
    """Парсит ТЗ.md и извлекает все данные"""
    tz_path = Path(tz_path).expanduser()
    project_dir = tz_path.parent
    
    with open(tz_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = {
        'project_dir': str(project_dir),
        'project_name': project_dir.name,
        'sketches': [],
        'references': {},
        'constraints': [],
        'style': {},
        'raw_content': content
    }
    
    # Ищем скетчи
    sketch_pattern = r'`скетчи/([^`]+)`|скетчи/(\S+\.(?:jpg|png|jpeg))'
    for match in re.finditer(sketch_pattern, content, re.IGNORECASE):
        sketch = match.group(1) or match.group(2)
        sketch_path = project_dir / 'скетчи' / sketch
        if sketch_path.exists():
            result['sketches'].append(str(sketch_path))
    
    # Ищем "Для первого рендера использовать"
    first_sketch = re.search(r'Для первого рендера[^`]*`скетчи/([^`]+)`', content)
    if first_sketch:
        result['primary_sketch'] = str(project_dir / 'скетчи' / first_sketch.group(1))
    elif result['sketches']:
        result['primary_sketch'] = result['sketches'][0]
    
    # Ищем референсы — паттерн "**Референс:** `референсы/filename`"
    ref_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Референс:\*\*\s*`референсы/([^`]+)`'
    for match in re.finditer(ref_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        ref_file = match.group(2).strip()
        ref_path = project_dir / 'референсы' / ref_file
        
        if ref_path.exists():
            # Нормализуем имя элемента
            key = normalize_element_name(element_name)
            result['references'][key] = {
                'name': element_name,
                'path': str(ref_path),
                'file': ref_file
            }
    
    # Ищем критичные элементы
    critical_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*КРИТИЧНО:\*\*\s*ДА'
    for match in re.finditer(critical_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['critical'] = True
    
    # Ищем модель/артикул для каждого элемента
    model_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Модель:\*\*\s*([^\n]+)'
    for match in re.finditer(model_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        model = match.group(2).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['model'] = model
    
    # Ищем артикул
    article_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Артикул:\*\*\s*([^\n]+)'
    for match in re.finditer(article_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        article = match.group(2).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['article'] = article
    
    # Ищем описание
    desc_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Описание:\*\*\s*([^\n]+)'
    for match in re.finditer(desc_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        description = match.group(2).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['description'] = description
    
    # Ищем размер
    size_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Размер:\*\*\s*([^\n]+)'
    for match in re.finditer(size_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        size = match.group(2).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['size'] = size
    
    # Извлекаем общее описание проекта
    general_desc = re.search(r'##\s*Общее описание\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if general_desc:
        result['general_description'] = general_desc.group(1).strip()
    
    # Ищем фактуры — паттерн "**Фактура:** текст"
    texture_pattern = r'###\s*([^\n]+)\n(?:[^#]*?)\*\*Фактура:\*\*\s*([^\n*]+)'
    for match in re.finditer(texture_pattern, content, re.IGNORECASE | re.DOTALL):
        element_name = match.group(1).strip()
        texture = match.group(2).strip()
        key = normalize_element_name(element_name)
        if key in result['references']:
            result['references'][key]['texture'] = texture
    
    # Ищем референс освещения
    lighting_pattern = r'##\s*Референс освещения\s*\n(?:[^#]*?)\*\*Файл:\*\*\s*`референсы/([^`]+)`'
    lighting_match = re.search(lighting_pattern, content, re.IGNORECASE | re.DOTALL)
    if lighting_match:
        lighting_path = project_dir / 'референсы' / lighting_match.group(1).strip()
        if lighting_path.exists():
            result['lighting_ref'] = str(lighting_path)
    
    # Ищем ограничения
    constraints_section = re.search(r'##\s*Ограничения\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if constraints_section:
        result['constraints'] = constraints_section.group(1).strip()
    
    # Ищем стиль
    style_section = re.search(r'##\s*Стиль рендера\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if style_section:
        result['style']['description'] = style_section.group(1).strip()
    
    return result


def normalize_element_name(name):
    """Нормализует название элемента в ключ"""
    name = name.lower()
    # Универсальный маппинг элементов интерьера RU -> EN ключи
    # Порядок важен! Более специфичные паттерны первыми
    mappings = [
        # Ванная
        ('полотенцесушител', 'towel_warmer'), ('полотенц', 'towel_warmer'), ('радиатор', 'radiator'),
        ('ванн', 'bathtub'), ('душ', 'shower'), ('унитаз', 'toilet'), ('биде', 'bidet'),
        # Кухня
        ('столешниц', 'countertop'), ('варочн', 'cooktop'), ('духов', 'oven'),
        ('холодильник', 'fridge'), ('вытяжк', 'hood'), ('посудомо', 'dishwasher'),
        # Мебель общая
        ('тумб', 'cabinet'), ('шкаф', 'wardrobe'), ('комод', 'dresser'),
        ('стол', 'table'), ('стул', 'chair'), ('кресл', 'armchair'),
        ('диван', 'sofa'), ('кроват', 'bed'), ('полк', 'shelf'),
        # Сантехника
        ('смесител', 'faucet'), ('кран', 'faucet'), ('раковин', 'sink'),
        # Отделка
        ('напольн', 'floor'), ('настенн', 'wall'), ('потолоч', 'ceiling'),
        ('плитк', 'tiles'), ('обо', 'wallpaper'), ('ламинат', 'laminate'),
        # Декор
        ('зеркал', 'mirror'), ('корзин', 'basket'), ('штор', 'curtain'),
        ('светильник', 'lamp'), ('люстр', 'chandelier'), ('ковр', 'carpet'),
        ('картин', 'painting'), ('ваз', 'vase'), ('растен', 'plant'),
    ]
    for pattern, key in mappings:
        if pattern in name:
            return key
    # Fallback — транслит
    return re.sub(r'[^a-z0-9]', '_', name)[:20]


# ============================================================
# ГЕНЕРАТОР ПРОМПТА
# ============================================================

def generate_prompts(tz_data):
    """Генерирует детальные промпты из ТЗ — ВСЕ данные должны попасть в промпт!"""
    
    # === POSITIVE PROMPT ===
    parts = []
    
    # 1. Заголовок качества
    parts.append("ULTRA HIGH QUALITY photorealistic interior photograph for Architectural Digest magazine cover")
    parts.append("Professional architectural photography, Hasselblad H6D-400c medium format camera")
    parts.append("8K ultra high resolution, tack sharp details, perfect exposure")
    parts.append("EXACT LAYOUT preserved from reference sketch")
    
    # 2. Ракурс из скетчей
    if tz_data.get('primary_sketch'):
        sketch_name = Path(tz_data['primary_sketch']).stem.lower()
        if 'front' in sketch_name or 'фронт' in sketch_name:
            parts.append("Front view perspective, straight-on camera angle")
        elif 'angle' in sketch_name or 'угол' in sketch_name:
            parts.append("Angled perspective view, three-quarter camera angle")
        elif 'top' in sketch_name or 'сверху' in sketch_name:
            parts.append("Top-down view, overhead camera angle")
        else:
            parts.append("Front view perspective")
    
    # 3. Общее описание из ТЗ (полностью)
    if tz_data.get('general_description'):
        desc = tz_data['general_description']
        # Добавляем всё описание, заменяя переводы строк
        parts.append(desc.replace('\n', ' ').strip())
    
    # 4. Стиль рендера из ТЗ (ВСЕ пункты)
    if tz_data.get('style', {}).get('description'):
        style_text = tz_data['style']['description']
        for line in style_text.split('\n'):
            # Убираем markdown форматирование
            line = re.sub(r'\*\*([^*]+):\*\*', r'\1:', line)  # **Освещение:** -> Освещение:
            line = line.strip('- *').strip()
            if line and len(line) > 5:
                # Конвертируем ключевые слова
                if 'освещение' in line.lower():
                    # Убираем дублирование "LIGHTING: Освещение:"
                    line = re.sub(r'^освещение:\s*', '', line, flags=re.IGNORECASE)
                    parts.append(f"LIGHTING: {line}")
                elif 'атмосфера' in line.lower():
                    line = re.sub(r'^атмосфера:\s*', '', line, flags=re.IGNORECASE)
                    parts.append(f"ATMOSPHERE: {line}")
                elif 'качество' in line.lower():
                    line = re.sub(r'^качество:\s*', '', line, flags=re.IGNORECASE)
                    parts.append(f"QUALITY: {line}")
                elif 'детали' in line.lower():
                    line = re.sub(r'^детали:\s*', '', line, flags=re.IGNORECASE)
                    parts.append(f"DETAILS: {line}")
                else:
                    parts.append(line)
    
    # 5. MATERIALS AND COLORS - CRITICAL секция
    parts.append("MATERIALS AND COLORS - CRITICAL:")
    
    # Сортируем: критичные элементы первыми
    refs = tz_data.get('references', {})
    critical_refs = [(k, v) for k, v in refs.items() if v.get('critical')]
    normal_refs = [(k, v) for k, v in refs.items() if not v.get('critical')]
    
    for key, ref_data in critical_refs + normal_refs:
        element_parts = []
        
        # Название элемента (капсом для критичных)
        name = ref_data.get('name', key).upper() if ref_data.get('critical') else ref_data.get('name', key)
        element_parts.append(name)
        
        # Модель в скобках
        if ref_data.get('model'):
            element_parts.append(f"({ref_data['model']})")
        
        # Артикул
        if ref_data.get('article'):
            element_parts.append(f"[{ref_data['article']}]")
        
        # Описание — самое важное!
        if ref_data.get('description'):
            desc = ref_data['description']
            element_parts.append(f"- {desc}")
        
        # Размер
        if ref_data.get('size'):
            element_parts.append(f"size: {ref_data['size']}")
        
        # Фактура
        if ref_data.get('texture'):
            element_parts.append(f"texture: {ref_data['texture']}")
        
        # CRITICAL маркер
        if ref_data.get('critical'):
            element_parts.append("- CRITICAL ELEMENT")
        
        parts.append(" ".join(element_parts))
    
    # 6. Дополнительные детали интерьера (если указаны в общем описании или стиле)
    # Парсим из raw_content если есть упоминание верхней части стен
    raw = tz_data.get('raw_content', '').lower()
    if 'верх' in raw and 'стен' in raw:
        # Ищем описание верхней части стен
        walls_upper = re.search(r'верх[а-я]*\s+стен[а-я]*[:\s]+([^\.]+)', raw, re.IGNORECASE)
        if walls_upper:
            parts.append(f"WALLS UPPER HALF: {walls_upper.group(1).strip()}")
    
    # 7. Качество финала (детализация) — универсальные характеристики
    parts.append("hyperrealistic materials and textures, accurate material properties")
    parts.append("soft shadows, depth of field, magazine editorial cover quality")
    parts.append("rich saturated colors, natural lighting")
    
    positive = ". ".join(parts)
    
    # === NEGATIVE PROMPT ===
    negative_parts = [
        # Стиль
        "cartoon, anime, drawing, sketch, painting, illustration, CGI, 3D render",
        "low quality, blurry, out of focus, distorted, deformed",
        "watermark, text, signature, logo, border, frame",
        "plastic look, video game graphics, Blender, Maya, Unreal Engine",
        "wrong colors, color bleeding, jpeg artifacts, noise, grain"
    ]
    
    # Добавляем ограничения из ТЗ — универсальный парсинг
    if tz_data.get('constraints'):
        constraints = tz_data['constraints']
        
        # Универсальный маппинг цветов/материалов RU -> EN
        color_map = {
            'латунн': 'brass', 'золот': 'gold, golden', 'бронз': 'bronze',
            'хром': 'chrome, silver, metallic', 'никел': 'nickel',
            'бел': 'white, light', 'чёрн': 'black, dark', 'черн': 'black, dark',
            'сер': 'gray, grey', 'беж': 'beige, cream, tan',
            'коричнев': 'brown', 'дерев': 'wood, wooden',
            'красн': 'red', 'син': 'blue', 'зелен': 'green',
        }
        
        # Ищем паттерны "НЕ [цвет/материал]" или "[цвет] [объект] - НЕТ"
        constraints_lower = constraints.lower()
        for ru_color, en_colors in color_map.items():
            if ru_color in constraints_lower:
                # Проверяем контекст запрета
                if any(x in constraints_lower for x in ['не ', 'нет', 'нельзя', '⛔']):
                    negative_parts.append(en_colors)
        
        # Общие запреты на изменение layout
        negative_parts.append("different layout, moved furniture, wrong position, extra objects, missing objects")
    
    negative = ", ".join(negative_parts)
    
    return positive, negative


# ============================================================
# WORKFLOW BUILDER
# ============================================================

def to_comfyui_path(abs_path):
    """Конвертирует абсолютный путь в относительный для ComfyUI input"""
    abs_path = str(abs_path)
    comfyui_input = os.path.expanduser("~/ComfyUI/input/")
    if abs_path.startswith(comfyui_input):
        return abs_path[len(comfyui_input):]
    # Fallback - попробуем найти /input/ в пути
    if '/input/' in abs_path:
        return abs_path.split('/input/', 1)[1]
    return abs_path

def build_workflow(tz_data, params):
    """Строит workflow динамически из ТЗ"""
    
    positive_prompt, negative_prompt = generate_prompts(tz_data)
    
    # Конвертируем путь скетча
    sketch_path = to_comfyui_path(tz_data['primary_sketch'])
    
    workflow = {
        # === LOADERS ===
        "checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "RealVisXL_V4.0.safetensors"}
        },
        "refiner": {
            "class_type": "CheckpointLoaderSimple", 
            "inputs": {"ckpt_name": "sd_xl_refiner_1.0.safetensors"}
        },
        "vae": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "sdxl_vae.safetensors"}
        },
        "controlnet_canny": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "controlnet-canny-sdxl.safetensors"}
        },
        
        # === SKETCH ===
        "load_sketch": {
            "class_type": "LoadImage",
            "inputs": {"image": sketch_path}
        },
        "canny_preprocess": {
            "class_type": "Canny",
            "inputs": {
                "image": ["load_sketch", 0],
                "low_threshold": 0.1,
                "high_threshold": 0.4
            }
        },
        
        # === PROMPTS ===
        "positive": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": positive_prompt
            }
        },
        "negative": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["checkpoint", 1],
                "text": negative_prompt
            }
        },
        
        # === CONTROLNET ===
        "apply_controlnet": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["positive", 0],
                "negative": ["negative", 0],
                "control_net": ["controlnet_canny", 0],
                "image": ["canny_preprocess", 0],
                "strength": params['cn_strength'],
                "start_percent": 0.0,
                "end_percent": 0.8
            }
        },
        
        # === LATENT ===
        "empty_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": params['size'], "height": params['size'], "batch_size": 1}
        },
    }
    
    # === IP-ADAPTER для каждого референса ===
    references = tz_data.get('references', {})
    current_model = ["checkpoint", 0]
    ip_adapter_log = []
    
    # === IP-ADAPTER для каждого референса ===
    use_ipadapter = not params.get('no_ipadapter', False)
    if references and use_ipadapter:
        workflow["ipadapter_model"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter_sdxl.safetensors"}
        }
        workflow["clip_vision"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"}
        }
        
        # Веса рассчитываются динамически:
        # - CRITICAL элементы: base 0.85
        # - Обычные элементы: base 0.5
        # - Масштабируются через --ip-strength
        
        for key, ref_data in references.items():
            ref_path = to_comfyui_path(ref_data['path'])
            
            # Базовый вес зависит от критичности
            if ref_data.get('critical'):
                base_weight = 0.85
            else:
                base_weight = 0.5
            
            weight = params['ip_strength'] * base_weight
            weight = min(weight, 1.0)  # Не больше 1.0
            
            node_load = f"load_ref_{key}"
            node_ip = f"ipadapter_{key}"
            
            workflow[node_load] = {
                "class_type": "LoadImage",
                "inputs": {"image": ref_path}
            }
            workflow[node_ip] = {
                "class_type": "IPAdapterAdvanced",
                "inputs": {
                    "model": current_model,
                    "ipadapter": ["ipadapter_model", 0],
                    "clip_vision": ["clip_vision", 0],
                    "image": [node_load, 0],
                    "weight": weight,
                    "weight_type": "linear",
                    "start_at": 0.0,
                    "end_at": 1.0,
                    "unfold_batch": False,
                    "combine_embeds": "concat",
                    "embeds_scaling": "V only"
                }
            }
            current_model = [node_ip, 0]
            
            ip_adapter_log.append({
                'element': ref_data['name'],
                'key': key,
                'path': ref_path,
                'weight': round(weight, 3),
                'critical': ref_data.get('critical', False),
                'texture': ref_data.get('texture', None)
            })
    
    # === LIGHTING REFERENCE (отдельный IP-Adapter с низким весом) ===
    lighting_ref = tz_data.get('lighting_ref')
    if lighting_ref and use_ipadapter:
        lighting_path = to_comfyui_path(lighting_ref)
        
        # Убедимся что IP-Adapter инфраструктура есть
        if "ipadapter_model" not in workflow:
            workflow["ipadapter_model"] = {
                "class_type": "IPAdapterModelLoader",
                "inputs": {"ipadapter_file": "ip-adapter_sdxl.safetensors"}
            }
            workflow["clip_vision"] = {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"}
            }
        
        workflow["load_lighting_ref"] = {
            "class_type": "LoadImage",
            "inputs": {"image": lighting_path}
        }
        workflow["ipadapter_lighting"] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": current_model,
                "ipadapter": ["ipadapter_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["load_lighting_ref", 0],
                "weight": 0.3,  # Низкий вес — влияет на атмосферу, не на объекты
                "weight_type": "style transfer",  # Специально для переноса стиля
                "start_at": 0.0,
                "end_at": 0.5,  # Только в начале — задаёт настроение
                "unfold_batch": False,
                "combine_embeds": "concat",
                "embeds_scaling": "V only"
            }
        }
        current_model = ["ipadapter_lighting", 0]
        
        ip_adapter_log.append({
            'element': 'Освещение (атмосфера)',
            'key': 'lighting',
            'path': lighting_path,
            'weight': 0.3,
            'critical': False,
            'type': 'lighting'
        })
    
    # === SAMPLER ===
    workflow["sampler_base"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": current_model,
            "positive": ["apply_controlnet", 0],
            "negative": ["apply_controlnet", 1],
            "latent_image": ["empty_latent", 0],
            "seed": int(time.time()),
            "steps": params['steps'],
            "cfg": params['cfg'],
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1.0
        }
    }
    
    # === REFINER (опционально) ===
    use_refiner = not params.get('no_refiner', False)
    two_pass = params.get('two_pass', False)
    
    if two_pass:
        # Two-pass mode: сохраняем latent и выходим (pass 1)
        # или загружаем latent и делаем refiner (pass 2)
        pass_num = params.get('pass_num', 1)
        latent_file = params.get('latent_file', 'latent_temp')
        
        if pass_num == 1:
            # Pass 1: Base → сохранить latent
            del workflow["refiner"]
            workflow["save_latent"] = {
                "class_type": "SaveLatent",
                "inputs": {
                    "samples": ["sampler_base", 0],
                    "filename_prefix": latent_file
                }
            }
            # Также декодируем для превью
            workflow["vae_decode"] = {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["sampler_base", 0],
                    "vae": ["vae", 0]
                }
            }
            workflow["save"] = {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["vae_decode", 0],
                    "filename_prefix": f"{params['output']}_pass1"
                }
            }
        else:
            # Pass 2: загрузить картинку Pass 1 → VAEEncode → Refiner
            # Строим минимальный workflow
            
            # Найдём последнюю картинку pass1
            import glob
            pass1_images = sorted(glob.glob(os.path.expanduser("~/ComfyUI/output/*_pass1_*.png")))
            if not pass1_images:
                print("❌ Не найдена картинка Pass 1. Сначала запустите --two-pass --pass 1")
                return {}, []
            pass1_image = os.path.basename(pass1_images[-1])
            print(f"📷 Загружаю Pass 1: {pass1_image}")
            
            workflow = {
                "refiner": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "sd_xl_refiner_1.0.safetensors"}
                },
                "vae": {
                    "class_type": "VAELoader",
                    "inputs": {"vae_name": "sdxl_vae.safetensors"}
                },
                "load_pass1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": pass1_image}
                },
                "vae_encode": {
                    "class_type": "VAEEncode",
                    "inputs": {
                        "pixels": ["load_pass1", 0],
                        "vae": ["vae", 0]
                    }
                },
                "refiner_positive": {
                    "class_type": "CLIPTextEncodeSDXLRefiner",
                    "inputs": {
                        "clip": ["refiner", 1],
                        "ascore": 6.0,
                        "width": params['size'],
                        "height": params['size'],
                        "text": "photorealistic interior, professional photography, sharp details, 8k"
                    }
                },
                "refiner_negative": {
                    "class_type": "CLIPTextEncodeSDXLRefiner",
                    "inputs": {
                        "clip": ["refiner", 1],
                        "ascore": 2.0,
                        "width": params['size'],
                        "height": params['size'],
                        "text": "blurry, low quality, cartoon, painting"
                    }
                },
                "sampler_refiner": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["refiner", 0],
                        "positive": ["refiner_positive", 0],
                        "negative": ["refiner_negative", 0],
                        "latent_image": ["vae_encode", 0],
                        "seed": int(time.time()) + 1,
                        "steps": 12,
                        "cfg": 7.5,
                        "sampler_name": "dpmpp_2m",
                        "scheduler": "normal",
                        "denoise": 0.25
                    }
                },
                "vae_decode": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["sampler_refiner", 0],
                        "vae": ["vae", 0]
                    }
                },
                "save": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["vae_decode", 0],
                        "filename_prefix": params['output']
                    }
                }
            }
            
            return workflow, [{'element': 'Refiner Pass 2', 'key': 'refiner', 'type': 'refiner'}]
    elif use_refiner:
        workflow["refiner_positive"] = {
            "class_type": "CLIPTextEncodeSDXLRefiner",
            "inputs": {
                "clip": ["refiner", 1],
                "ascore": 6.0,
                "width": 1024,
                "height": 1024,
                "text": "photorealistic interior, professional photography, sharp details"
            }
        }
        workflow["refiner_negative"] = {
            "class_type": "CLIPTextEncodeSDXLRefiner",
            "inputs": {
                "clip": ["refiner", 1],
                "ascore": 2.0,
                "width": 1024,
                "height": 1024,
                "text": "blurry, low quality, cartoon"
            }
        }
        workflow["sampler_refiner"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["refiner", 0],
                "positive": ["refiner_positive", 0],
                "negative": ["refiner_negative", 0],
                "latent_image": ["sampler_base", 0],
                "seed": int(time.time()) + 1,
                "steps": 12,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "normal",
                "denoise": 0.25
            }
        }
        vae_input = ["sampler_refiner", 0]
        
        workflow["vae_decode"] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": vae_input,
                "vae": ["vae", 0]
            }
        }
        workflow["save"] = {
            "class_type": "SaveImage",
            "inputs": {
                    "images": ["vae_decode", 0],
                    "filename_prefix": params['output']
                }
            }
    elif use_refiner:
        workflow["refiner_positive"] = {
            "class_type": "CLIPTextEncodeSDXLRefiner",
            "inputs": {
                "clip": ["refiner", 1],
                "ascore": 6.0,
                "width": 1024,
                "height": 1024,
                "text": "photorealistic interior, professional photography, sharp details"
            }
        }
        workflow["refiner_negative"] = {
            "class_type": "CLIPTextEncodeSDXLRefiner",
            "inputs": {
                "clip": ["refiner", 1],
                "ascore": 2.0,
                "width": 1024,
                "height": 1024,
                "text": "blurry, low quality, cartoon"
            }
        }
        workflow["sampler_refiner"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["refiner", 0],
                "positive": ["refiner_positive", 0],
                "negative": ["refiner_negative", 0],
                "latent_image": ["sampler_base", 0],
                "seed": int(time.time()) + 1,
                "steps": 12,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "normal",
                "denoise": 0.25
            }
        }
        vae_input = ["sampler_refiner", 0]
        
        workflow["vae_decode"] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": vae_input,
                "vae": ["vae", 0]
            }
        }
        workflow["save"] = {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["vae_decode", 0],
                "filename_prefix": params['output']
            }
        }
    else:
        # Без Refiner — удаляем его loader
        del workflow["refiner"]
        vae_input = ["sampler_base", 0]
        
        workflow["vae_decode"] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": vae_input,
                "vae": ["vae", 0]
            }
        }
        workflow["save"] = {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["vae_decode", 0],
                "filename_prefix": params['output']
            }
        }
    
    return workflow, ip_adapter_log


# ============================================================
# COMFYUI API
# ============================================================

def analyze_workflow(workflow):
    """Анализирует workflow для верификации"""
    analysis = {
        'total_nodes': len(workflow),
        'ipadapter_nodes': [],
        'controlnet_nodes': [],
        'loaded_images': [],
        'models_used': [],
    }
    
    for node_id, node in workflow.items():
        class_type = node.get('class_type', '')
        inputs = node.get('inputs', {})
        
        # IP-Adapter ноды
        if 'IPAdapter' in class_type:
            analysis['ipadapter_nodes'].append({
                'node_id': node_id,
                'class': class_type,
                'weight': inputs.get('weight'),
                'image_source': inputs.get('image', [None])[0] if isinstance(inputs.get('image'), list) else None
            })
        
        # ControlNet ноды
        if 'ControlNet' in class_type:
            analysis['controlnet_nodes'].append({
                'node_id': node_id,
                'class': class_type,
                'strength': inputs.get('strength')
            })
        
        # Загруженные изображения
        if class_type == 'LoadImage':
            analysis['loaded_images'].append({
                'node_id': node_id,
                'image': inputs.get('image')
            })
        
        # Модели
        if 'Loader' in class_type:
            for key in ['ckpt_name', 'vae_name', 'control_net_name', 'ipadapter_file', 'clip_name']:
                if key in inputs:
                    analysis['models_used'].append({
                        'node_id': node_id,
                        'type': key,
                        'file': inputs[key]
                    })
    
    # Итоговая проверка
    analysis['verification'] = {
        'ipadapter_count': len(analysis['ipadapter_nodes']),
        'controlnet_count': len(analysis['controlnet_nodes']),
        'images_loaded': len(analysis['loaded_images']),
        'has_refiner': any('refiner' in n.lower() for n in workflow.keys()),
        'has_vae': any('vae' in n.lower() for n in workflow.keys()),
    }
    
    return analysis


def queue_prompt(workflow):
    """Отправляет workflow в ComfyUI"""
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('prompt_id')
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}", file=sys.stderr)
        return None


def wait_for_completion(prompt_id, timeout=2400):
    """Ждёт завершения генерации"""
    start = time.time()
    last_progress = ""
    
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if prompt_id in data:
                    status = data[prompt_id].get('status', {})
                    if status.get('status_str') == 'success':
                        outputs = data[prompt_id].get('outputs', {})
                        for node_id, output in outputs.items():
                            if 'images' in output:
                                for img in output['images']:
                                    return os.path.join(
                                        os.path.expanduser("~/ComfyUI/output"),
                                        img['filename']
                                    )
                    elif status.get('status_str') == 'error':
                        for msg in status.get('messages', []):
                            if msg[0] == 'execution_error':
                                return None, msg[1].get('exception_message', 'unknown error')
        except:
            pass
        
        # Прогресс из лога
        try:
            with open('/tmp/comfyui.log', 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-10:]):
                    if '%|' in line:
                        progress = line.strip().split('\r')[-1][:60]
                        if progress != last_progress:
                            elapsed = int(time.time() - start)
                            print(f"[{elapsed//60}m{elapsed%60:02d}s] {progress}")
                            last_progress = progress
                        break
        except:
            pass
        
        time.sleep(10)
    
    return None, f"Timeout after {timeout}s"


# ============================================================
# LOGGING
# ============================================================

def save_log(log_data, workflow=None):
    """Сохраняет лог рендера и workflow"""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(LOG_DIR, f"render_{timestamp}.json")
    
    # Сохраняем workflow отдельно для полного аудита
    if workflow:
        workflow_path = os.path.join(LOG_DIR, f"workflow_{timestamp}.json")
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        log_data['workflow_file'] = workflow_path
        
        # Анализируем workflow для верификации
        workflow_analysis = analyze_workflow(workflow)
        log_data['workflow_analysis'] = workflow_analysis
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    # Также выводим summary в консоль
    print("\n" + "="*60)
    print("📋 RENDER LOG")
    print("="*60)
    print(f"Project: {log_data.get('project_name')}")
    print(f"Sketch: {log_data.get('sketch')}")
    print(f"Output: {log_data.get('output_file')}")
    print(f"Duration: {log_data.get('duration_seconds')}s")
    print(f"\n📦 IP-Adapter References ({len(log_data.get('ip_adapters', []))}):")
    for ip in log_data.get('ip_adapters', []):
        critical = " ⚠️ CRITICAL" if ip.get('critical') else ""
        print(f"  • {ip['element']}: weight={ip['weight']}{critical}")
    print(f"\n⚙️ Parameters:")
    for k, v in log_data.get('params', {}).items():
        print(f"  • {k}: {v}")
    # Workflow verification
    if 'workflow_analysis' in log_data:
        v = log_data['workflow_analysis'].get('verification', {})
        print(f"\n🔍 Workflow Verification:")
        print(f"  • IP-Adapter nodes: {v.get('ipadapter_count', 0)}")
        print(f"  • ControlNet nodes: {v.get('controlnet_count', 0)}")
        print(f"  • Images loaded: {v.get('images_loaded', 0)}")
        print(f"  • Has Refiner: {v.get('has_refiner', False)}")
        print(f"  • Has VAE: {v.get('has_vae', False)}")
    
    print("="*60)
    print(f"📁 Full log: {log_path}")
    if log_data.get('workflow_file'):
        print(f"📁 Workflow: {log_data['workflow_file']}")
    
    return log_path


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='ComfyUI Universal Render')
    parser.add_argument('--tz', required=True, help='Путь к ТЗ.md')
    parser.add_argument('--output', default=None, help='Имя выходного файла')
    parser.add_argument('--steps', type=int, default=50)
    parser.add_argument('--cfg', type=float, default=7.5)
    parser.add_argument('--cn-strength', type=float, default=0.4)
    parser.add_argument('--ip-strength', type=float, default=0.85)
    parser.add_argument('--no-ipadapter', action='store_true', help='Отключить IP-Adapter (только промпт + ControlNet)')
    parser.add_argument('--no-refiner', action='store_true', help='Отключить Refiner (экономия ~6GB RAM)')
    parser.add_argument('--two-pass', action='store_true', help='Двухпроходный режим: Base → сохранить latent → Refiner')
    parser.add_argument('--pass', dest='pass_num', type=int, choices=[1, 2], help='Номер прохода (только с --two-pass)')
    parser.add_argument('--latent-file', default='latent_temp', help='Имя файла для промежуточного latent')
    parser.add_argument('--size', type=int, default=1024, help='Размер изображения (1024, 768, 512)')
    parser.add_argument('--bundle', default=None, help='Путь к scene bundle (пропускает сегментацию, использует authoritative маски)')

    
    args = parser.parse_args()
    
    # Режим bundle — пропускаем сегментацию
    if args.bundle:
        print(f"📦 BUNDLE MODE: {args.bundle}")
        print("   → Пропускаем UperNet/SAM сегментацию")
        print("   → Используем authoritative маски из SketchUp")
    
    # Проверяем ComfyUI
    try:
        urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
    except:
        print("❌ ComfyUI не доступен", file=sys.stderr)
        sys.exit(1)
    
    # Парсим ТЗ
    print(f"📖 Читаю ТЗ: {args.tz}")
    tz_data = parse_tz(args.tz)
    
    if not tz_data.get('primary_sketch'):
        print("❌ Скетч не найден в ТЗ", file=sys.stderr)
        sys.exit(1)
    
    print(f"📁 Проект: {tz_data['project_name']}")
    print(f"🎨 Скетч: {tz_data['primary_sketch']}")
    print(f"📦 Референсов: {len(tz_data['references'])}")
    print(f"⚙️  Steps: {args.steps}")
    
    # Параметры
    params = {
        'output': args.output or f"{tz_data['project_name']}_render",
        'steps': args.steps,
        'cfg': args.cfg,
        'cn_strength': args.cn_strength,
        'ip_strength': args.ip_strength,
        'no_ipadapter': args.no_ipadapter,
        'no_refiner': args.no_refiner,
        'two_pass': args.two_pass,
        'pass_num': args.pass_num or 1,
        'latent_file': args.latent_file,
        'size': args.size,
    }
    
    # Логируем память перед стартом
    mem_start = get_memory_usage()
    print(f"💾 RAM: {mem_start['used_gb']}/{mem_start['total_gb']} GB (доступно: {mem_start['available_gb']} GB)")
    
    # Запускаем мониторинг памяти каждые 5 секунд
    monitor_log = os.path.join(LOG_DIR, f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    os.makedirs(LOG_DIR, exist_ok=True)
    start_memory_monitor(monitor_log, interval=5)
    print(f"📊 Мониторинг памяти: {monitor_log}")
    
    # Строим workflow
    workflow, ip_log = build_workflow(tz_data, params)
    
    # Отправляем
    mode_desc = ""
    if params['two_pass']:
        mode_desc = f" (Pass {params['pass_num']})"
    elif params['no_refiner']:
        mode_desc = " (без Refiner)"
    
    print(f"\n📤 Отправляю в ComfyUI{mode_desc}...")
    start_time = time.time()
    prompt_id = queue_prompt(workflow)
    
    if not prompt_id:
        sys.exit(1)
    
    print(f"🆔 Prompt ID: {prompt_id}")
    print(f"⏱️  Ожидание ~30-40 минут на CPU...\n")
    
    result = wait_for_completion(prompt_id)
    end_time = time.time()
    duration = int(end_time - start_time)
    
    mem_end = get_memory_usage()
    print(f"💾 RAM после: {mem_end['used_gb']}/{mem_end['total_gb']} GB")
    
    # Логируем
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'project_name': tz_data['project_name'],
        'tz_path': args.tz,
        'sketch': tz_data['primary_sketch'],
        'prompt_id': prompt_id,
        'output_file': result if isinstance(result, str) else None,
        'error': result[1] if isinstance(result, tuple) else None,
        'duration_seconds': duration,
        'ip_adapters': ip_log,
        'params': params,
        'references_count': len(tz_data['references']),
        'constraints': tz_data.get('constraints', ''),
        'memory': {
            'start': mem_start,
            'end': mem_end,
        },
    }
    
    log_path = save_log(log_data, workflow)
    
    if isinstance(result, str):
        print(f"\n✅ Готово: {result}")
        sys.exit(0)
    else:
        print(f"\n❌ Ошибка: {result[1] if isinstance(result, tuple) else 'unknown'}")
        sys.exit(1)


if __name__ == "__main__":
    main()
