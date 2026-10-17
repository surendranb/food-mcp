# SPDX-License-Identifier: MIT
"""Recipe formulation and macro-optimization engine."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from food_mcp.data.ifct_data import get_ifct_food, search_ifct_foods
from food_mcp.data.usda_data import get_usda_food, search_usda_foods
from food_mcp.engine.chemistry import (
    LEUCINE_MPS_THRESHOLD_G,
    calculate_amino_acid_completeness,
    calculate_glycemic_metrics,
    calculate_micronutrient_synergy,
    calculate_nova_processing_score,
)


def resolve_food_profile(
    food_ref: str,
    external_lookup_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> Optional[Dict[str, Any]]:
    """Resolves a food reference (ID or name) across IFCT, USDA, and external sources."""
    ref = food_ref.strip()

    # 1. Direct ID lookup
    if ref.startswith("ifct:"):
        p = get_ifct_food(ref)
        if p:
            return p
    if ref.startswith("usda:"):
        p = get_usda_food(ref)
        if p:
            return p

    # 2. Local IFCT key match
    p = get_ifct_food(f"ifct:{ref}")
    if p:
        return p

    # 3. Local USDA key match
    p = get_usda_food(f"usda:{ref}")
    if p:
        return p

    # 4. Search IFCT dataset
    ifct_matches = search_ifct_foods(ref, limit=1)
    if ifct_matches:
        return ifct_matches[0]

    # 5. Search USDA dataset
    usda_matches = search_usda_foods(ref, limit=1)
    if usda_matches:
        return usda_matches[0]

    # 6. External fallback (e.g. Open Food Facts barcode or client)
    if external_lookup_fn:
        ext = external_lookup_fn(ref)
        if ext:
            return ext

    return None


def formulate_recipe(
    ingredients: List[Dict[str, Any]],
    servings: int = 1,
    title: Optional[str] = None,
    external_lookup_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Formulates a precision recipe with molecular nutrition, amino acid completeness,

    micronutrient synergies, glycemic load, and cleanliness score.
    """
    servings = max(1, int(servings))
    resolved_items: List[Dict[str, Any]] = []
    unresolved_items: List[str] = []

    total_grams = 0.0
    tot_cal = 0.0
    tot_prot = 0.0
    tot_fat = 0.0
    tot_carbs = 0.0
    tot_fiber = 0.0
    tot_net_carbs = 0.0

    tot_na = 0.0
    tot_k = 0.0
    tot_ca = 0.0
    tot_mg = 0.0
    tot_fe = 0.0
    tot_zn = 0.0

    tot_aa: Dict[str, float] = {
        "histidine": 0.0,
        "isoleucine": 0.0,
        "leucine": 0.0,
        "lysine": 0.0,
        "methionine": 0.0,
        "cysteine": 0.0,
        "phenylalanine": 0.0,
        "tyrosine": 0.0,
        "threonine": 0.0,
        "tryptophan": 0.0,
        "valine": 0.0,
    }

    tot_fatty_acids: Dict[str, float] = {
        "saturated": 0.0,
        "monounsaturated": 0.0,
        "polyunsaturated": 0.0,
        "trans": 0.0,
    }

    detected_allergens: set[str] = set()
    detected_additives: set[str] = set()

    for item in ingredients:
        grams = float(item.get("grams", item.get("amount_g", 100.0)))
        if grams <= 0:
            continue

        ref = item.get("food_id") or item.get("name") or item.get("barcode") or ""
        profile = resolve_food_profile(ref, external_lookup_fn=external_lookup_fn)

        if not profile:
            unresolved_items.append(ref)
            continue

        scale = grams / 100.0
        p100 = profile.get("per_100g", {})

        cals = p100.get("calories", 0.0) * scale
        prot = p100.get("protein_g", 0.0) * scale
        fat = p100.get("fat_g", 0.0) * scale
        carbs = p100.get("carbohydrates_g", 0.0) * scale
        fib = p100.get("fiber_g", 0.0) * scale
        net_c = max(0.0, carbs - fib)

        tot_cal += cals
        tot_prot += prot
        tot_fat += fat
        tot_carbs += carbs
        tot_fiber += fib
        tot_net_carbs += net_c
        total_grams += grams

        tot_na += p100.get("sodium_mg", 0.0) * scale
        tot_k += p100.get("potassium_mg", 0.0) * scale
        tot_ca += p100.get("calcium_mg", 0.0) * scale
        tot_mg += p100.get("magnesium_mg", 0.0) * scale
        tot_fe += p100.get("iron_mg", 0.0) * scale
        tot_zn += p100.get("zinc_mg", 0.0) * scale

        aa_map = p100.get("amino_acids_mg", {})
        for aa_key in tot_aa:
            tot_aa[aa_key] += aa_map.get(aa_key, 0.0) * scale

        fa_map = p100.get("fatty_acids_g", {})
        for fa_key in tot_fatty_acids:
            tot_fatty_acids[fa_key] += fa_map.get(fa_key, 0.0) * scale

        for alg in p100.get("allergens", []):
            detected_allergens.add(alg)
        for add in p100.get("additives", []):
            detected_additives.add(add)

        resolved_items.append({
            "food_id": profile.get("id"),
            "name": profile.get("name"),
            "grams": grams,
            "calories": round(cals, 1),
            "protein_g": round(prot, 2),
            "fat_g": round(fat, 2),
            "carbohydrates_g": round(carbs, 2),
            "fiber_g": round(fib, 2),
            "net_carbs_g": round(net_c, 2),
            "glycemic_index": p100.get("glycemic_index", 50),
            "nova_group": p100.get("nova_group", 1),
            "nutri_score": p100.get("nutri_score", "A"),
        })

    # Caloric macro distribution
    prot_kcal = tot_prot * 4.0
    fat_kcal = tot_fat * 9.0
    carb_kcal = tot_net_carbs * 4.0
    macro_kcal_sum = prot_kcal + fat_kcal + carb_kcal

    pct_prot = round((prot_kcal / macro_kcal_sum) * 100, 1) if macro_kcal_sum > 0 else 0.0
    pct_fat = round((fat_kcal / macro_kcal_sum) * 100, 1) if macro_kcal_sum > 0 else 0.0
    pct_carbs = round((carb_kcal / macro_kcal_sum) * 100, 1) if macro_kcal_sum > 0 else 0.0

    # Engine evaluations
    aa_evaluation = calculate_amino_acid_completeness(tot_aa, tot_prot, servings=servings)
    micro_evaluation = calculate_micronutrient_synergy(tot_na, tot_k, tot_ca, tot_mg, tot_fe, tot_zn)
    glycemic_metrics = calculate_glycemic_metrics(resolved_items, tot_net_carbs, servings=servings)
    nova_evaluation = calculate_nova_processing_score(resolved_items, total_grams)

    return {
        "title": title or "Custom Formulated Recipe",
        "servings": servings,
        "total_weight_grams": round(total_grams, 1),
        "aggregate_macros": {
            "calories": round(tot_cal, 1),
            "protein_g": round(tot_prot, 2),
            "fat_g": round(tot_fat, 2),
            "carbohydrates_g": round(tot_carbs, 2),
            "fiber_g": round(tot_fiber, 2),
            "net_carbs_g": round(tot_net_carbs, 2),
        },
        "per_serving_macros": {
            "calories": round(tot_cal / servings, 1),
            "protein_g": round(tot_prot / servings, 2),
            "fat_g": round(tot_fat / servings, 2),
            "carbohydrates_g": round(tot_carbs / servings, 2),
            "fiber_g": round(tot_fiber / servings, 2),
            "net_carbs_g": round(tot_net_carbs / servings, 2),
        },
        "caloric_distribution": {
            "protein_pct": pct_prot,
            "fat_pct": pct_fat,
            "net_carbs_pct": pct_carbs,
            "macro_calories_sum": round(macro_kcal_sum, 1),
        },
        "amino_acid_profile": aa_evaluation,
        "micronutrient_synergy": micro_evaluation,
        "glycemic_impact": glycemic_metrics,
        "cleanliness_processing": nova_evaluation,
        "detected_allergens": sorted(detected_allergens),
        "detected_additives": sorted(detected_additives),
        "ingredients": resolved_items,
        "unresolved_ingredients": unresolved_items,
    }


