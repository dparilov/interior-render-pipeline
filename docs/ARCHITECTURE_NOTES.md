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
