# SPDX-License-Identifier: MIT
"""Unit tests for curated IFCT and USDA nutrition datasets."""

from food_mcp.data.ifct_data import (
    IFCT_DATABASE,
    get_ifct_food,
    list_ifct_foods,
    search_ifct_foods,
)
from food_mcp.data.usda_data import (
    USDA_DATABASE,
    get_usda_food,
    list_usda_foods,
    search_usda_foods,
)


def test_ifct_staples_count_and_keys():
    """Verify IFCT dataset contains 30+ core South Asian staples with required fields."""
    foods = list_ifct_foods()
    assert len(foods) >= 30, f"Expected >= 30 IFCT staples, found {len(foods)}"

    required_per_100g = [
        "calories", "protein_g", "fat_g", "carbohydrates_g", "fiber_g",
        "net_carbs_g", "sodium_mg", "potassium_mg", "calcium_mg",
        "magnesium_mg", "iron_mg", "zinc_mg", "glycemic_index", "nova_group",
    ]

    for f in foods:
        assert "id" in f and f["id"].startswith("ifct:")
        assert "name" in f and len(f["name"]) > 0
        p100 = f.get("per_100g", {})
        for req in required_per_100g:
            assert req in p100, f"Missing {req} in {f['id']}"
            assert isinstance(p100[req], (int, float))

        # Check amino acids
        aa = p100.get("amino_acids_mg", {})
        assert isinstance(aa, dict)
        if p100["protein_g"] > 2.0:
            assert "leucine" in aa, f"Missing leucine in protein-bearing food {f['id']}"
            assert "lysine" in aa, f"Missing lysine in {f['id']}"


def test_ifct_lookup_and_search():
    """Verify direct lookup and search capabilities in IFCT."""
    ragi = get_ifct_food("ifct:ragi")
    assert ragi is not None
    assert "Finger Millet" in ragi["name"]
    assert ragi["per_100g"]["calcium_mg"] >= 300.0  # High calcium signature

    # Lookup without prefix
    toor = get_ifct_food("toor_dal")
    assert toor is not None
    assert toor["per_100g"]["protein_g"] >= 20.0

    # Search by English name
    matches = search_ifct_foods("moringa", limit=5)
    assert len(matches) > 0
    assert any("Moringa" in m["name"] for m in matches)

    # Search by vernacular name
    matches_tam = search_ifct_foods("Kezhvaragu", limit=5)
    assert len(matches_tam) > 0
    assert matches_tam[0]["id"] == "ifct:ragi"

    # Search by Hindi vernacular
    matches_hin = search_ifct_foods("Sarson", limit=5)
    assert len(matches_hin) > 0


def test_usda_staples_and_swaps():
    """Verify curated USDA dataset contains reference whole foods and modern swaps."""
    foods = list_usda_foods()
    assert len(foods) >= 12, f"Expected >= 12 USDA staples, found {len(foods)}"

    chicken = get_usda_food("usda:chicken_breast")
    assert chicken is not None
    assert chicken["per_100g"]["protein_g"] >= 20.0
    assert chicken["per_100g"]["amino_acids_mg"]["leucine"] >= 1500.0

    hemp = get_usda_food("hemp_seeds")
    assert hemp is not None
    assert hemp["per_100g"]["protein_g"] >= 30.0
    assert hemp["per_100g"]["magnesium_mg"] >= 600.0

    lupin = get_usda_food("lupin_flour")
    assert lupin is not None
    assert lupin["per_100g"]["protein_g"] >= 35.0

    # Search USDA
    results = search_usda_foods("salmon", limit=3)
    assert len(results) > 0
    assert "Salmon" in results[0]["name"]