def optimize_recipe_macros(
    ingredients: List[Dict[str, Any]],
    target_protein_g: float = 40.0,
    max_carbs_g: float = 30.0,
    servings: int = 1,
    external_lookup_fn: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Analyzes a recipe and suggests precise gram adjustments and nutrient-dense swaps

    to reach target protein, stay under max net carbs, and clear the 2.5g leucine MPS threshold.
    """
    initial = formulate_recipe(ingredients, servings=servings, external_lookup_fn=external_lookup_fn)
    per_serv = initial["per_serving_macros"]
    current_protein = per_serv["protein_g"]
    current_carbs = per_serv["net_carbs_g"]
    current_leucine = initial["amino_acid_profile"]["leucine_per_serving_g"]
    limiting_aa = initial["amino_acid_profile"]["limiting_amino_acid"]

    recommendations: List[Dict[str, Any]] = []

    # 1. Protein Deficit / Leucine Threshold
    protein_deficit = target_protein_g - current_protein
    leucine_deficit = LEUCINE_MPS_THRESHOLD_G - current_leucine

    if protein_deficit > 0 or leucine_deficit > 0:
        # Suggest protein-dense additions
        rec_options = [
            {
                "food_id": "usda:hemp_seeds",
                "name": "Hemp Seed Hearts",
                "suggested_grams_per_serving": 30.0,
                "protein_boost_g": 9.5,
                "leucine_boost_g": 0.65,
                "carb_addition_g": 1.4,
                "benefit": "Complete plant protein + 210mg Magnesium, zero glycemic impact.",
            },
            {
                "food_id": "ifct:paneer",
                "name": "Indian Cottage Cheese (Paneer)",
                "suggested_grams_per_serving": 60.0,
                "protein_boost_g": 11.0,
                "leucine_boost_g": 1.09,
                "carb_addition_g": 2.2,
                "benefit": "Rich bioavailable casein/whey leucine and 288mg Calcium.",
            },
            {
                "food_id": "usda:nutritional_yeast",
                "name": "Nutritional Yeast Flakes",
                "suggested_grams_per_serving": 15.0,
                "protein_boost_g": 7.5,
                "leucine_boost_g": 0.57,
                "carb_addition_g": 2.2,
                "benefit": "50% protein density by weight + B-complex vitamins.",
            },
            {
                "food_id": "usda:whey_protein_isolate",
                "name": "Whey Protein Isolate",
                "suggested_grams_per_serving": 25.0,
                "protein_boost_g": 22.5,
                "leucine_boost_g": 2.75,
                "carb_addition_g": 0.25,
                "benefit": "Single-serving immediate 2.75g Leucine MPS trigger with near-zero carbs.",
            },
        ]
        recommendations.append({
            "category": "Protein & Leucine Optimization",
            "observation": f"Current protein is {current_protein}g (target: {target_protein_g}g), Leucine is {current_leucine}g (MPS target: {LEUCINE_MPS_THRESHOLD_G}g).",
            "options": rec_options,
        })

    # 2. Carbohydrate Excess / High GI Swaps
    if current_carbs > max_carbs_g:
        carb_excess = current_carbs - max_carbs_g
        swap_options = [
            {
                "swap_target": "Rice / Atta / High-carb flours",
                "replacement": "Lupin Flour (usda:lupin_flour) or Almond Flour (usda:almond_flour)",
                "impact": "Lupin flour provides 40% protein and only 12% net carbs with 28% prebiotic fiber.",
                "estimated_carb_reduction_g": round(carb_excess * 0.6, 1),
            },
            {
                "swap_target": "Polished Basmati Rice",
                "replacement": "Ragi (ifct:ragi), Foxtail Millet (ifct:foxtail_millet), or Cauliflower Rice",
                "impact": "Lowers glycemic load from high spike to slow-digesting complex carbs with 3x minerals.",
                "estimated_carb_reduction_g": round(carb_excess * 0.4, 1),
            },
        ]
        recommendations.append({
            "category": "Carbohydrate Reduction & Glycemic Stabilization",
            "observation": f"Current net carbs are {current_carbs}g per serving, exceeding max target {max_carbs_g}g by {round(carb_excess, 1)}g.",
            "options": swap_options,
        })

    # 3. Limiting Amino Acid Complementation
    if limiting_aa:
        if "lysine" in limiting_aa.lower():
            recommendations.append({
                "category": "Amino Acid Complementation (Lysine Deficit)",
                "observation": "Recipe is limited by Lysine (common in millets, wheat, and cereals).",
                "solution": "Complement with Lysine-rich pulses (Toor dal, Moong dal, or Chana dal) or dairy/paneer at a 3:1 cereal-to-legume ratio to achieve a 1.0+ Amino Acid Score.",
            })
        elif "methionine" in limiting_aa.lower():
            recommendations.append({
                "category": "Amino Acid Complementation (Sulfur Amino Acid Deficit)",
                "observation": "Recipe is limited by Methionine + Cysteine (common in pulses and legumes).",
                "solution": "Complement with Methionine-dense White Sesame Seeds (ifct:sesame_seeds, 580mg SAA/100g) or millets (Bajra/Ragi) to complete the protein matrix.",
            })

    # Simulated post-optimization projection
    projected_protein = current_protein
    projected_carbs = current_carbs
    projected_leucine = current_leucine

    if protein_deficit > 0:
        projected_protein += min(protein_deficit + 5.0, 25.0)
        projected_leucine += 1.5
    if current_carbs > max_carbs_g:
        projected_carbs = max_carbs_g

    projected_clears_mps = projected_leucine >= LEUCINE_MPS_THRESHOLD_G

    return {
        "current_evaluation": {
            "protein_per_serving_g": current_protein,
            "target_protein_g": target_protein_g,
            "net_carbs_per_serving_g": current_carbs,
            "max_carbs_g": max_carbs_g,
            "leucine_per_serving_g": current_leucine,
            "clears_leucine_mps_threshold": initial["amino_acid_profile"]["clears_leucine_threshold"],
            "limiting_amino_acid": limiting_aa,
        },
        "optimization_recommendations": recommendations,
        "projected_optimized_macros": {
            "projected_protein_g": round(projected_protein, 1),
            "projected_net_carbs_g": round(projected_carbs, 1),
            "projected_leucine_g": round(projected_leucine, 2),
            "projected_clears_mps": projected_clears_mps,
        },
    }
