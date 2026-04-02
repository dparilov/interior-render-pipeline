# EPIC: Nano Banana Pro Integration Research

**Created:** 2026-04-02
**Status:** RESEARCH
**Priority:** HIGH

---

## Goal

Исследовать возможность замены/дополнения текущего pipeline (SketchUp → Blender) на Nano Banana Pro для interior rendering.

---

## Background

### Что такое Nano Banana Pro

- **Model:** Google Gemini 3 Pro Image
- **Architecture:** Multi-step self-correction (не simple diffusion)
- **Process:** Planning → Generation → Self-analysis → Auto-correction → Iteration
- **References:** До 14 images (6 high-fidelity)
- **Masking:** Semantic через текст (без ручных масок)
- **Speed:** 8-12 секунд на 4K

### Доступ

| Platform | Type | Cost |
|----------|------|------|
| RunPod | `nano-banana-pro-edit` | Per-use |
| Google AI Studio | API | Free tier + paid |
| fal.ai | API | $0.12-0.24/image |
| Dzine.ai | Web | $25-60/month |

---

## Research Questions

### Q1: Optimal Input Format

| Input | Описание | Pros | Cons |
|-------|----------|------|------|
| SketchUp raw | beauty.png as-is | Простота | Текстуры SKP |
| SketchUp white | Белые материалы | Чистая геометрия | Требует prep |
| Blender gray | Серый рендер | Точная геометрия | Лишний шаг |
| Blender + masks | Рендер + маски | Региональный контроль | Сложность |

### Q2: Reference Strategy

| Strategy | Refs | Expected |
|----------|------|----------|
| Single swatch | 1 | Style transfer |
| Per-surface | 3-5 | Regional materials |
| Full moodboard | 10-14 | Overall style |
| Tiled + prompt | 1 | Exact pattern? |

### Q3: Pattern Accuracy (CRITICAL)

**Вопрос:** Сохраняется ли ТОЧНЫЙ геометрический паттерн плитки?

**Test:**
- Reference: Rivoli Bergen Azul (quatrefoil pattern)
- Measure: Visual similarity to reference tile

---

## Experiments

### E1: Raw SketchUp Input
```
Input: examples/bathroom_02/beauty.png
References: 
  - references/floor_tiles.jpg
  - references/wall_tiles.png
Prompt: "Photorealistic interior render. Apply floor tiles from 
        ref1 to floor. Apply wall tiles from ref2 to walls.
        Preserve exact camera, framing, geometry."
```

### E2: Prepared Base (White Materials)
```
Input: Blender render with white materials
References: Same as E1
Prompt: Same as E1
```

### E3: Semantic Masking
```
Input: beauty.png
Prompt: "Replace only the floor area with exact tile pattern 
        from reference image. Keep everything else unchanged."
Reference: floor_tiles.jpg
```

### E4: Multi-turn Editing
```
Turn 1: Base render
Turn 2: Apply floor material
Turn 3: Apply wall material
Turn 4: Adjust lighting
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Pattern accuracy | ≥ 80% visual match |
| Geometry preservation | ≥ 95% |
| Generation time | < 30 sec (1080p) |
| Reproducibility | Consistent across runs |

---

## Deliverables

1. [ ] Comparison matrix: Input × Reference × Quality
2. [ ] Pattern accuracy test (quantitative)
3. [ ] Latency benchmark
4. [ ] Cost analysis vs Blender
5. [ ] Final recommendation

---

## Comparison with Current Pipeline

| Aspect | Blender Pipeline | Nano Banana |
|--------|------------------|-------------|
| Geometry accuracy | ✅ 100% | ⚠️ ~95% |
| Material accuracy | ✅ PBR exact | ⚠️ TBD |
| Pattern reproduction | ✅ UV mapping | ⚠️ TBD |
| Speed | ❌ Minutes | ✅ Seconds |
| Automation | ✅ Full API | ✅ Full API |
| Setup complexity | ❌ High | ✅ Low |

---

## Notes

- Nano Banana решает ДРУГУЮ задачу: быстрые эскизы vs детальные рендеры
- Но качество Pro версии может быть достаточным для production
- Критический тест: точность паттернов плитки
