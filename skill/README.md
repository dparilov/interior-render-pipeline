# ComfyUI Interior Render Skill

**Автоматизированная генерация фотореалистичных интерьерных рендеров с точной сегментацией регионов и переносом материалов.**

**Версия:** 1.0-beta
**Дата:** 2026-03-27

---

## Обзор

Skill для агентов OpenClaw, который превращает архитектурные скетчи в фотореалистичные интерьерные визуализации. Использует двухэтапную сегментацию (UperNet + SAM) с верификацией через Vision LLM и региональный IP-Adapter для точного переноса материалов в каждую зону.

### Ключевые возможности (v1.0-beta)

- 🎯 **Региональный IP-Adapter** — каждый элемент получает свою маску и референс материала
- 🔍 **Двухэтапная сегментация** — UperNet для базовых масок + SAM для рефайнмента
- 🤖 **AI верификация масок** — Opus оценивает Coverage/Precision каждой маски
- 🔄 **Итеративная оптимизация** — морфологические операции до достижения порога
- 📐 **Dual ControlNet** — Canny (детали) + Depth (перспектива)
- 📋 **Структурированный ТЗ** — парсинг Markdown с референсами
- 📊 **Матрица верификации** — confidence scores для каждого региона

### Что нового в beta (vs alpha)

| Компонент | Alpha | Beta |
|-----------|-------|------|
| Сегментация | Нет (глобальный IP-Adapter) | UperNet + SAM с масками |
| IP-Adapter | Один для всех референсов | Региональный (маска на элемент) |
| ControlNet | Только Canny | Canny + Depth |
| Верификация | Ручная | Автоматическая через Opus |
| Оптимизация масок | Нет | Морфология до 10 итераций |

---

## Архитектура Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT STAGE                               │
│  Скетч (JPG/PNG) + ТЗ (Markdown) + Референсы материалов         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  SEGMENTATION STAGE                              │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   UperNet    │────────►│   Извлечение │                      │
│  │ (Interior    │         │   масок по   │                      │
│  │  Design)     │         │   цветам     │                      │
│  └──────────────┘         └──────┬───────┘                      │
│                                  │                               │
│                                  ▼                               │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │     SAM      │◄────────│  Point hints │                      │
│  │  Refinement  │         │  (UperNet/   │                      │
│  │              │         │   coords)    │                      │
│  └──────────────┘         └──────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 VERIFICATION STAGE                               │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │    Opus      │────────►│  Coverage +  │                      │
│  │   Vision     │         │  Precision   │                      │
│  │   Analysis   │         │  = Confidence│                      │
│  └──────────────┘         └──────┬───────┘                      │
│                                  │                               │
│                                  ▼                               │
│  ┌──────────────────────────────────────────┐                   │
│  │  Морфология (до 10 итераций):            │                   │
│  │  dilate/erode/open/close                  │                   │
│  │  Выход: confidence ≥95% ИЛИ plateau       │                   │
│  └──────────────────────────────────────────┘                   │
│                                  │                               │
│                                  ▼                               │
│  ┌──────────────────────────────────────────┐                   │
│  │  Выбор лучшего: max(UperNet, SAM)        │                   │
│  │  для каждого элемента                     │                   │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RENDER STAGE                                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  SDXL (RealVisXL V4.0)                                 │     │
│  │    + ControlNet Canny (структура)                      │     │
│  │    + ControlNet Depth (перспектива)                    │     │
│  │    + Regional IP-Adapter × N (материал → маска)        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  OUTPUT: Фотореалистичный рендер                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Этап 1: Сегментация

### UperNet (Interior Design Segmentator)

**Назначение:** Базовая semantic segmentation архитектурных элементов.

**Модель:** UperNet обученный на ADE20K (150 классов интерьера).

**Как работает:**
1. Скетч → Interior Design Segmentator
2. Выход: цветовая карта (seg_map) где каждый цвет = класс
3. Извлечение бинарных масок по уникальным цветам

**Ограничения:**
- Не различает подтипы (tiled wall vs painted wall)
- Детерминистичен (параметры control_items не влияют на результат)
- Некоторые элементы сливаются (bathtub + wall в одном цвете)

### SAM (Segment Anything Model)

**Назначение:** Рефайнмент масок через point-prompted segmentation.

**Модель:** sam_vit_b (375MB)

**Как работает:**
1. Входная маска (UperNet или rect) → MaskToSEGS
2. SAMDetectorSegmented с detection_hint="center-1"
3. Выход: уточнённая маска с чёткими границами

