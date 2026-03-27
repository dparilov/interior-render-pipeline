# Interior Render Pipeline v1.0-beta

## Спецификация системы рендеринга интерьеров

**Версия:** 1.0-beta
**Дата:** 2026-03-27
**Статус:** В разработке

---

## 1. Обзор системы

### 1.1 Назначение
Система преобразует архитектурные скетчи в фотореалистичные рендеры интерьеров с точным переносом материалов из референсов в указанные зоны изображения.

### 1.2 Входные данные
- **Скетч** — изображение помещения (SketchUp, ручной рисунок, CAD-экспорт)
- **ТЗ** — техническое задание с описанием материалов и референсами
- **Референсы материалов** — фотографии конкретных товаров (плитка, мебель, сантехника)

### 1.3 Выходные данные
- **Рендер** — фотореалистичное изображение 1024×1024+ с применёнными материалами
- **Маски регионов** — бинарные маски каждого элемента
- **Матрица верификации** — confidence scores для каждой маски

---

## 2. Архитектура pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT STAGE                               │
├─────────────────────────────────────────────────────────────────┤
│  Скетч (JPG/PNG)  →  ТЗ (Markdown)  →  Референсы (JPG/PNG)      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SEGMENTATION STAGE                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   UperNet   │ → │    SAM      │ → │   Opus      │          │
│  │ Segmentator │    │  Refinement │    │ Verification │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         ↓                  ↓                  ↓                  │
│  Цветовые маски    Point-prompted      Coverage/Precision       │
│  (Interior Design   маски              Confidence scores        │
│   Segmentator)                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MASK OPTIMIZATION STAGE                       │
├─────────────────────────────────────────────────────────────────┤
│  Морфологические операции (dilate, erode, open, close)          │
│  Итерации: до 10 или пока confidence растёт                     │
│  Выбор лучшего источника: max(UperNet, SAM) для каждого элемента│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RENDER STAGE                                │
├─────────────────────────────────────────────────────────────────┤
│  SDXL + Canny ControlNet + Depth ControlNet                     │
│  + Regional IP-Adapter (маска + референс для каждого элемента)  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    VERIFICATION STAGE                            │
├─────────────────────────────────────────────────────────────────┤
│  Opus анализ рендера по ТЗ → оценка соответствия                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Этап сегментации

### 3.1 UperNet (Interior Design Segmentator)

**Компонент:** `InteriorDesign-for-ComfyUI`
**Модель:** UperNet trained on ADE20K

**Входы:**
- `image`: Скетч помещения
- `control_items`: {window, door, staircase, columns}

**Выходы:**
- `seg_map`: Цветовая карта сегментации (каждый цвет = класс)

**Ограничения:**
- Детерминистичен на одном входе
- Не различает подтипы (tiled wall vs painted wall)
- Control Items влияет только на постобработку, не на сегментацию

**Извлечение масок:**
```python
# Для каждого уникального цвета в seg_map
for color in unique_colors:
    mask = (seg_map == color).astype(uint8) * 255
```

### 3.2 SAM (Segment Anything Model)

**Модель:** `sam_vit_b_01ec64.pth` (ViT-B, 375MB)

**Режим работы:** Point-prompted через SEGS
- Входная маска (UperNet или rect) → MaskToSEGS → SAMDetectorSegmented

**Параметры:**
| Параметр | Значение | Описание |
|----------|----------|----------|
| detection_hint | center-1 | Использовать центр региона как hint |
| threshold | 0.85-0.93 | Порог уверенности SAM |
| bbox_expansion | 10-20 | Расширение bounding box |
| dilation | 0 | Постобработка маски |

**Для элементов без UperNet маски:**
```python
# Создаём rectangular hint mask по координатам центра
mask = create_rect_mask(center_x, center_y, width, height)
```

### 3.3 Исключённые методы

