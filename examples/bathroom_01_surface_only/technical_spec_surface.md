# Technical Specification: Surface-Only Experiment

Derived from: `bathroom_01/technical_spec.md`
Scope: **Surfaces and preserved geometry only**

---

## Included Surfaces

### Напольная плитка (floor)

- **Модель:** Equipe Rivoli Bergen Azul
- **Артикул:** 30725
- **Размер:** 200×200 мм
- **Описание:** Керамическая плитка — СИНИЙ фон с БЕЛЫМ геометрическим узором (пересекающиеся круги/лепестки). Средиземноморский стиль.
- **Референс:** `references/floor_tiles.jpg`
- **КРИТИЧНО:** ДА

**Acceptance Criteria:**
- Pattern matches reference (recognizable Rivoli Bergen)
- Blue color with white geometric overlay
- Grout lines visible
- >95% of floor mask affected

### Настенная плитка (walls_tile)

- **Модель:** Equipe Costa Nova White
- **Артикул:** 28454
- **Размер:** 50×200 мм (subway/кабанчик)
- **Описание:** БЕЛАЯ глянцевая плитка с волнистой ребристой текстурой. Укладка ВЕРТИКАЛЬНАЯ.
- **Референс:** `references/wall_tiles.png`
- **КРИТИЧНО:** ДА

**Acceptance Criteria:**
- Pattern matches reference (recognizable Costa Nova wavy tiles)
- White glossy appearance
- 3D ribbed/wave texture visible
- >95% of walls_tile mask affected

### Верхняя стена (walls_upper)

- **Описание:** Гладкая крашеная стена нейтрального серого цвета (matte finish)
- **Референс:** НЕТ (оценивается по цвету и консистентности)
- **Цвет:** ~RGB(203, 203, 203) — нейтральный серый
- **КРИТИЧНО:** ДА

**Acceptance Criteria:**
- Uniform neutral gray color
- Matte paint appearance (no pattern, no texture)
- Clean boundary with tiles (no bleeding, no artifacts)
- Stable appearance across multiple renders (no drift)
- Consistent with technical_spec color requirement

**Note:** walls_upper does not have an image reference. Evaluation is based on:
1. Technical specification compliance
2. Color accuracy (neutral gray)
3. Clean boundary with walls_tile
4. No random texture/pattern injection

---

## Preserved Geometry

### Окно (window)

- **Описание:** Небольшое окно с белой ПВХ рамой, матовое стекло
- **Роль:** Источник естественного освещения
- **Референс:** НЕТ

**Acceptance Criteria:**
- Window pixels unchanged from original
- Clean boundary with adjacent walls
- Natural daylight quality preserved
- Excluded from surface fidelity scoring

---

## Boundary Quality Requirements

### Tile → Upper Wall Transition

- Clean horizontal boundary
- No color bleeding between zones
- Edge alignment follows original geometry
- No halos, smearing, or gradient artifacts

### Wall → Window Transition

- Window frame pixels unchanged
- No wall texture bleeding into window
- Light quality from window preserved

---

## Excluded Elements

The following elements from `bathroom_01` are **NOT** part of this surface-only experiment:

| Element | Reason |
|---------|--------|
| bathtub | Fixture, not surface |
| vanity | Fixture, not surface |
| mirror | Fixture, not surface |
| faucet | Fixture, not surface |
| rainshower | Fixture, not surface |
| towel_warmer | Fixture, not surface |
| basket | Accessory, not surface |
| shower_screen | Fixture, not surface |

These elements are masked in `masks/fixtures_all.png` and should be:
- Preserved unchanged in SF1-SF4 workflows
- Explicitly protected via boundary_mask in SF5

---

## Quality Standards

- **Освещение:** Тёплый естественный свет из окна
- **Атмосфера:** Чистая, современная
- **Детали:** Чёткие текстуры материалов, видны швы плитки

---

## Constraints

⛔ **НЕ ДОЛЖНО ПОЯВИТЬСЯ:**
- Другой цвет напольной плитки (только синяя с паттерном)
- Другой цвет/текстура настенной плитки (только белая волнистая)
- Текстура/паттерн на верхней стене (только гладкий серый)
- Изменения окна (должно остаться неизменным)