**Параметры:**
| Параметр | Значение | Описание |
|----------|----------|----------|
| threshold | 0.85-0.93 | Порог уверенности |
| bbox_expansion | 10-20 | Расширение bounding box |
| detection_hint | center-1 | Использовать центр как hint |

**Для элементов без UperNet маски:**
```python
# Создание rect hint по координатам центра объекта
mask = create_rect_mask(center_x, center_y, width, height)
```

---

## Этап 2: Верификация масок

### Метрики

| Метрика | Формула | Описание |
|---------|---------|----------|
| **Coverage** | % объекта под маской | Полнота покрытия |
| **Precision** | % маски на объекте | Точность границ |
| **Confidence** | (Coverage + Precision) / 2 | Итоговый score |

### Верификатор

**Модель:** Anthropic Claude (Opus) через Vision API

**Промпт:**
```
Image 1: Original sketch
Image 2-N: Binary masks

CRITERIA:
1. COVERAGE: % of object area covered by white pixels
2. PRECISION: % of white pixels ONLY on this object
3. CONFIDENCE = (Coverage + Precision) / 2

OUTPUT: Table with scores for each element
```

### Оптимизация

**Морфологические операции:**
| Операция | Эффект | Когда применять |
|----------|--------|-----------------|
| dilate | Расширение | Coverage низкий |
| erode | Сужение | Precision низкий (bleed) |
| open | Удаление шума | Артефакты |
| close | Заполнение дыр | Разрывы |

**Алгоритм итераций:**
```
MAX_ITERATIONS = 10
NO_IMPROVEMENT = 2 подряд

while iterations < MAX and improving:
    mask = apply_morphology(mask)
    confidence = opus_verify(mask)
    if confidence >= 95%: break
    if no improvement 2x: break

final_mask = best_iteration_mask
```

### Выбор финальной маски

```python
for element in elements:
    if sam_confidence >= upernet_confidence:
        use sam_mask
    else:
        use upernet_mask
```

---

## Этап 3: Рендеринг

### Базовая модель

| Параметр | Значение |
|----------|----------|
| Checkpoint | RealVisXL V4.0 |
| Resolution | 1024×1024 |
| Sampler | dpmpp_2m_sde + karras |
| Steps | 50 |
| CFG | 7.5 |

### ControlNet (Dual)

| ControlNet | Strength | End % | Назначение |
|------------|----------|-------|------------|
| Canny | 0.7 | 80% | Сохранение линий/деталей |
| Depth | 0.5 | 60% | Сохранение перспективы |

**Depth map:** Генерируется через DepthAnythingV2 (vitl).

### Regional IP-Adapter

**Модель:** ip-adapter-plus_sdxl_vit-h
**CLIP Vision:** CLIP-ViT-H-14-laion2B

**Для каждого элемента:**
```python
IPAdapterAdvanced(
    model=prev_model,
    image=reference_image,    # Фото материала из ТЗ
    weight=0.35-0.6,          # По критичности
    weight_type="style transfer",
    start_at=0.0,
    end_at=0.6,
    embeds_scaling="V only",
    attn_mask=element_mask    # Бинарная маска региона
)
```

**Веса по элементам:**
| Элемент | Weight | Критичность |
|---------|--------|-------------|
| vanity | 0.6 | КРИТИЧНО |
| wall | 0.5 | КРИТИЧНО |
| floor | 0.5 | КРИТИЧНО |
| towel_warmer | 0.5 | КРИТИЧНО |
| mirror, bathtub, faucet | 0.4 | Нормально |
| basket | 0.35 | Нормально |

---

## Результаты тестирования

### Матрица верификации (bathroom_masha)

| Element | UperNet | SAM | Final | Source |
|---------|---------|-----|-------|--------|
| mirror | 92.5% | 96.0% | **96.0%** | SAM |
| basket | 82.5% | 91.5% | **91.5%** | SAM |
| towel_warmer | — | 87.5% | **87.5%** | SAM |
| window | — | 79.0% | **79.0%** | SAM |
| faucet | — | 78.5% | **78.5%** | SAM |
| floor | 74.0% | 77.5% | **77.5%** | SAM |
| vanity | 77.5% | 75.0% | **77.5%** | UperNet |
| bathtub_screen | — | 70.0% | **70.0%** | SAM |
| wall | 53.0% | 32.5% | **53.0%** | UperNet |
| bathtub | 52.5% | 37.5% | **52.5%** | UperNet |