| Метод | Причина исключения |
|-------|-------------------|
| CLIPSeg | Не работает на архитектурных скетчах (обучен на фото) |
| GroundingDINO | Не тестировался, предположительно та же проблема |
| UperNet regeneration | Детерминистичен, параметры не влияют на результат |
| SAM confidence score | Не коррелирует с semantic correctness |
| CLIP similarity | Низкие scores на скетчах (0.2-0.3) |

---

## 4. Верификация масок

### 4.1 Метрики

| Метрика | Формула | Диапазон |
|---------|---------|----------|
| **Coverage** | % площади объекта покрытый маской | 0-100% |
| **Precision** | % маски не залезающей на соседние объекты | 0-100% |
| **Confidence** | (Coverage + Precision) / 2 | 0-100% |

### 4.2 Метод верификации

**Верификатор:** Anthropic Claude (Opus) через Vision API

**Промпт для верификации:**
```
Image 1: Original sketch (reference)
Image 2-N: Binary masks for elements

CRITERIA:
1. COVERAGE (0-100%): What % of the object's area is covered by white pixels?
2. PRECISION (0-100%): What % of white pixels are ONLY on this object?
3. CONFIDENCE = (Coverage + Precision) / 2

OUTPUT FORMAT:
| Element | Coverage | Precision | Confidence | Notes |
```

**Почему Vision LLM, а не IoU:**
- IoU требует ground truth маску (у нас её нет)
- Vision LLM оценивает semantic correctness
- Может давать actionable feedback для улучшения

### 4.3 Порог прохождения

**Target:** 95% confidence

**Реально достижимо на скетчах:** 50-96% (зависит от сложности элемента)

---

## 5. Оптимизация масок

### 5.1 Морфологические операции

| Операция | Эффект | Когда применять |
|----------|--------|-----------------|
| `dilate` | Расширение маски | Coverage < target |
| `erode` | Сужение маски | Precision < target (bleed) |
| `open` | Удаление шума | Мелкие артефакты |
| `close` | Заполнение дыр | Разрывы в маске |

**Параметры:**
- `kernel_size`: 3-15 (размер структурного элемента)
- `iterations`: 1-5 (количество повторений)

### 5.2 Алгоритм итераций

```python
MAX_ITERATIONS = 10
NO_IMPROVEMENT_THRESHOLD = 2

prev_confidence = 0
no_improvement_count = 0

for iteration in range(MAX_ITERATIONS):
    # Применить морфологию
    mask = apply_morphology(mask, operation, kernel, iters)
    
    # Верификация
    confidence = opus_verify(sketch, mask, element_name)
    
    # Проверка условий выхода
    if confidence >= 0.95:
        break  # Достигнут порог
    
    if confidence <= prev_confidence:
        no_improvement_count += 1
        if no_improvement_count >= NO_IMPROVEMENT_THRESHOLD:
            break  # Нет улучшений
    else:
        no_improvement_count = 0
    
    prev_confidence = confidence

# Вернуть маску с максимальным confidence
return best_mask, best_confidence
```

### 5.3 Выбор финальной маски

Для каждого элемента:
```python
final_mask = sam_mask if sam_confidence >= upernet_confidence else upernet_mask
```

---

## 6. Этап рендеринга

### 6.1 Базовая модель

**Checkpoint:** RealVisXL V4.0 (SDXL-based)
**Разрешение:** 1024×1024
**Sampler:** dpmpp_2m_sde + karras
**Steps:** 50
**CFG Scale:** 7.5

### 6.2 ControlNet

| ControlNet | Модель | Strength | End % | Назначение |
|------------|--------|----------|-------|------------|
| Canny | controlnet-canny-sdxl | 0.7 | 80% | Сохранение линий/деталей |
| Depth | controlnet-depth-sdxl | 0.5 | 60% | Сохранение перспективы/формы |

**Depth map:** Генерируется через DepthAnythingV2 (vitl)

### 6.3 IP-Adapter

