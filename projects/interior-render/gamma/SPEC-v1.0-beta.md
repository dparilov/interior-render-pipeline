# IRP Gamma — Interior Render Pipeline v1.0-beta

> **Статус:** Research MVP, отладка flow
> **Дата:** 2026-03-29
> **Автор:** AI Assistant + Dmitrii Parilov

---

## 1. Обзор

IRP Gamma — полуавтоматический pipeline для генерации фотореалистичных интерьерных рендеров из SketchUp моделей с точным контролем материалов через референсы.

### Цели
- **Точность:** ~100% соответствие ТЗ по материалам и расположению
- **Воспроизводимость:** детерминированный pipeline без "угадывания"
- **Контроль:** каждый шаг верифицируется, возможен откат

### Ключевое отличие от предыдущих версий
- **Alpha/Beta:** сегментация из растра (UperNet/SAM) → 76% avg confidence
- **Gamma:** authoritative маски из SketchUp → 89.4% avg confidence (target: 100%)

---

## 2. Входные данные

### 2.1 ТЗ (Техническое задание)

**Формат:** Markdown файл

**Структура ТЗ:**

```markdown
# ТЗ — [Название проекта]

## Общие параметры
- **Тип помещения:** ванная комната / кухня / гостиная
- **Стиль:** современный / классический / скандинавский
- **Освещение:** естественное дневное / вечернее тёплое
- **Ракурс:** фронтальный / угловой / сверху

## Объекты

### [Название объекта]
- **Тип:** surface / fixture / opening
- **Артикул:** [если есть]
- **Производитель:** [если есть]
- **Размеры:** [если важно]
- **Материал:** [описание текстуры, цвета]
- **Фактура:** глянцевая / матовая / рельефная
- **КРИТИЧНО:** ДА / НЕТ

## Референс освещения
[Опционально: фото желаемой атмосферы]

## Негативные промпты
- Что НЕ должно быть на рендере
```

**Пример объекта:**

```markdown
### Напольная плитка
- **Тип:** surface
- **Артикул:** Equipe Rivoli Bergen Azul (30725)
- **Размеры:** 200×200 мм
- **Материал:** керамогранит
- **Фактура:** матовая с геометрическим узором
- **Цвет:** тёмно-синий с белым паттерном
- **КРИТИЧНО:** ДА
```

### 2.2 Референсы

**Папка:** `references/`

**Формат:** JPG/PNG, желательно 512×512 или больше

**Именование:** `[role].jpg` или `[role]_[variant].jpg`

**Примеры:**
- `floor_tiles.jpg` — плитка пола
- `wall_tiles.png` — настенная плитка
- `vanity.jpg` — тумба
- `bathtub.jpg` — ванна
- `faucet.jpg` — смеситель
- `mirror.jpg` — зеркало

### 2.3 SKP модель

**Требования к модели:**

| Требование | Описание |
|------------|----------|
| Именование | Компоненты с узнаваемыми именами (Bathtub_classic, Mirror, etc.) |
| Группировка | Каждый объект — отдельный Group или Component |
| Материалы | Привязаны к faces (для верификации) |
| Сцены | Минимум одна Scene с настроенной камерой |

**⚠️ Известные проблемы:**
- Безымянные Groups (пустое имя) → требуют ручного маппинга
- Вложенные объекты (faucet внутри vanity) → требуют рекурсивного extract
- Sumele (человеческая фигура) → исключать из рендера

---

## 3. Pipeline — детальный flow

### PHASE 0: Scene Graph Extraction

**Скрипт:** `irp_extract.rb`
**Расположение:** `http://100.96.1.25:9090/irp_extract.rb`

**Входы:**
- Открытый SKP файл в SketchUp

**Выходы:**
- `scene_graph.json` — полный граф сцены
- `beauty.png` — рендер активной Scene

**Команды в Ruby Console:**

```ruby
load 'C:/Users/paril/Downloads/irp_extract.rb'
IRP.extract
```

**Структура scene_graph.json:**

