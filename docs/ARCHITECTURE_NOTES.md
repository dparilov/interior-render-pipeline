# Architecture Notes — 2026-04-02

## AI vs Blender Rendering — Выводы

### Проблемы ComfyUI/IPAdapter (от которых ушли на Blender):
- IPAdapter "размазывает" материалы, не копирует паттерн точно
- AI галлюцинирует геометрию
- Маски работают плохо на границах surfaces
- Tile patterns не воспроизводятся точно
- ControlNet даёт только приблизительную перспективу

### Где Blender выигрывает:
- UV mapping — точное позиционирование текстур
- Детерминированный результат
- Per-object materials
- Procedural textures для паттернов
- Точная камера из DAE

### Где AI реально нужен:
1. Анализ ТЗ → prompts (LLM)
2. Reference → PBR texture generation (возможно)
3. Финальный enhance с очень низким denoise (0.1-0.2)
4. Inpainting дефектов

### Гипотеза: Blender + ComfyUI pipeline
Вариант A (Blender → EXR → ComfyUI) вернёт те же проблемы.
Лучше: Blender-only с качественными PBR текстурами.

### Открытые вопросы:
- [ ] Fixtures: как менять отдельные объекты (смесители, ванны)?
- [ ] PBR текстуры: генерировать AI или брать готовые?
- [ ] Финальный enhance: нужен или достаточно Blender denoiser?

---

## Fixtures — Подходы (2026-04-02)

### Задача: Замена fixtures (смеситель, ванна, унитаз)

### Вариант 1: 3D Asset Libraries ❌
- BlenderKit, Poly Haven, CGTrader
- **Отклонено:** 3D моделей не будет, не масштабируется

### Вариант 2: AI 3D Generation ⚠️ ПРОБОВАТЬ
- Meshy.ai, Luma AI Genie, Tripo3D
- Reference image → 3D model → Blender
- **Статус:** Нужен эксперимент, только для fixtures

### Вариант 3: Hybrid (generic 3D + AI materials) ⚠️
- Найти похожую базовую модель
- AI style transfer на текстуры
- **Оценка:** Скептицизм, но возможно

### Вариант 4: Inpainting в финальном рендере ⚠️
- Маска fixture → ComfyUI inpainting
- **Оценка:** Сомнения, особенно для крупных объектов

### Текущий план:
- **Surfaces:** Blender + PBR (приоритет)
- **Fixtures:** Отложить, нужны эксперименты с AI 3D generation

### TODO:
- [ ] Эксперимент: Meshy.ai image-to-3D на референсе смесителя
- [ ] Эксперимент: Luma Genie на фото ванны
- [ ] Оценить качество для Blender рендера

---