**Модель:** ip-adapter-plus_sdxl_vit-h.safetensors
**CLIP Vision:** CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors

**Региональное применение:**
```python
IPAdapterAdvanced(
    model=prev_model,
    image=reference_image,      # Фото материала из ТЗ
    weight=0.35-0.6,            # Зависит от критичности
    weight_type="style transfer",
    start_at=0.0,
    end_at=0.6,
    embeds_scaling="V only",
    attn_mask=element_mask      # Бинарная маска региона
)
```

**Веса по элементам:**
| Элемент | Weight | Критичность |
|---------|--------|-------------|
| vanity | 0.6 | КРИТИЧНО |
| wall | 0.5 | КРИТИЧНО |
| floor | 0.5 | КРИТИЧНО |
| towel_warmer | 0.5 | КРИТИЧНО |
| bathtub | 0.4 | Нормально |
| mirror | 0.4 | Нормально |
| faucet | 0.4 | Нормально |
| basket | 0.35 | Нормально |

### 6.4 Генерация промпта

**Из ТЗ автоматически:**
1. Парсинг секций `### Element`
2. Извлечение описаний материалов
3. Перевод ключевых терминов RU→EN
4. Сборка детального промпта (2000+ символов)

**Negative prompt:**
- Исключение неправильных материалов из ТЗ
- Стандартные артефакты (blur, watermark, low quality)

---

## 7. Формат ТЗ

### 7.1 Структура файла

```markdown
# ТЗ: [Название проекта]

## Общее описание
[Текстовое описание стиля, атмосферы, освещения]

## Скетчи
| Ракурс | Файл | Описание |
|--------|------|----------|
| Фронтальный | `скетчи/front.jpg` | Основной вид |

## Материалы и предметы

### [Название элемента]
- **Модель:** [Производитель и модель]
- **Артикул:** [Код товара]
- **Размер:** [Габариты]
- **Описание:** [Детальное описание материала, цвета, текстуры]
- **Референс:** `референсы/filename.jpg`
- **КРИТИЧНО:** ДА/НЕТ

## Ограничения
⛔ **НЕЛЬЗЯ:**
- [Список запрещённых материалов/цветов]

## Стиль рендера
- **Освещение:** [Описание]
- **Атмосфера:** [Описание]
- **Качество:** [Описание]
```

### 7.2 Обязательные поля элемента

| Поле | Обязательно | Используется для |
|------|-------------|------------------|
| Описание | ✅ | Генерация промпта |
| Референс | ✅ | IP-Adapter |
| КРИТИЧНО | ❌ | Вес IP-Adapter |
| Модель/Артикул | ❌ | Документация |

---

## 8. Результаты тестирования

### 8.1 Матрица верификации масок (bathroom_masha)

| Element | UperNet | SAM | Final | Source | Morph Iters |
|---------|---------|-----|-------|--------|-------------|
| mirror | 92.5% | 96.0% | **96.0%** | SAM | 1 |
| basket | 82.5% | 91.5% | **91.5%** | SAM | 1 |
| towel_warmer | — | 87.5% | **87.5%** | SAM | 1 |
| window | — | 79.0% | **79.0%** | SAM | 2 |
| faucet | — | 78.5% | **78.5%** | SAM | 2 |
| floor | 74.0% | 77.5% | **77.5%** | SAM | 1 |
| vanity | 77.5% | 75.0% | **77.5%** | UperNet | 6 |
| bathtub_screen | — | 70.0% | **70.0%** | SAM | 2 |
| wall | 53.0% | 32.5% | **53.0%** | UperNet | 6 |
| bathtub | 52.5% | 37.5% | **52.5%** | UperNet | 6 |

**Средний confidence:** 76.3%
**Всего итераций:** 16 (UperNet: 6, SAM: 10)

### 8.2 Характеристики по типам элементов

