---
name: ultra-processed-food-audit
description: Ultra-Processed Food (UPF) Audit playbook covering NOVA classification (Group 1 to 4), Nutri-Score analysis, and industrial additive detection.
---

# Ultra-Processed Food (UPF) Audit Playbook

## 1. The NOVA Classification Framework
Developed by Professor Carlos Monteiro and researchers at the University of São Paulo, NOVA classifies foods according to the extent and purpose of industrial processing, rather than nutrient taxonomy alone:

```
NOVA 1: Unprocessed or Minimally Processed Foods
  └── Grains, pulses, millets, fresh vegetables, fruits, eggs, unseasoned meat/fish, pasteurized milk.
NOVA 2: Processed Culinary Ingredients
  └── Oils (mustard, sesame, olive), butter, ghee, sugar, salt, vinegar, honey.
NOVA 3: Processed Foods
  └── Freshly baked bread (flour, water, yeast, salt), canned legumes in brine, cheeses, salted nuts.
NOVA 4: Ultra-Processed Food and Drink Products (UPFs)
  └── Formulations made mostly from substances derived from foods and additives, with little or no intact whole food.
```

---

## 2. Molecular Markers of Ultra-Processing
When inspecting an ingredient list or Open Food Facts payload, look for these tell-tale UPF signatures:

1. **Substances not found in domestic kitchens**:
   - High-fructose corn syrup (HFCS), invert sugar, maltodextrin, dextrose.
   - Hydrogenated or interesterified oils, refined palm oil fractions.
   - Hydrolyzed vegetable protein, soy protein isolates, mechanically separated meat.

2. **Cosmetic & Texture-Modifying Additives**:
   - **Emulsifiers**: Carboxymethylcellulose (E466), Polysorbate 80 (E433), Mono- and diglycerides of fatty acids (E471), Soy lecithin in non-chocolate products.
   - **Thickeners & Gelling Agents**: Carrageenan (E407), Xanthan gum, Modified corn starch.
   - **Artificial Sweeteners**: Sucralose (E955), Acesulfame-K (E950), Aspartame (E951).
   - **Flavor Enhancers**: Monosodium glutamate (E621), Disodium 5'-ribonucleotides (E635).
   - **Artificial Colorants**: Tartrazine (E102), Sunset Yellow (E110), Allura Red (E129).

---

## 3. Physiological Impact of UPFs
1. **Gut Mucosal Disruption**: Emulsifiers erode the protective mucus bilayer of the gut lining, promoting low-grade systemic inflammation and bacterial translocation.
2. **Hyper-Palatability Overdrive**: The artificial combination of refined carbohydrates, trans/saturated fats, and sensory flavorings bypasses homeostatic satiety cues (leptin signalling).
3. **Impaired Ileal Brake**: Pre-digested, hyper-refined matrices are absorbed high in the jejunum, preventing distal nutrients from reaching the ileum to release GLP-1 and PYY.

---

## 4. Audit Workflow with `food-mcp`
To execute an ultra-processed food audit:
1. Scan or query the packaged product via `lookup_barcode(barcode="...")` or `lookup_food(query="...")`.
2. Inspect the returned `per_100g.nova_group`:
   - If NOVA is **4**, examine `per_100g.additives` and `ingredients_text` to isolate the industrial markers.
   - Check `nutri_score` (Grades A/B indicate better nutritional profile, though products can be NOVA 4 and Nutri-Score A/B!).
3. For homemade or restaurant recipes, run `formulate_recipe(...)` and inspect `cleanliness_processing.weighted_nova_score`:
   - Score $\le 1.5$: Clean whole food.
   - Score $> 2.5$: Processed ingredient warning.
   - Any ingredient flagged in `ultra_processed_alerts` requires substitution.