```json
{
  "version": "gamma",
  "model_name": "bathroom.skp",
  "camera": {
    "eye": [x, y, z],
    "target": [x, y, z],
    "up": [x, y, z],
    "fov": 35
  },
  "resolution": [1920, 1080],
  "entities": [
    {
      "pid": 36696,
      "type": "Group",
      "name": "",
      "depth": 0,
      "face_count": 47,
      "child_count": 0,
      "bounds": {
        "width": 2549,
        "height": 3500,
        "depth": 2143
      },
      "position": [x, y, z],
      "volume": 19123456,
      "world_transform": [[...], [...], [...], [...]]
    }
  ]
}
```

**Полнота extract:**
- Рекурсивный обход до 20 уровней
- face_count, child_count для каждого entity
- World transform matrix
- Volume (bounding box)

---

### PHASE 1: Intelligent Mapping (Opus Vision)

**Исполнитель:** Claude Opus с vision

**Входы:**
- `scene_graph.json`
- `beauty.png`
- ТЗ (markdown)
- Референсы (images)

**Процесс:**

1. **Анализ scene_graph:**
   - Идентификация компонентов по именам (Bathtub_classic → bathtub)
   - Идентификация групп по размерам и позиции
   - Исключение служебных объектов (Sumele)

2. **Визуальный анализ beauty.png:**
   - Сопоставление объектов с ТЗ
   - Определение позиций

3. **Генерация role_map.json:**

```json
{
  "version": "gamma",
  "mappings": [
    {
      "pid": 36696,
      "role": "walls",
      "type": "surface",
      "confidence": 0.95,
      "reasoning": "Largest group, contains wall materials"
    },
    {
      "pid": 43754,
      "role": "bathtub",
      "type": "fixture",
      "confidence": 1.0,
      "reasoning": "Component named 'Bathtub classic'"
    }
  ],
  "excluded": [
    {
      "pid": 27700,
      "reason": "Human figure (Sumele) for scale"
    }
  ]
}
```

**Критерии маппинга:**

| Источник | Приоритет | Confidence |
|----------|-----------|------------|
| Имя компонента совпадает с ТЗ | 1 | 1.0 |
| Размеры/позиция однозначны | 2 | 0.9-0.95 |
| Визуальный анализ | 3 | 0.7-0.9 |

---

### PHASE 2: Mask Export

**Скрипт:** `irp_export.rb`
**Расположение:** `http://100.96.1.25:9090/irp_export.rb`

**Входы:**
- `role_map.json`
- Открытый SKP файл

**Выходы:**
- `masks/*.png` — бинарные маски (белый объект на чёрном фоне)
- `manifest.json` — метаданные
- `beauty.png`, `surfaces_only.png`, `fixtures_only.png`
- `model.dae`, `model.fbx`, `model.glb` — для Blender

**Команды:**

```ruby
load 'C:/Users/paril/Downloads/irp_export.rb'
IRP.load_map('C:/Users/paril/Downloads/irp_bundle/role_map.json')
IRP.export
```

**Алгоритм генерации масок:**

```
1. Сохранить состояние видимости всех объектов
2. Для каждого объекта из role_map:
   a. Скрыть ВСЕ объекты
   b. Показать ТОЛЬКО целевой объект
   c. Покрасить все faces целевого объекта в белый
   d. Установить чёрный фон
   e. Рендер в masks/{role}.png
   f. Восстановить материалы
3. Восстановить видимость
4. Экспортировать DAE/FBX/GLB с именами IRP_{role}
5. Сгенерировать manifest.json
```

**⚠️ Критично: Окклюзия**

Маски должны учитывать окклюзию — объекты впереди "вырезают" дырки:
```
1. Показать ВСЕ объекты
2. Целевой объект → белый материал
3. ВСЕ остальные объекты → чёрный материал
4. Рендер → объекты впереди создают правильные вырезы
```

**Именование в экспорте:**

Перед экспортом DAE/FBX/GLB объекты переименовываются:
```ruby
entity.name = "IRP_#{role}"  # walls → IRP_walls
```

Это позволяет Blender находить объекты по имени.

---

### PHASE 3: Visual QA (Scoring)

