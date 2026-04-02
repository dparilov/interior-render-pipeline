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

---

## Prompting Strategy (Extended)

### Prompt Structure

```
[STRUCTURE] + [MATERIALS] + [LIGHTING] + [CAMERA] + [STYLE]
```

### ТЗ → Prompt Mapping

| ТЗ Section | Prompt Component |
|------------|------------------|
| Напольная плитка | `floor tiles from ref1, blue ceramic quatrefoil, 200x200mm` |
| Настенная плитка | `wall tiles from ref2, white glossy wavy subway, vertical` |
| Ванна | `white cast iron bathtub, front panel matching wall tiles` |
| Освещение | `natural daylight from left window, soft shadows` |

### Reference Strategies

**A) Per-Surface (recommended):**
- Ref 1: floor_tiles.jpg
- Ref 2: wall_tiles.png
- Ref 3-4: fixtures
- Ref 5-6: lighting/style mood

**B) Composite Moodboard:**
- Single collage with labeled sections
- Prompt references quadrants

**C) High-Fidelity Swatches:**
- Tileable pattern at correct scale
- 3x3 grid showing repeat
- Explicit "replicate exactly" instruction

### Multi-turn Workflow

```
Turn 1: Base photorealistic room (white materials)
Turn 2: Apply floor material + reference
Turn 3: Apply wall material + reference
Turn 4: Enhance fixtures
Turn 5: Adjust lighting
Turn 6: Final polish
```

### Prompt Experiments

| Experiment | Prompt Type | Expected |
|------------|-------------|----------|
| E5 | Minimal | Baseline quality |
| E6 | Detailed | Better accuracy |
| E7 | ТЗ-based auto | Production-ready |
| E8 | Multi-turn | Best precision |

### Auto-generation from Manifest

```python
def generate_prompt(manifest, references):
    prompt = "Transform SketchUp view into photorealistic render.\n"
    prompt += "GEOMETRY: Preserve exact layout, camera, fixtures.\n"
    prompt += "SURFACES:\n"
    
    for entity in manifest['entities']:
        if entity['class'] == 'surface':
            ref_idx = references.index(entity['reference']) + 1
            prompt += f"- {entity['name']}: ref{ref_idx}, {entity['prompt']}\n"
    
    prompt += "LIGHTING: Natural daylight, soft shadows.\n"
    prompt += "STYLE: Professional interior photography, 4K.\n"
    
    return prompt
```
