# Experiment Plan

> Гипотезы и тесты для улучшения качества рендера

## Текущие гипотезы

### H1: SketchUp Depth > Neural Depth

**Гипотеза:** Depth map из геометрии SketchUp даёт более точное позиционирование объектов, чем DepthAnything/MiDaS.

**Тест:**
- S1: SketchUp depth (0.9)
- S1-neural: DepthAnything depth (0.9)
- Seed: 42, одинаковый bundle

**Метрика:** Отклонение позиций объектов от ground truth (beauty.png)

**Статус:** 🔄 В процессе

---

### H2: Boundary Mask предотвращает генерацию за пределами

**Гипотеза:** Latent mask по boundary_mask.png не даёт модели "додумывать" объекты за стенами.

**Тест:**
- S1: с boundary mask
- S1-no-boundary: без boundary mask
- Seed: 42

**Метрика:** Наличие объектов/структур за пределами комнаты

**Статус:** 📋 Запланировано

---

### H3: Surfaces требуют меньший weight чем Fixtures

**Гипотеза:** Большие плоскости (walls, floor) при высоком weight "размазываются", fixtures (vanity, mirror) держат форму.

**Тест (weight sweep):**
| Entity | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 |
|--------|-----|-----|-----|-----|-----|
| floor  | I2a | I2b | I2c | I2d | I2e |
| vanity | I4a | I4b | I4c | I4d | I4e |

**Метрика:** Соответствие референсу + сохранение структуры

**Статус:** 📋 Запланировано

---

### H4: Canny 0.8 + Depth 0.9 — оптимальный баланс

**Гипотеза:** Ниже — модель "творит", выше — артефакты от переобучения.

**Тест:**
| Canny | Depth | Experiment |
|-------|-------|------------|
| 0.6   | 0.5   | F3         |
| 0.7   | 0.7   | F3b        |
| 0.8   | 0.9   | S1         |
| 0.9   | 1.0   | F3c        |

**Метрика:** Геометрия vs артефакты

**Статус:** 📋 Запланировано

---

### H5: Порядок IPAdapter влияет на результат

**Гипотеза:** Последний IPAdapter в цепочке имеет больший вес.

**Тест:**
- F2-order1: floor → walls → vanity → ...
- F2-order2: vanity → ... → walls → floor

**Метрика:** Какой объект лучше соответствует референсу

**Статус:** 📋 Запланировано

---

## Матрица экспериментов

### Структурные (S)

| ID | Canny | Depth | Boundary | IPAdapter | Цель |
|----|-------|-------|----------|-----------|------|
| S1 | 0.8 | 0.9 (SKP) | ON | OFF | Golden baseline |
| S1-neural | 0.8 | 0.9 (DA) | ON | OFF | Compare depth sources |
| S2 | 0.5 | 0.5 | OFF | OFF | Degradation threshold |

### Изоляционные (I)

| ID | Entity | Weight | Цель |
|----|--------|--------|------|
| I1 | floor | 0.5 | Surface baseline |
| I2a-e | floor | 0.3-0.7 | Weight sweep |
| I3 | walls | 0.5 | Surface comparison |
| I4 | vanity | 0.5 | Fixture baseline |
| I4a-e | vanity | 0.3-0.7 | Fixture weight sweep |

### Интеграционные (F)

| ID | Entities | Weights | Цель |
|----|----------|---------|------|
| F1 | critical only | 0.5-0.55 | Core pipeline |
| F2 | all | per class | Full pipeline |
| F3 | all | 0.5, weak CN | Degradation |

## Приоритеты

1. **S1** — подтвердить что геометрия держится (блокер)
2. **H1** — SketchUp vs Neural depth
3. **H2** — boundary mask работает
4. **I2** — найти оптимальный weight для surfaces
5. **F2** — полный pipeline

## Результаты

| Experiment | Date | Result | Notes |
|------------|------|--------|-------|
| baseline_v1 | 2026-03-29 | ❌ | Душ слева, уступ справа |
| | | | |

## Выводы

_(Заполняется по мере проведения экспериментов)_
