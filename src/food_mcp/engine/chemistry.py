# SPDX-License-Identifier: MIT
"""Precision Food Chemistry Engine: Molecular nutrition, amino acids, micros, and GI/GL."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# WHO/FAO/UNU 2007 Adult Essential Amino Acid Reference Scoring Pattern (mg per g of protein)
WHO_FAO_2007_EAA_PATTERN: Dict[str, float] = {
    "histidine": 15.0,
    "isoleucine": 30.0,
    "leucine": 59.0,
    "lysine": 45.0,
    "methionine_cysteine": 22.0,  # Sulfur Amino Acids (SAA)
    "phenylalanine_tyrosine": 38.0,  # Aromatic Amino Acids (AAA)
    "threonine": 23.0,
    "tryptophan": 6.0,
    "valine": 39.0,
}

LEUCINE_MPS_THRESHOLD_G: float = 2.50  # 2.5g Leucine triggers muscle protein synthesis in adults


def calculate_amino_acid_completeness(
    amino_acids_mg: Dict[str, float],
    total_protein_g: float,
    servings: int = 1,
) -> Dict[str, Any]:
    """Evaluates essential amino acid profile against WHO/FAO 2007 adult scoring pattern

    and checks the 2.5g Leucine Muscle Protein Synthesis (MPS) threshold.
    """
    servings = max(1, servings)
    total_leucine_mg = amino_acids_mg.get("leucine", 0.0)
    leucine_per_serving_g = (total_leucine_mg / servings) / 1000.0

    clears_mps = leucine_per_serving_g >= LEUCINE_MPS_THRESHOLD_G
    leucine_deficit_g = max(0.0, LEUCINE_MPS_THRESHOLD_G - leucine_per_serving_g)

    if total_protein_g <= 0.0:
        return {
            "amino_acid_score": 0.0,
            "completeness_status": "No Protein",
            "limiting_amino_acid": None,
            "limiting_amino_acid_ratio": 0.0,
            "leucine_per_serving_g": 0.0,
            "clears_leucine_threshold": False,
            "leucine_threshold_target_g": LEUCINE_MPS_THRESHOLD_G,
            "leucine_deficit_g": LEUCINE_MPS_THRESHOLD_G,
            "eaa_ratios": {},
            "total_eaa_mg": 0.0,
        }

    # Combined groups for WHO standard
    saa_mg = amino_acids_mg.get("methionine", 0.0) + amino_acids_mg.get("cysteine", 0.0)
    aaa_mg = amino_acids_mg.get("phenylalanine", 0.0) + amino_acids_mg.get("tyrosine", 0.0)

    evaluated_eaa: Dict[str, float] = {
        "histidine": amino_acids_mg.get("histidine", 0.0),
        "isoleucine": amino_acids_mg.get("isoleucine", 0.0),
        "leucine": total_leucine_mg,
        "lysine": amino_acids_mg.get("lysine", 0.0),
        "methionine_cysteine": saa_mg,
        "phenylalanine_tyrosine": aaa_mg,
        "threonine": amino_acids_mg.get("threonine", 0.0),
        "tryptophan": amino_acids_mg.get("tryptophan", 0.0),
        "valine": amino_acids_mg.get("valine", 0.0),
    }

    total_eaa_mg = sum(evaluated_eaa.values())
    eaa_ratios: Dict[str, float] = {}
    limiting_aa: Optional[str] = None
    min_ratio = float("inf")

    for aa, amount_mg in evaluated_eaa.items():
        ref_val = WHO_FAO_2007_EAA_PATTERN.get(aa, 1.0)
        # Concentration in mg / g protein
        conc = amount_mg / total_protein_g
        ratio = conc / ref_val
        eaa_ratios[aa] = round(ratio, 2)
        if ratio < min_ratio:
            min_ratio = ratio
            limiting_aa = aa

    if min_ratio == float("inf"):
        min_ratio = 0.0

    aas = round(min_ratio, 2)
    is_complete = aas >= 1.0

    if is_complete:
        status = "Complete protein (clears 100% of WHO/FAO 2007 reference adult pattern)"
    else:
        percentage = int(aas * 100)
        limiting_name = limiting_aa.replace("_", " + ") if limiting_aa else "unknown"
        status = f"Incomplete (limiting: {limiting_name} at {percentage}% of WHO/FAO requirement)"

    return {
        "amino_acid_score": aas,
        "is_complete": is_complete,
        "completeness_status": status,
        "limiting_amino_acid": limiting_aa,
        "limiting_amino_acid_ratio": aas,
        "leucine_per_serving_g": round(leucine_per_serving_g, 2),
        "clears_leucine_threshold": clears_mps,
        "leucine_threshold_target_g": LEUCINE_MPS_THRESHOLD_G,
        "leucine_deficit_g": round(leucine_deficit_g, 2),
        "eaa_ratios": eaa_ratios,
        "total_eaa_mg": round(total_eaa_mg, 1),
    }


def calculate_micronutrient_synergy(
    sodium_mg: float,
    potassium_mg: float,
    calcium_mg: float,
    magnesium_mg: float,
    iron_mg: float,
    zinc_mg: float,
) -> Dict[str, Any]:
    """Calculates critical mineral balance ratios (Na:K, Ca:Mg) and iron bioavailability notes."""
    # Sodium to Potassium ratio
    na_k_ratio = round(sodium_mg / potassium_mg, 2) if potassium_mg > 0 else (999.0 if sodium_mg > 0 else 0.0)
    if na_k_ratio <= 0.8:
        na_k_verdict = "Optimal (potassium significantly exceeds sodium, supporting healthy blood pressure)"
    elif na_k_ratio <= 1.0:
        na_k_verdict = "Balanced (meets recommended < 1.0 dietary target)"
    else:
        na_k_verdict = f"Elevated ({na_k_ratio} > 1.0 target; excess sodium relative to potassium)"

    # Calcium to Magnesium ratio
    ca_mg_ratio = round(calcium_mg / magnesium_mg, 2) if magnesium_mg > 0 else (999.0 if calcium_mg > 0 else 0.0)
    if 1.7 <= ca_mg_ratio <= 2.6:
        ca_mg_verdict = "Optimal biological balance (~2:1 ratio for bone metabolism and vascular tone)"
    elif ca_mg_ratio > 3.0:
        ca_mg_verdict = f"High Ca:Mg ({ca_mg_ratio}:1 > 3.0; excess calcium may compete with magnesium uptake)"
    elif ca_mg_ratio < 1.5 and ca_mg_ratio > 0.0:
        ca_mg_verdict = f"Low Ca:Mg ({ca_mg_ratio}:1; magnesium rich relative to calcium)"
    else:
        ca_mg_verdict = f"Acceptable balance ({ca_mg_ratio}:1)"

    # Iron Bioavailability & Synergy
    notes: List[str] = []
    if iron_mg >= 3.0:
        notes.append(
            f"Contains substantial iron ({round(iron_mg, 1)} mg). Non-heme plant iron absorption is boosted "
            "up to 300% when paired with ascorbic acid (lemon juice, amla, bell peppers, tomatoes)."
        )
        notes.append(
            "Avoid concurrent consumption of tea, coffee, or calcium supplements within 1 hour to prevent phytate/tannin inhibition."
        )
    if zinc_mg >= 2.0:
        notes.append(
            f"Provides bioavailable zinc ({round(zinc_mg, 1)} mg), essential for immune competence and enzymatic protein synthesis."
        )

    return {
        "sodium_mg": round(sodium_mg, 1),
        "potassium_mg": round(potassium_mg, 1),
        "na_k_ratio": na_k_ratio,
        "na_k_verdict": na_k_verdict,
        "calcium_mg": round(calcium_mg, 1),
        "magnesium_mg": round(magnesium_mg, 1),
        "ca_mg_ratio": ca_mg_ratio,
        "ca_mg_verdict": ca_mg_verdict,
        "iron_mg": round(iron_mg, 2),
        "zinc_mg": round(zinc_mg, 2),
        "bioavailability_notes": notes,
    }


def calculate_glycemic_metrics(
    ingredients_breakdown: List[Dict[str, Any]],
    total_net_carbs_g: float,
    servings: int = 1,
) -> Dict[str, Any]:
    """Calculates weighted meal Glycemic Index (GI) and per-serving Glycemic Load (GL)."""
    servings = max(1, servings)
    if total_net_carbs_g <= 0.1:
        return {
            "estimated_gi": 0,
            "gi_category": "Very Low (Keto / Zero Carb)",
            "total_glycemic_load": 0.0,
            "gl_per_serving": 0.0,
            "gl_category": "Low (GL <= 10)",
        }

    sum_carbs = sum(ing.get("net_carbs_g", 0.0) for ing in ingredients_breakdown)
    if sum_carbs <= 0.0:
        sum_carbs = total_net_carbs_g

    weighted_gi_sum = 0.0
    for ing in ingredients_breakdown:
        nc = ing.get("net_carbs_g", 0.0)
        gi = ing.get("glycemic_index", 50)
        weighted_gi_sum += gi * nc

    meal_gi = round(weighted_gi_sum / sum_carbs, 1)

    # Glycemic Load per serving = (GI * Net Carbs per serving) / 100
    net_carbs_per_serving = total_net_carbs_g / servings
    gl_per_serving = round((meal_gi * net_carbs_per_serving) / 100.0, 1)

    # GI categorization
    if meal_gi <= 55:
        gi_cat = "Low GI (<= 55)"
    elif meal_gi <= 69:
        gi_cat = "Medium GI (56 - 69)"
    else:
        gi_cat = "High GI (>= 70)"

    # GL categorization
    if gl_per_serving <= 10:
        gl_cat = "Low Glycemic Load (<= 10 per serving; minimal blood glucose spike)"
    elif gl_per_serving <= 19:
        gl_cat = "Medium Glycemic Load (11 - 19 per serving; moderate glycemic response)"
    else:
        gl_cat = "High Glycemic Load (>= 20 per serving; rapid insulin demand)"

    return {
        "estimated_gi": int(round(meal_gi)),
        "gi_category": gi_cat,
        "total_glycemic_load": round((meal_gi * total_net_carbs_g) / 100.0, 1),
        "gl_per_serving": gl_per_serving,
        "gl_category": gl_cat,
    }


def calculate_nova_processing_score(
    ingredients_breakdown: List[Dict[str, Any]],
    total_grams: float,
) -> Dict[str, Any]:
    """Calculates weighted NOVA cleanliness score and flags ultra-processed ingredients."""
    if total_grams <= 0:
        return {
            "weighted_nova_score": 1.0,
            "classification": "Unprocessed / Whole Food",
            "ultra_processed_alerts": [],
            "nova_distribution": {},
        }

    nova_grams: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    up_alerts: List[Dict[str, Any]] = []

    weighted_sum = 0.0
    for ing in ingredients_breakdown:
        g = ing.get("grams", 0.0)
        nova = ing.get("nova_group", 1)
        if nova not in (1, 2, 3, 4):
            nova = 1
        nova_grams[nova] += g
        weighted_sum += nova * g

        if nova == 4:
            up_alerts.append({
                "ingredient": ing.get("name", "Unknown"),
                "grams": g,
                "reason": "Classified as NOVA 4 (Ultra-processed formulation or contains industrial additives)",
            })

    weighted_score = round(weighted_sum / total_grams, 2)

    if weighted_score <= 1.5:
        classification = "Clean Whole Food (NOVA 1 dominant)"
    elif weighted_score <= 2.5:
        classification = "Culinary Whole-Food Preparation (NOVA 1-2 balanced)"
    elif weighted_score <= 3.5:
        classification = "Processed Food Inclusion (NOVA 3 present)"
    else:
        classification = "Ultra-Processed Heavy Formulation (NOVA 4 dominant)"

    dist = {f"nova_{k}": round((v / total_grams) * 100, 1) for k, v in nova_grams.items()}

    return {
        "weighted_nova_score": weighted_score,
        "classification": classification,
        "ultra_processed_alerts": up_alerts,
        "nova_distribution": dist,
    }