**Исполнитель:** Claude Opus с vision

**Входы:**
- `masks/*.png`
- `beauty.png`
- ТЗ

**Метрики:**

| Метрика | Описание | Вес |
|---------|----------|-----|
| Coverage | % площади объекта покрытый маской | 40% |
| Precision | Маска не залезает на соседние объекты | 40% |
| Binary | Чистый белый/чёрный без градиентов | 10% |
| Alignment | Совпадение с beauty по пикселям | 10% |

**Scoring formula:**
```
Score = Coverage×0.4 + Precision×0.4 + Binary×0.1 + Alignment×0.1
```

**Scoring matrix (пример):**

| Объект | Coverage | Precision | Binary | Align | **Score** |
|--------|----------|-----------|--------|-------|-----------|
| walls | 95 | 75 | 80 | 90 | **85** |
| floor | 100 | 95 | 95 | 98 | **97** |
| bathtub | 80 | 70 | 70 | 80 | **75** |
| mirror | 100 | 98 | 100 | 99 | **99** |

**Известные проблемы (из текущего bundle):**

| Объект | Score | Проблема |
|--------|-------|----------|
| window | 67 | Маска hollow (только рамка, пусто внутри) |
| bathtub | 75 | Содержит toilet, градиенты |
| walls | 85 | Gray tones вместо pure white |

**Порог прохождения:** Score ≥ 95 для всех объектов

---

### PHASE 4: Blender Verification (Optional)

**Цель:** Альтернативный headless pipeline для автоматизации

**Входы:**
- `model.dae` — содержит камеру
- `model.glb` — содержит геометрию с именами IRP_*

**Скрипт:** `blender_gamma_export.py`

**Ограничения:**

| Проблема | Причина | Решение |
|----------|---------|---------|
| walls/floor NOT FOUND | Безымянные Groups экспортируются как EMPTY | Конвертировать Groups → Components |
| Камера не совпадает | GLB не содержит камеры | Извлечь из DAE |
| 8/10 объектов | 2 объекта теряют mesh | Использовать SketchUp маски |

**Вывод:** SketchUp pipeline надёжнее (10/10 vs 8/10). Blender — fallback для headless.

---

## 4. ComfyUI Rendering

### 4.1 Архитектура workflow

```
                    ┌─────────────────┐
                    │   checkpoint    │
                    │  RealVisXL V4.0 │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ IPAdapter     │    │ IPAdapter     │    │ IPAdapter     │
│ floor         │    │ walls         │    │ bathtub       │
│ + attn_mask   │    │ + attn_mask   │    │ + attn_mask   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ↓
                    ┌─────────────────┐
                    │  ControlNet     │
                    │  Canny + Depth  │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │    KSampler     │
                    │    50 steps     │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  SDXL Refiner   │
                    │   12 steps      │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   VAE Decode    │
                    │   Save Image    │
                    └─────────────────┘
```

### 4.2 IPAdapter с Attention Masks

**🔴 КРИТИЧЕСКИЙ ВЫВОД:**
> 9 IP-Adapter'ов последовательно ПОРТЯТ генерацию!
> Каждый модифицирует уже изменённую модель, эффекты накапливаются.

**Правильный способ:**

```json
{
  "load_floor_mask": {
    "class_type": "LoadImageMask",
    "inputs": {
      "image": "masks/floor.png",
      "channel": "red"
    }
  },
  "apply_ipadapter_floor": {
    "class_type": "IPAdapterAdvanced",
    "inputs": {
      "model": ["checkpoint", 0],
      "ipadapter": ["ipadapter_model", 0],
      "image": ["load_floor_ref", 0],
      "weight": 0.5,
      "weight_type": "ease in-out",
      "combine_embeds": "concat",
      "embeds_scaling": "V only",
      "start_at": 0.0,
      "end_at": 0.9,
      "attn_mask": ["load_floor_mask", 0]
    }
  }
}
```

**Параметры:**

