---
name: recipe-formulation
description: Precision Recipe Formulation playbook covering macro distribution, caloric ratios, micronutrient synergies (Na:K, Ca:Mg), and glycemic load profiling.
---

# Precision Recipe Formulation Playbook

## 1. Principles of Molecular Recipe Design
Formulating a meal for performance, metabolic health, or longevity requires looking past gross calories to molecular nutrient density, bioavailability, and synergistic interactions:

1. **Caloric Distribution**:
   - **Protein**: 25% - 35% of energy for satiety, lean mass retention, and thermic effect of food (TEF).
   - **Fats**: 30% - 40% of energy prioritizing monounsaturated fatty acids (MUFA) and balanced Omega-3:6 ratios.
   - **Net Carbs**: Controlled based on metabolic demand, focusing on low glycemic impact and high soluble/insoluble dietary fiber.

2. **The $Na:K$ Cellular Electrolyte Balance**:
   - **Target**: Sodium-to-Potassium ratio $< 1.0$ (ideally $0.5 - 0.8$).
   - High sodium without compensatory potassium leads to vascular stiffening and elevated systolic pressure.
   - Whole plant staples (Toor dal, Moringa, Turmeric, Cumin, Avocado, Potatoes) provide massive potassium ($> 800\text{ mg}/100\text{g}$) to naturally buffer sodium.

3. **The $Ca:Mg$ Divalent Mineral Balance**:
   - **Target**: Calcium-to-Magnesium ratio between $1.7:1$ and $2.6:1$ (optimal ~ $2.0:1$).
   - Calcium without adequate magnesium can cause cellular calcium accumulation and vascular calcification.
   - Seeds (Hemp, Chia, Sesame) and dark leafy greens (Moringa) provide robust magnesium to counter high-calcium dairy (Paneer, Curd).

4. **Iron Bioavailability Synergy**:
   - Non-heme iron in pulses, millets, and leafy greens is predominantly in the ferric ($Fe^{3+}$) state.
   - **The Ascorbic Acid Lever**: Adding just 25–50mg of Vitamin C (fresh lime juice, Amla, raw capsicum) converts ferric to ferrous ($Fe^{2+}$) iron, multiplying absorption up to 300%.
   - **Inhibitor Timing**: Keep tannins (black tea, coffee) and high-dose calcium supplements at least 60 minutes away from iron-rich meals.

---

## 2. Glycemic Load (GL) vs Glycemic Index (GI)
While Glycemic Index measures the *speed* of carbohydrate absorption relative to glucose, Glycemic Load measures the *total glycemic impact* of an actual serving:

$$\text{Glycemic Load (GL)} = \frac{\text{Meal GI} \times \text{Net Carbs per serving (g)}}{100}$$

| GL Category | Score per Serving | Physiological Impact |
|---|---|---|
| **Low** | $\le 10$ | Stable glucose curve, minimal insulin demand, prolonged satiety |
| **Medium** | $11 - 19$ | Moderate glycemic elevation suitable for active recovery |
| **High** | $\ge 20$ | Rapid glucose influx triggering steep insulin spike and reactive hypoglycemia |

---

## 3. Step-by-Step AI Formulation Protocol
When an agent or user asks to formulate or audit a recipe:
1. Run `formulate_recipe(ingredients=[...], servings=N)`.
2. Check `aggregate_macros` and `per_serving_macros`.
3. Check `amino_acid_profile.clears_leucine_threshold` (must hit $\ge 2.5\text{g}$ per serving).
4. Inspect `micronutrient_synergy.na_k_ratio` ($< 1.0$) and `ca_mg_ratio` ($\sim 2:1$).
5. Inspect `glycemic_impact.gl_per_serving` ($\le 10$ for fat loss / insulin management).
6. Inspect `cleanliness_processing.weighted_nova_score` ($< 2.0$ for clean whole-food status).
7. If targets are missed, invoke `optimize_recipe_macros` to generate exact gram adjustments and nutrient-dense swaps.