| Тип элемента | Лучший метод | Avg Confidence |
|--------------|--------------|----------------|
| Изолированные объекты (mirror, basket) | SAM | 90%+ |
| Крупные простые зоны (floor) | SAM | 77% |
| Сложные составные зоны (wall, bathtub) | UperNet | 53% |
| Мелкие детали (faucet, towel_warmer) | SAM | 78-87% |

---

## 9. Известные ограничения

### 9.1 Сегментация

1. **UperNet не различает подтипы стен** (tiled vs painted) — сливает в один класс
2. **SAM over-segments сложные объекты** (bathtub + wall merged)
3. **Максимальный confidence на скетчах ~96%** — не достигает 100% из-за природы скетчей

### 9.2 Рендеринг

1. **CPU mode медленный** (~40-60 мин vs ~5 мин на GPU)
2. **9 IP-Adapter могут конфликтовать** при высоких весах
3. **Нет гарантии точного переноса текстуры** — IP-Adapter передаёт "стиль", не пиксели

### 9.3 Верификация

1. **Vision LLM субъективен** — разные промпты дают разные scores
2. **Нет ground truth для сравнения** — только экспертная оценка

---

## 10. Зависимости

### 10.1 Python пакеты

```
torch>=2.0
transformers
segment-anything
scipy
Pillow
requests
```

### 10.2 ComfyUI Custom Nodes

```
ComfyUI-Impact-Pack
ComfyUI_IPAdapter_plus
comfyui_controlnet_aux
ComfyUI-DepthAnythingV2
InteriorDesign-for-ComfyUI
```

### 10.3 Модели

| Модель | Размер | Путь |
|--------|--------|------|
| RealVisXL V4.0 | ~6.5GB | models/checkpoints/ |
| controlnet-canny-sdxl | ~2.5GB | models/controlnet/ |
| controlnet-depth-sdxl | ~2.5GB | models/controlnet/ |
| ip-adapter-plus_sdxl_vit-h | 809MB | models/ipadapter/ |
| CLIP-ViT-H-14-laion2B | 2.4GB | models/clip_vision/ |
| sam_vit_b | 375MB | models/sams/ |
| depth_anything_v2_vitl | ~330MB | models/depthanything/ |

---

## 11. API

### 11.1 ComfyUI HTTP API

**Base URL:** `http://127.0.0.1:8188`

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/prompt` | POST | Queue workflow |
| `/queue` | GET | Get queue status |
| `/history/{id}` | GET | Get execution history |
| `/system_stats` | GET | System info |
| `/object_info` | GET | Available nodes |

### 11.2 Workflow JSON

Сохраняется в: `~/.openclaw/workspace/logs/comfyui/v6_{timestamp}.json`

---

## 12. Roadmap

### v1.1 (planned)
- [ ] Интеграция GroundingDINO для text-prompted segmentation
- [ ] Автоматический retry при низком confidence
- [ ] Batch processing multiple views

### v2.0 (future)
- [ ] Inpainting pipeline для точечных исправлений
- [ ] Multi-view consistency
- [ ] Video walkthrough generation

---

## Приложение A: Скрипты

| Скрипт | Назначение |
|--------|------------|
| `comfyui-render-v6.py` | Полный pipeline рендеринга |
| `extract-masks.py` | Извлечение масок из seg_map |
| `verify-masks-opus.py` | Верификация через Opus |
| `sam-segmentation.py` | SAM с point prompts |

---

## Приложение B: Глоссарий

| Термин | Определение |
|--------|-------------|
| **Coverage** | Доля площади объекта, покрытая маской |
| **Precision** | Доля маски, не выходящая за границы объекта |
| **Confidence** | Среднее Coverage и Precision |
| **IP-Adapter** | Метод переноса стиля через attention injection |
| **ControlNet** | Метод условной генерации (Canny, Depth, etc.) |
| **UperNet** | Архитектура для semantic segmentation |
| **SAM** | Segment Anything Model (Meta) |
| **Attention Mask** | Маска для ограничения области применения IP-Adapter |
