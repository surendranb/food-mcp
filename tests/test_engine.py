# SPDX-License-Identifier: MIT
"""Unit tests for precision food chemistry and recipe formulation engines."""

from food_mcp.engine.chemistry import (
    LEUCINE_MPS_THRESHOLD_G,
    calculate_amino_acid_completeness,
    calculate_glycemic_metrics,
    calculate_micronutrient_synergy,
    calculate_nova_processing_score,
)
from food_mcp.engine.recipe import formulate_recipe, optimize_recipe_macros


def test_amino_acid_completeness_and_leucine_threshold():
    """Verify WHO/FAO 2007 pattern scoring, limiting AA detection, and Leucine MPS threshold."""
    # 1. High Leucine Complete Profile (e.g. 100g Chicken Breast)
    chicken_aa = {
        "histidine": 700.0,
        "isoleucine": 1190.0,
        "leucine": 2600.0,  # 2.6g clears MPS threshold
        "lysine": 1940.0,
        "methionine": 630.0,
        "cysteine": 260.0,
        "phenylalanine": 900.0,
        "tyrosine": 760.0,
        "threonine": 970.0,
        "tryptophan": 270.0,
        "valine": 1140.0,
    }
    eval_chicken = calculate_amino_acid_completeness(chicken_aa, total_protein_g=25.0, servings=1)
    assert eval_chicken["is_complete"] is True
    assert eval_chicken["amino_acid_score"] >= 1.0
    assert eval_chicken["clears_leucine_threshold"] is True
    assert eval_chicken["leucine_per_serving_g"] >= 2.5
    assert eval_chicken["leucine_deficit_g"] == 0.0

    # 2. Cereal Profile Limited by Lysine & Low Leucine
    cereal_aa = {
        "histidine": 150.0,
        "isoleucine": 250.0,
        "leucine": 600.0,  # Only 0.6g
        "lysine": 120.0,   # Low lysine
        "methionine": 180.0,
        "cysteine": 120.0,
        "phenylalanine": 300.0,
        "tyrosine": 200.0,
        "threonine": 200.0,
        "tryptophan": 70.0,
        "valine": 350.0,
    }
    eval_cereal = calculate_amino_acid_completeness(cereal_aa, total_protein_g=8.0, servings=1)
    assert eval_cereal["is_complete"] is False
    assert eval_cereal["limiting_amino_acid"] == "lysine"
    assert eval_cereal["clears_leucine_threshold"] is False
    assert eval_cereal["leucine_per_serving_g"] == 0.6
    assert eval_cereal["leucine_deficit_g"] == round(LEUCINE_MPS_THRESHOLD_G - 0.6, 2)


def test_micronutrient_synergy_and_ratios():
    """Verify Na:K and Ca:Mg ratios with clinical feedback."""
    # Optimal electrolyte ratio (High Potassium, Low Sodium)
    res_opt = calculate_micronutrient_synergy(
        sodium_mg=150.0,
        potassium_mg=800.0,
        calcium_mg=400.0,
        magnesium_mg=200.0,
        iron_mg=5.5,
        zinc_mg=3.0,
    )
    assert res_opt["na_k_ratio"] == 0.19
    assert "Optimal" in res_opt["na_k_verdict"]
    assert res_opt["ca_mg_ratio"] == 2.0  # 400:200 = 2:1
    assert "Optimal" in res_opt["ca_mg_verdict"]
    assert len(res_opt["bioavailability_notes"]) > 0

    # Elevated Na:K ratio
    res_high_na = calculate_micronutrient_synergy(
        sodium_mg=1200.0,
        potassium_mg=400.0,
        calcium_mg=50.0,
        magnesium_mg=30.0,
        iron_mg=0.5,
        zinc_mg=0.5,
    )
    assert res_high_na["na_k_ratio"] == 3.0
    assert "Elevated" in res_high_na["na_k_verdict"]


def test_glycemic_metrics_calculation():
    """Verify weighted meal GI and Glycemic Load (GL) calculation."""
    ingredients = [
        {"name": "Ragi", "net_carbs_g": 30.0, "glycemic_index": 54},
        {"name": "Moong Dal", "net_carbs_g": 20.0, "glycemic_index": 38},
    ]
    # Total net carbs = 50.0g
    # Weighted GI = (54*30 + 38*20) / 50 = (1620 + 760) / 50 = 2380 / 50 = 47.6 -> ~48
    # GL = (47.6 * 50) / 100 = 23.8
    res = calculate_glycemic_metrics(ingredients, total_net_carbs_g=50.0, servings=1)
    assert res["estimated_gi"] == 48
    assert "Low GI" in res["gi_category"]
    assert res["gl_per_serving"] == 23.8
    assert "High Glycemic Load" in res["gl_category"]

    # Low carb meal
    res_low = calculate_glycemic_metrics(ingredients, total_net_carbs_g=10.0, servings=2)
    assert res_low["gl_per_serving"] <= 10.0
    assert "Low Glycemic Load" in res_low["gl_category"]