**Средний confidence:** 76.3%
**Итераций:** 16 (UperNet: 6, SAM: 10)

### Выводы по методам

| Тип элемента | Лучший метод | Avg Confidence |
|--------------|--------------|----------------|
| Изолированные (mirror, basket) | SAM | 90%+ |
| Мелкие детали (faucet) | SAM | 78% |
| Сложные составные (wall, bathtub) | UperNet | 53% |

---

## Исключённые подходы

### 1. CLIPSeg (text-prompted segmentation)

**Почему пробовали:** Сегментация по текстовому описанию ("white tiled wall").

**Почему не подошёл:**
- Обучен на фотографиях, не на архитектурных скетчах
- На скетчах давал 0-3% coverage
- Путал объекты (выделял раковину вместо ванны)

**Тест:**
```
CLIPSeg "white tiled bathroom wall" → 0% coverage
CLIPSeg "white bathtub" → выделил раковину
CLIPSeg "blue floor tiles" → 2.8% coverage
```

### 2. UperNet перегенерация

**Почему пробовали:** Изменение параметров Control Items для улучшения сегментации.

**Почему не подошёл:**
- UperNet детерминистичен на одном входе
- Изменение window/door/columns не влияет на результат
- 3 варианта дали идентичные seg_map

### 3. SAM confidence score

**Почему пробовали:** Использовать внутренний score SAM (0.85-0.99) как метрику качества.

**Почему не подошёл:**
- Не коррелирует с semantic correctness
- bathtub: SAM score 0.99, но Opus confidence 52% (неправильная область)
- Показывает "уверенность в сегментации", не "правильность"

### 4. CLIP similarity

**Почему пробовали:** Сравнение crop региона с текстовым описанием через CLIP.

**Почему не подошёл:**
- На скетчах все scores низкие (0.21-0.31)
- CLIP обучен на фото, не на абстрактных рисунках
- Не различает качество масок

### 5. Глобальный IP-Adapter (Alpha)

**Почему пробовали:** Один IP-Adapter на все референсы без масок.

**Почему не подошёл:**
- IP-Adapter применяется ко ВСЕМУ изображению
- Цвета/текстуры смешиваются
- Результат: абстрактный шум вместо интерьера

**Решение:** Regional IP-Adapter с attention masks.

---

## Зависимости

### Python пакеты

```
torch>=2.0
transformers
segment-anything
scipy
Pillow
requests
```

### ComfyUI Custom Nodes

```
ComfyUI-Impact-Pack       # SAM, SEGS
ComfyUI_IPAdapter_plus    # IP-Adapter
comfyui_controlnet_aux    # ControlNet preprocessors
ComfyUI-DepthAnythingV2   # Depth estimation
InteriorDesign-for-ComfyUI # UperNet segmentator
```

### Модели

| Модель | Размер |
|--------|--------|
| RealVisXL V4.0 | 6.5GB |
| controlnet-canny-sdxl | 2.5GB |
| controlnet-depth-sdxl | 2.5GB |
| ip-adapter-plus_sdxl_vit-h | 809MB |
| CLIP-ViT-H-14-laion2B | 2.4GB |
| sam_vit_b | 375MB |
| depth_anything_v2_vitl | 330MB |

**Всего:** ~15GB моделей

---

## Использование

### Подготовка ТЗ

```
~/ComfyUI/input/project_name/
├── ТЗ.md
├── скетчи/
│   └── front.jpg
└── референсы/
    ├── floor_tiles.jpg
    ├── wall_tiles.png
    ├── vanity.jpg
    └── ...
```

### Запуск

```bash
cd ~/ComfyUI && source venv/bin/activate

# GPU
python main.py --listen --port 8188

# CPU
python main.py --listen --port 8188 --cpu

# Рендер
python ~/.openclaw/workspace/ops/comfyui-render-v6.py
```

### Время генерации

| Режим | Время |
|-------|-------|
| GPU (RTX 3080) | 5-10 мин |
| CPU (Ryzen 7) | 40-60 мин |

---

## Roadmap

### v1.1 (planned)
- [ ] Автоматический retry при низком confidence
- [ ] GroundingDINO для text-prompted segmentation
- [ ] Batch processing multiple views

### v2.0 (future)
- [ ] Inpainting pipeline для точечных исправлений
- [ ] Multi-view consistency
- [ ] Video walkthrough generation

---

## Лицензия

MIT

---

## Авторы

OpenClaw Community
