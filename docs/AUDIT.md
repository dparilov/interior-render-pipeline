# Audit Guide

> Для внешнего ревью: как проверить pipeline от начала до конца

## TL;DR

1. Открыть `examples/bathroom_01/` — готовый bundle
2. Сравнить `beauty.png` (input) и `render.png` (output)
3. Проверить `depth.png` и `boundary_mask.png` на корректность
4. Запустить `render/render.py` — получить новый эксперимент

## Контрольные точки

### 1. Scene Graph (Phase 0)

**Файл:** `scene_graph.json` в extract zip

**Проверить:**
- Все объекты сцены присутствуют с уникальными PID
- Камера совпадает с текущим видом в SketchUp
- face_count > 0 для объектов с геометрией

```json
{
  "entities": [
    {"pid": 36696, "name": "walls", "face_count": 156},
    {"pid": 43754, "name": "bathtub", "face_count": 892}
  ]
}
```

### 2. Role Map (Phase 1)

**Файл:** `role_map.json`

**Проверить:**
- Каждый PID из ТЗ присутствует
- class корректен (surface/fixture/opening)
- excluded содержит служебные объекты (люди, камеры)

### 3. Masks (Phase 2)

**Папка:** `masks/`

**Проверить визуально:**

| Критерий | Описание | Как проверить |
|----------|----------|---------------|
| Coverage | Маска покрывает весь объект | Наложить на beauty.png |
| Precision | Нет захвата соседей | Сравнить границы |
| Binary | Только чёрный/белый | Гистограмма = 2 пика |
| Alignment | Совпадает с beauty | Pixel-perfect наложение |

**Типичные проблемы:**
- `hollow` — только контур, внутри чёрное (faces не покрашены)
- `leak` — захват соседнего объекта
- `gray` — градиенты вместо бинарной маски

### 4. Depth Map

**Файл:** `depth.png`

**Проверить:**
- Ближние объекты светлее (ванна, тумба)
- Дальние темнее (стены, окно)
- Нет артефактов на границах объектов
- Соответствует реальной геометрии (не угадывание нейросетью)

### 5. Boundary Mask

**Файл:** `boundary_mask.png`

**Проверить:**
- Белый = вся комната
- Чёрный = за пределами стен
- Контур точно по границам геометрии

### 6. Render Output

**Файл:** `render.png`

**Критерии качества:**

| Критерий | Вес | Описание |
|----------|-----|----------|
| Geometry | 40% | Объекты на своих местах, нет лишних |
| Materials | 30% | Материалы соответствуют референсам |
| Lighting | 15% | Естественное освещение |
| Details | 15% | Нет артефактов, резкость |

**Критические ошибки (автоматический FAIL):**
- Объект в неправильном месте
- Лишние объекты (не из ТЗ)
- Генерация за пределами комнаты
- Изменение архитектуры (стены, проёмы)

## Контрольные эксперименты

### Структурные (геометрия)

#### S1: Structural Baseline (Golden Reference)

```
Canny: 0.8, Depth: 0.9 (SketchUp)
Boundary: ON
IPAdapter: OFF
Seed: 42
```

**Ожидание:** Точная геометрия, случайные материалы. Это эталон — если здесь геометрия ломается, проблема в ControlNet.

#### S2: Weak Structure

```
Canny: 0.5, Depth: 0.5
Boundary: OFF
IPAdapter: OFF
Seed: 42
```

**Ожидание:** Модель "додумывает" — покажет где структура слабая.

### Изоляционные (один объект)

#### I1: Floor Only

```
IPAdapter: floor (0.5)
Остальное: OFF
Seed: 42
```

#### I2: Floor Weight Sweep

```
IPAdapter floor: 0.3 / 0.5 / 0.7
Seed: 42 (три прогона)
```

**Ожидание:** Найти оптимальный weight для surfaces.

#### I3: Walls Only

```
IPAdapter: walls (0.5)
Seed: 42
```

#### I4: Vanity Only (fixture)

```
IPAdapter: vanity (0.5)
Seed: 42
```

**Ожидание:** Сравнить поведение surface vs fixture.

### Интеграционные

#### F1: Critical Only

```
IPAdapter: floor, walls, vanity, mirror, bathtub
Weights: 0.5-0.55
Seed: 42
```

#### F2: Full Pipeline

```
IPAdapter: all entities
Weights: per entity class
Seed: 42
```

#### F3: Degradation Test

```
Canny: 0.6, Depth: 0.5
IPAdapter: all (0.5)
Seed: 42
```

**Ожидание:** Больше "творчества", определить порог деградации.

## Воспроизводимость

Для повторения эксперимента:

1. Использовать тот же `bundle`
2. Использовать тот же `seed`
3. Использовать ту же версию ComfyUI и моделей
4. Сравнить `workflow_hash` из `experiment.json`

```bash
python render/experiment.py compare --dir experiments/ exp_1 exp_2
```

## Чек-лист аудита

- [ ] README понятен без дополнительных объяснений
- [ ] QUICKSTART воспроизводим с нуля
- [ ] example bundle содержит все необходимые файлы
- [ ] Masks бинарные и выровнены с beauty
- [ ] Depth map соответствует геометрии
- [ ] Render не выходит за boundary mask
- [ ] Эксперименты логируются с полными параметрами
- [ ] Можно воспроизвести любой предыдущий результат