def test_nova_processing_score():
    """Verify weighted NOVA score and ultra-processed food alert."""
    ingredients = [
        {"name": "Ragi Flour", "grams": 100.0, "nova_group": 1},
        {"name": "Ghee", "grams": 10.0, "nova_group": 2},
        {"name": "Artificially Sweetened Protein Bar", "grams": 50.0, "nova_group": 4},
    ]
    # Total grams = 160.0
    # Weighted sum = 1*100 + 2*10 + 4*50 = 100 + 20 + 200 = 320
    # Score = 320 / 160 = 2.0
    res = calculate_nova_processing_score(ingredients, total_grams=160.0)
    assert res["weighted_nova_score"] == 2.0
    assert len(res["ultra_processed_alerts"]) == 1
    assert "Artificially Sweetened" in res["ultra_processed_alerts"][0]["ingredient"]


def test_formulate_recipe_end_to_end():
    """Verify formulate_recipe calculates full macro, amino acid, and mineral synergies."""
    ingredients = [
        {"name": "Ragi", "grams": 60.0},
        {"name": "Toor Dal", "grams": 40.0},
        {"name": "Paneer", "grams": 100.0},
        {"name": "Moringa Leaves", "grams": 25.0},
        {"name": "Ghee", "grams": 10.0},
    ]

    report = formulate_recipe(ingredients, servings=1, title="Millet & Paneer Power Bowl")

    assert report["title"] == "Millet & Paneer Power Bowl"
    assert report["servings"] == 1
    assert report["total_weight_grams"] == 235.0

    macros = report["aggregate_macros"]
    assert macros["calories"] > 500.0
    assert macros["protein_g"] > 25.0
    assert macros["fiber_g"] > 10.0
    assert macros["net_carbs_g"] > 0.0

    # Caloric distribution
    cal_dist = report["caloric_distribution"]
    assert cal_dist["protein_pct"] > 0.0
    assert cal_dist["fat_pct"] > 0.0
    assert cal_dist["net_carbs_pct"] > 0.0

    # Amino Acid Profile
    aa_prof = report["amino_acid_profile"]
    assert aa_prof["leucine_per_serving_g"] >= 2.5  # Paneer + Toor + Ragi clears 2.5g Leucine
    assert aa_prof["clears_leucine_threshold"] is True

    # Micronutrient Synergy
    micros = report["micronutrient_synergy"]
    assert micros["potassium_mg"] > 500.0
    assert micros["calcium_mg"] > 400.0  # Ragi + Paneer + Moringa = huge calcium!
    assert micros["iron_mg"] > 3.0

    # Cleanliness score
    cleanliness = report["cleanliness_processing"]
    assert cleanliness["weighted_nova_score"] < 2.5
    assert len(cleanliness["ultra_processed_alerts"]) == 0


def test_optimize_recipe_macros():
    """Verify optimize_recipe_macros provides actionable suggestions for protein and carbs."""
    # High-carb, low-protein meal (150g Atta + 10g Ghee)
    ingredients = [
        {"name": "Atta", "grams": 150.0},
        {"name": "Ghee", "grams": 10.0},
    ]

    opt = optimize_recipe_macros(
        ingredients=ingredients,
        target_protein_g=40.0,
        max_carbs_g=30.0,
        servings=1,
    )

    cur = opt["current_evaluation"]
    assert cur["protein_per_serving_g"] < 30.0
    assert cur["net_carbs_per_serving_g"] > 70.0
    assert cur["clears_leucine_mps_threshold"] is False

    recs = opt["optimization_recommendations"]
    assert len(recs) >= 2

    # Check categories
    categories = [r["category"] for r in recs]
    assert any("Protein & Leucine" in c for c in categories)
    assert any("Carbohydrate Reduction" in c for c in categories)

    proj = opt["projected_optimized_macros"]
    assert proj["projected_protein_g"] >= 35.0
    assert proj["projected_net_carbs_g"] <= 30.0
