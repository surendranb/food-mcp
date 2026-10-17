# SPDX-License-Identifier: MIT
"""Unit tests for Open Food Facts client with network mocks and fallbacks."""

import json
from unittest.mock import MagicMock, patch

from food_mcp.client import FoodAPIClient


def test_client_parse_off_product():
    """Verify normalization of raw Open Food Facts product structure."""
    raw_prod = {
        "code": "737628064502",
        "product_name": "Organic Thai Peanut Sauce",
        "brands": "Thai Kitchen",
        "categories": "Sauces, Peanut Sauces",
        "ingredients_text": "Water, peanuts, coconut milk, sugar, salt",
        "nutriments": {
            "energy-kcal_100g": 240,
            "proteins_100g": 6.0,
            "fat_100g": 16.0,
            "saturated-fat_100g": 4.0,
            "carbohydrates_100g": 18.0,
            "fiber_100g": 2.0,
            "sodium_100g": 0.45,
            "potassium_100g": 0.25,
            "calcium_100g": 0.04,
            "iron_100g": 0.001,
        },
        "nova_group": 4,
        "nutriscore_grade": "d",
        "allergens_tags": ["en:peanuts"],
        "additives_tags": ["en:e415"],
    }

    client = FoodAPIClient()
    parsed = client._parse_off_product(raw_prod)

    assert parsed is not None
    assert parsed["id"] == "off:737628064502"
    assert parsed["barcode"] == "737628064502"
    assert "Thai Kitchen" in parsed["name"]
    p100 = parsed["per_100g"]
    assert p100["calories"] == 240.0
    assert p100["protein_g"] == 6.0
    assert p100["net_carbs_g"] == 16.0
    assert p100["sodium_mg"] == 450.0  # 0.45g -> 450mg
    assert p100["potassium_mg"] == 250.0  # 0.25g -> 250mg
    assert p100["nova_group"] == 4
    assert p100["nutri_score"] == "D"
    assert "peanuts" in p100["allergens"]
    assert "E415" in p100["additives"]


def test_fetch_barcode_success():
    """Verify barcode lookup using mocked successful HTTP response."""
    mock_payload = {
        "status": 1,
        "product": {
            "code": "3017620422003",
            "product_name": "Nutella",
            "brands": "Ferrero",
            "nutriments": {
                "energy-kcal_100g": 539,
                "proteins_100g": 6.3,
                "fat_100g": 30.9,
                "carbohydrates_100g": 57.5,
                "fiber_100g": 0.0,
            },
            "nova_group": 4,
            "nutriscore_grade": "e",
        },
    }

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    client = FoodAPIClient()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.fetch_barcode("3017620422003")

    assert res is not None
    assert "Nutella" in res["name"]
    assert res["per_100g"]["calories"] == 539.0
    assert res["per_100g"]["nova_group"] == 4


def test_fetch_barcode_not_found_or_timeout():
    """Verify graceful handling when barcode is not found or connection times out."""
    client = FoodAPIClient(timeout=0.1)

    # Simulated timeout exception
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        res = client.fetch_barcode("0000000000000")
        assert res is None

    # Empty barcode
    assert client.fetch_barcode("") is None
