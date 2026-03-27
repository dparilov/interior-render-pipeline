#!/usr/bin/env python3
"""
Постобработка рендера — применение визуальных пресетов.
Работает мгновенно (PIL), без ComfyUI.

Использование:
  python3 comfyui-postprocess.py --input image.png --preset 3
  python3 comfyui-postprocess.py --input image.png --preset "Плёночный"
  python3 comfyui-postprocess.py --list  # показать пресеты
"""

import argparse
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np

# Пресеты постобработки
PRESETS = {
    1: {
        'name_ru': 'Без обработки',
        'name_en': 'None',
        'description': 'Оригинал без изменений',
        'grain': 0,
        'vignette': 0,
        'fade': 0,
        'saturation': 1.0,
        'contrast': 1.0,
        'brightness': 1.0,
        'warmth': 0,
    },
    2: {
        'name_ru': 'Чистый журнальный',
        'name_en': 'Clean Magazine',
        'description': 'Яркий, насыщенный, контрастный — как в глянцевом журнале',
        'grain': 0,
        'vignette': 0,
        'fade': 0,
        'saturation': 1.15,
        'contrast': 1.1,
        'brightness': 1.02,
        'warmth': 5,
    },
    3: {
        'name_ru': 'Мягкий редакционный',
        'name_en': 'Soft Editorial',
        'description': 'Мягкий журнальный стиль, лёгкая виньетка',
        'grain': 0.05,
        'vignette': 0.2,
        'fade': 0,
        'saturation': 1.0,
        'contrast': 0.95,
        'brightness': 1.0,
        'warmth': 0,
    },
    4: {
        'name_ru': 'Плёночный тёплый',
        'name_en': 'Film Analog',
        'description': 'Аналоговая плёнка — зерно, приподнятые тени, тёплые тона',
        'grain': 0.25,
        'vignette': 0.25,
        'fade': 0.1,
        'saturation': 0.9,
        'contrast': 1.0,
        'brightness': 1.0,
        'warmth': 15,
    },
    5: {
        'name_ru': 'Приглушённый скандинавский',
        'name_en': 'Moody Nordic',
        'description': 'Холодный, приглушённый, атмосферный — датский стиль',
        'grain': 0.15,
        'vignette': 0.3,
        'fade': 0.15,
        'saturation': 0.75,
        'contrast': 0.9,
        'brightness': 0.98,
        'warmth': -10,
    },
    6: {
        'name_ru': 'Кинематографичный',
        'name_en': 'Cinematic',
        'description': 'Как кадр из фильма — контрастный, с виньеткой и лёгким зерном',
        'grain': 0.2,
        'vignette': 0.35,
        'fade': 0.1,
        'saturation': 0.85,
        'contrast': 1.15,
        'brightness': 0.98,
        'warmth': -5,
    },
    7: {
        'name_ru': 'Светлый воздушный',
        'name_en': 'Bright & Airy',
        'description': 'Лёгкий, светлый, воздушный — много света, мягкие тени',
        'grain': 0,
        'vignette': 0.1,
        'fade': 0.05,
        'saturation': 0.95,
        'contrast': 0.9,
        'brightness': 1.05,
        'warmth': 10,
    },
}


def list_presets():
    """Выводит список пресетов для пользователя"""
    print("\n🎨 Доступные пресеты постобработки:\n")
    for num, preset in PRESETS.items():
        print(f"  {num}. **{preset['name_ru']}**")
        print(f"     {preset['description']}\n")


def find_preset(query):
    """Находит пресет по номеру или названию"""
    # По номеру
    if isinstance(query, int) or query.isdigit():
        num = int(query)
        if num in PRESETS:
            return PRESETS[num]
    
    # По названию (русскому или английскому)
    query_lower = query.lower()
    for preset in PRESETS.values():
        if query_lower in preset['name_ru'].lower() or query_lower in preset['name_en'].lower():
            return preset
    
    return None