| Параметр | Значение | Примечание |
|----------|----------|------------|
| weight | 0.3-0.5 | При 10 зонах — ниже! |
| weight_type | "ease in-out" | Плавное применение |
| combine_embeds | "concat" | Конкатенация эмбеддингов |
| embeds_scaling | "V only" | Только Value в attention |
| LoadImageMask | channel: "red" | Маска как MASK, не IMAGE! |

### 4.3 ControlNet

**Dual ControlNet (рекомендуется):**

| ControlNet | Strength | End % | Назначение |
|------------|----------|-------|------------|
| Canny | 0.6-0.7 | 0.85 | Контуры, edges |
| Depth | 0.4-0.5 | 0.6 | Перспектива, глубина |

**Canny preprocessing:**
```json
{
  "class_type": "Canny",
  "inputs": {
    "image": ["load_beauty", 0],
    "low_threshold": 0.1,
    "high_threshold": 0.4
  }
}
```

### 4.4 Refiner

**Двухпроходный рендер:**

| Pass | Model | Steps | Denoise |
|------|-------|-------|---------|
| 1 | RealVisXL V4.0 | 50 | 1.0 |
| 2 | SDXL Refiner 1.0 | 12 | 0.3 |

**RAM Management:**
- Refiner требует ~6GB дополнительно
- `--disable-smart-memory` выгружает модели после использования
- Последовательный запуск: Pass1 → выгрузить → Pass2

### 4.5 Послойный Inpainting (альтернатива)

Если 10 IPAdapter не помещаются в RAM:

```
Pass 1: Base render (Canny + общий prompt)
        ↓
Pass 2: Inpaint floor (mask_floor + floor_ref)
        ↓
Pass 3: Inpaint walls (mask_walls + wall_ref)
        ↓
... (по очереди для каждой зоны)
```

**Преимущества:**
- Каждый шаг выгружает модели
- Можно итерировать отдельные зоны
- RAM не накапливается

---

## 5. Модели и зависимости

### 5.1 Checkpoints

| Модель | Размер | Назначение |
|--------|--------|------------|
| RealVisXL_V4.0.safetensors | 6.5GB | Base SDXL |
| sd_xl_refiner_1.0.safetensors | 5.7GB | Refiner |

### 5.2 ControlNet

| Модель | Размер |
|--------|--------|
| controlnet-canny-sdxl.safetensors | 2.4GB |
| controlnet-depth-sdxl.safetensors | 2.4GB |

### 5.3 IP-Adapter

| Модель | Размер | Примечание |
|--------|--------|------------|
| ip-adapter_sdxl.safetensors | 671MB | Стандартный |
| ip-adapter-plus_sdxl_vit-h.safetensors | 98MB | Plus версия |

### 5.4 CLIP Vision

| Модель | Размер | Для какого IP-Adapter |
|--------|--------|----------------------|
| clip_vision_g.safetensors | 2.4GB | ip-adapter_sdxl |
| CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors | 3.5GB | ip-adapter_sdxl |
| CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors | 2.5GB | ip-adapter-plus |

### 5.5 ComfyUI Custom Nodes

```
~/ComfyUI/custom_nodes/
├── ComfyUI_IPAdapter_plus/      # IPAdapterAdvanced с attn_mask
├── comfyui_controlnet_aux/      # Canny/Depth preprocessing
├── ComfyUI-DepthAnythingV2/     # Depth estimation
├── ComfyUI-Impact-Pack/         # SAM segmentation
└── InteriorDesign-for-ComfyUI/  # StableDesign port
```

---

## 6. Скрипты и пути

### 6.1 SketchUp скрипты

| Скрипт | Путь | HTTP |
|--------|------|------|
| irp_extract.rb | `~/.openclaw/workspace/projects/interior-render/gamma/scripts/` | `http://100.96.1.25:9090/irp_extract.rb` |
| irp_export.rb | `~/.openclaw/workspace/projects/interior-render/gamma/scripts/` | `http://100.96.1.25:9090/irp_export.rb` |

### 6.2 ComfyUI пути

| Назначение | Путь |
|------------|------|
| Input | `~/ComfyUI/input/irp_gamma/` |
| Output | `~/ComfyUI/output/` |
| Models | `~/ComfyUI/models/` |

