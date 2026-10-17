# SPDX-License-Identifier: MIT
"""Unit tests for server tool endpoints."""

import json
from unittest.mock import MagicMock, patch

from food_mcp.server import (
    check_for_updates,
    doctor,
    formulate_recipe,
    get_food_chemistry,
    lookup_barcode,
    lookup_food,
    optimize_recipe_macros,
    skill_read,
    skills_list,
)


def test_server_lookup_food():
    """Verify lookup_food tool returns valid JSON matching query."""
    res_str = lookup_food("ragi", region="south_asia", limit=3)
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["query"] == "ragi"
    assert data["count"] > 0
    assert any("Finger Millet" in f["name"] for f in data["foods"])


def test_server_get_food_chemistry():
    """Verify get_food_chemistry returns detailed molecular profile."""
    res_str = get_food_chemistry("ifct:toor_dal")
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["id"] == "ifct:toor_dal"
    assert "Pigeon Pea" in data["name"]
    assert data["per_100g"]["protein_g"] > 20.0
    assert data["per_100g"]["amino_acids_mg"]["lysine"] > 1000.0


def test_server_get_food_chemistry_not_found():
    """Verify get_food_chemistry returns input fixable message when not found."""
    res_str = get_food_chemistry("non_existent_food_12345")
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert "error" in data
    assert "[INPUT_FIXABLE]" in data["error"]


def test_server_formulate_recipe():
    """Verify formulate_recipe tool returns complete evaluation."""
    ingredients = [
        {"name": "Ragi", "grams": 80.0},
        {"name": "Paneer", "grams": 80.0},
    ]
    res_str = formulate_recipe(ingredients=ingredients, servings=1, title="Test Bowl")
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["title"] == "Test Bowl"
    assert data["aggregate_macros"]["protein_g"] > 15.0
    assert "amino_acid_profile" in data
    assert "micronutrient_synergy" in data
    assert "glycemic_impact" in data


def test_server_optimize_recipe_macros():
    """Verify optimize_recipe_macros tool returns recommendations."""
    ingredients = [
        {"name": "Whole Wheat Flour", "grams": 100.0},
    ]
    res_str = optimize_recipe_macros(ingredients=ingredients, target_protein_g=40.0, max_carbs_g=30.0)
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert "current_evaluation" in data
    assert "optimization_recommendations" in data
    assert len(data["optimization_recommendations"]) > 0


def test_server_lookup_barcode_mocked():
    """Verify lookup_barcode tool returns parsed barcode."""
    mock_prod = {
        "id": "off:123456789012",
        "barcode": "123456789012",
        "name": "Mock Oats",
        "per_100g": {"calories": 380.0, "protein_g": 13.0, "nova_group": 1},
    }
    with patch("food_mcp.server.default_client.fetch_barcode", return_value=mock_prod):
        res_str = lookup_barcode("123456789012")
        data = json.loads(res_str.split("\n\n[NOTICE")[0])
        assert data["barcode"] == "123456789012"
        assert data["name"] == "Mock Oats"


def test_server_doctor():
    """Verify doctor tool checks datasets and returns health status."""
    res_str = doctor()
    data = json.loads(res_str.split("\n\n[NOTICE")[0])
    assert data["status"] in ("healthy", "degraded")
    assert data["datasets"]["ifct_ninja_icmr"]["staples_count"] >= 30
    assert data["datasets"]["usda_curated"]["staples_count"] >= 12


def test_server_check_for_updates():
    """Verify check_for_updates tool executes cleanly."""
    res_str = check_for_updates(force=False)
    data = json.loads(res_str)
    assert data["package"] == "food-mcp"
    assert "current_version" in data
    assert "latest_version" in data