def add_grain(img, intensity):
    """Добавляет зернистость"""
    if intensity <= 0:
        return img
    
    arr = np.array(img).astype(np.float32)
    noise = np.random.normal(0, intensity * 25, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def add_vignette(img, intensity):
    """Добавляет виньетку"""
    if intensity <= 0:
        return img
    
    width, height = img.size
    
    # Создаём градиентную маску
    x = np.linspace(-1, 1, width)
    y = np.linspace(-1, 1, height)
    X, Y = np.meshgrid(x, y)
    
    # Радиальный градиент
    radius = np.sqrt(X**2 + Y**2)
    vignette = 1 - np.clip((radius - 0.7) * intensity * 2, 0, intensity)
    
    # Применяем
    arr = np.array(img).astype(np.float32)
    for i in range(3):
        arr[:, :, i] *= vignette
    
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def add_fade(img, intensity):
    """Приподнимает чёрную точку (плёночный fade)"""
    if intensity <= 0:
        return img
    
    arr = np.array(img).astype(np.float32)
    lift = intensity * 40  # Приподнять чёрный на N уровней
    arr = arr + lift
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def adjust_warmth(img, warmth):
    """Регулирует теплоту (сдвиг в жёлтый/синий)"""
    if warmth == 0:
        return img
    
    arr = np.array(img).astype(np.float32)
    
    if warmth > 0:
        # Теплее: +R, +G (жёлтый), -B
        arr[:, :, 0] = np.clip(arr[:, :, 0] + warmth * 0.5, 0, 255)  # R
        arr[:, :, 1] = np.clip(arr[:, :, 1] + warmth * 0.3, 0, 255)  # G
        arr[:, :, 2] = np.clip(arr[:, :, 2] - warmth * 0.3, 0, 255)  # B
    else:
        # Холоднее: -R, +B
        arr[:, :, 0] = np.clip(arr[:, :, 0] + warmth * 0.5, 0, 255)  # R (warmth отрицательный)
        arr[:, :, 2] = np.clip(arr[:, :, 2] - warmth * 0.4, 0, 255)  # B
    
    return Image.fromarray(arr.astype(np.uint8))


def apply_preset(img, preset):
    """Применяет все эффекты пресета"""
    
    # 1. Яркость
    if preset['brightness'] != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(preset['brightness'])
    
    # 2. Контраст
    if preset['contrast'] != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(preset['contrast'])
    
    # 3. Насыщенность
    if preset['saturation'] != 1.0:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(preset['saturation'])
    
    # 4. Теплота
    img = adjust_warmth(img, preset['warmth'])
    
    # 5. Fade (приподнять чёрный)
    img = add_fade(img, preset['fade'])
    
    # 6. Виньетка
    img = add_vignette(img, preset['vignette'])
    
    # 7. Зерно (последним, чтобы было поверх)
    img = add_grain(img, preset['grain'])
    
    return img


def main():
    parser = argparse.ArgumentParser(description='Постобработка рендера')
    parser.add_argument('--input', '-i', help='Входной файл изображения')
    parser.add_argument('--output', '-o', help='Выходной файл (по умолчанию: input_presetN.png)')
    parser.add_argument('--preset', '-p', help='Номер или название пресета')
    parser.add_argument('--list', '-l', action='store_true', help='Показать список пресетов')
    
    args = parser.parse_args()
    
    if args.list:
        list_presets()
        return
    
    if not args.input:
        print("❌ Укажите входной файл: --input image.png")
        sys.exit(1)
    
    if not args.preset:
        print("❌ Укажите пресет: --preset 3 или --preset 'Плёночный'")
        list_presets()
        sys.exit(1)
    
    # Находим пресет
    preset = find_preset(args.preset)
    if not preset:
        print(f"❌ Пресет не найден: {args.preset}")
        list_presets()
        sys.exit(1)
    
    # Загружаем изображение
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Файл не найден: {input_path}")
        sys.exit(1)
    
    img = Image.open(input_path).convert('RGB')
    print(f"📷 Загружен: {input_path} ({img.size[0]}×{img.size[1]})")
    print(f"🎨 Пресет: {preset['name_ru']} ({preset['name_en']})")
    
    # Применяем пресет
    result = apply_preset(img, preset)
    
    # Сохраняем
    if args.output:
        output_path = Path(args.output)
    else:
        # Автоматическое имя: image_preset3.png
        preset_num = [k for k, v in PRESETS.items() if v == preset][0]
        output_path = input_path.parent / f"{input_path.stem}_preset{preset_num}{input_path.suffix}"
    
    result.save(output_path, quality=95)
    print(f"✅ Сохранён: {output_path}")


if __name__ == "__main__":
    main()