### 6.3 Blender скрипты

| Скрипт | Путь |
|--------|------|
| blender_gamma_export.py | `~/sketchup-share/blender_gamma_export.py` |
| blender_gamma_export_v2.py | `~/sketchup-share/blender_gamma_export_v2.py` |
| blender_gamma_export_v3.py | `~/sketchup-share/blender_gamma_export_v3.py` |

---

## 7. Hardcoded значения (Research MVP)

> ⚠️ Это research MVP — hardcoded значения для текущего bundle

### 7.1 PID → Role mapping

```ruby
ROLE_MAP = {
  36696 => { name: 'walls', type: 'surface' },
  36828 => { name: 'floor', type: 'surface' },
  43754 => { name: 'bathtub', type: 'fixture' },
  124416 => { name: 'vanity', type: 'fixture' },
  143585 => { name: 'shower', type: 'fixture' },
  229917 => { name: 'rainshower', type: 'fixture' },
  352872 => { name: 'towel_warmer', type: 'fixture' },
  359764 => { name: 'window', type: 'fixture' },
  424271 => { name: 'basket', type: 'fixture' },
  471300 => { name: 'mirror', type: 'fixture' }
}

EXCLUDED = [27700]  # Sumele (человек)
```

### 7.2 Resolution

```ruby
RESOLUTION = [1920, 1080]
SCENE_NAME = "Сцена №1"
```

### 7.3 IP-Adapter weights

```python
WEIGHTS = {
    'surface': 0.6,   # walls, floor
    'fixture': 0.5,   # bathtub, vanity, etc.
    'small': 0.4      # faucet, towel_warmer
}
```

---

## 8. Известные ограничения

| Ограничение | Причина | Workaround |
|-------------|---------|------------|
| Безымянные Groups | SketchUp не требует имена | Маппинг по PID |
| Walls/floor в Blender | Groups экспортируются как EMPTY | Использовать SketchUp маски |
| Камера в GLB | GLB не содержит камеры | Извлечь из DAE |
| RAM при 10 IPAdapter | Накопление в памяти | Послойный inpainting |
| CPU рендер медленный | Нет NVIDIA GPU | ~2 мин/step |

---

## 9. Версии и история

| Версия | Дата | Изменения |
|--------|------|-----------|
| Alpha | 2026-03-26 | UperNet/SAM сегментация, 76% confidence |
| Beta | 2026-03-27 | Scene Bundle из SketchUp, 85% confidence |
| Gamma | 2026-03-29 | Полный pipeline с PID маппингом, 89.4% confidence |

---

## 10. TODO

- [ ] Исправить window.png (hollow mask)
- [ ] Исправить bathtub.png (toilet leak)
- [ ] Исправить walls.png (gray tones)
- [ ] Workflow с 10 IPAdapter + attn_mask
- [ ] Тест послойного inpainting
- [ ] Автоматизация Phase 1 (LLM → role_map.json)
- [ ] Документация для Маши (подготовка моделей)

---

## Appendix A: Полный workflow JSON

См. `~/ComfyUI/input/irp_gamma/workflow_10zones.json`

## Appendix B: Scoring Matrix текущего bundle

| Объект | Score | Coverage | Precision | Binary | Alignment | Issues |
|--------|-------|----------|-----------|--------|-----------|--------|
| walls | 85 | 90 | 75 | 80 | 95 | gray tones |
| floor | 97 | 100 | 95 | 95 | 98 | OK |
| bathtub | 75 | 80 | 70 | 70 | 80 | toilet leak |
| vanity | 96 | 98 | 95 | 95 | 96 | OK |
| shower | 94 | 95 | 93 | 94 | 94 | OK |
| rainshower | 97 | 98 | 97 | 96 | 97 | OK |
| towel_warmer | 90 | 92 | 88 | 90 | 90 | banding |
| window | 67 | 50 | 80 | 70 | 68 | hollow |
| basket | 94 | 95 | 93 | 94 | 94 | OK |
| mirror | 99 | 100 | 98 | 100 | 98 | OK |
| **Avg** | **89.4** | | | | | |
