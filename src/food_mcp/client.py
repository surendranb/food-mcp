# SPDX-License-Identifier: MIT
"""Client for Open Food Facts and global nutrition API queries."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

OPEN_FOOD_FACTS_BASE = "https://world.openfoodfacts.org"
USER_AGENT = "food-mcp/0.1.0 (https://github.com/surendranb/food-mcp; reachsuren@gmail.com)"


class FoodAPIClient:
    """HTTP client for Open Food Facts API with caching and error handling."""

    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        self._cache: Dict[str, Any] = {}

    def fetch_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Fetch packaged food chemistry and metadata by barcode from Open Food Facts."""
        clean_code = barcode.strip().replace(" ", "").replace("-", "")
        if not clean_code or not clean_code.isdigit():
            return None

        cache_key = f"barcode:{clean_code}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{OPEN_FOOD_FACTS_BASE}/api/v2/product/{clean_code}.json"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == 1 and "product" in data:
                        parsed = self._parse_off_product(data["product"])
                        self._cache[cache_key] = parsed
                        return parsed
        except Exception:
            pass

        return None

    def search_open_food_facts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search products on Open Food Facts by keyword."""
        q = query.strip()
        if not q:
            return []

        cache_key = f"search:{q}:{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = urllib.parse.urlencode({
            "search_terms": q,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": max(1, limit),
        })
        url = f"{OPEN_FOOD_FACTS_BASE}/cgi/search.pl?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    products = data.get("products", [])
                    results = []
                    for prod in products[:limit]:
                        parsed = self._parse_off_product(prod)
                        if parsed:
                            results.append(parsed)
                    self._cache[cache_key] = results
                    return results
        except Exception:
            pass

        return []

    def _parse_off_product(self, prod: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize an Open Food Facts product dictionary into standard schema."""
        code = prod.get("code") or prod.get("_id") or ""
        name = prod.get("product_name") or prod.get("product_name_en") or "Unknown Product"
        brands = prod.get("brands", "")
        full_name = f"{name} ({brands})" if brands and brands not in name else name

        nutriments = prod.get("nutriments", {})

        calories = float(nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0.0)
        protein = float(nutriments.get("proteins_100g") or nutriments.get("proteins") or 0.0)
        fat = float(nutriments.get("fat_100g") or nutriments.get("fat") or 0.0)
        saturated_fat = float(nutriments.get("saturated-fat_100g") or 0.0)
        carbs = float(nutriments.get("carbohydrates_100g") or nutriments.get("carbohydrates") or 0.0)
        sugars = float(nutriments.get("sugars_100g") or 0.0)
        fiber = float(nutriments.get("fiber_100g") or nutriments.get("fiber") or 0.0)
        net_carbs = max(0.0, carbs - fiber)

        # Minerals: OFF stores sodium in grams or salt in grams
        sodium_g = float(nutriments.get("sodium_100g") or 0.0)
        if sodium_g == 0.0 and "salt_100g" in nutriments:
            sodium_g = float(nutriments.get("salt_100g", 0.0)) / 2.5
        sodium_mg = sodium_g * 1000.0

        potassium_mg = float(nutriments.get("potassium_100g") or 0.0) * 1000.0
        calcium_mg = float(nutriments.get("calcium_100g") or 0.0) * 1000.0
        iron_mg = float(nutriments.get("iron_100g") or 0.0) * 1000.0

        # Processing & quality scores
        nova = prod.get("nova_group")
        try:
            nova_int = int(nova) if nova is not None else 3
        except (ValueError, TypeError):
            nova_int = 3

        nutri_score = str(prod.get("nutriscore_grade") or "unknown").upper()

        allergens = [a.replace("en:", "").strip() for a in prod.get("allergens_tags", [])]
        additives = [ad.replace("en:", "").upper().strip() for ad in prod.get("additives_tags", [])]

        return {
            "id": f"off:{code}" if code else f"off:{name.lower().replace(' ', '_')}",
            "barcode": code,
            "name": full_name,
            "category": prod.get("categories", "Packaged Food"),
            "ingredients_text": prod.get("ingredients_text", ""),
            "per_100g": {
                "calories": round(calories, 1),
                "protein_g": round(protein, 2),
                "fat_g": round(fat, 2),
                "carbohydrates_g": round(carbs, 2),
                "sugars_g": round(sugars, 2),
                "fiber_g": round(fiber, 2),
                "net_carbs_g": round(net_carbs, 2),
                "sodium_mg": round(sodium_mg, 1),
                "potassium_mg": round(potassium_mg, 1),
                "calcium_mg": round(calcium_mg, 1),
                "magnesium_mg": 0.0,
                "iron_mg": round(iron_mg, 2),
                "zinc_mg": 0.0,
                "glycemic_index": 55,
                "nova_group": nova_int,
                "nutri_score": nutri_score,
                "amino_acids_mg": {},
                "fatty_acids_g": {
                    "saturated": round(saturated_fat, 2),
                    "monounsaturated": 0.0,
                    "polyunsaturated": 0.0,
                    "trans": 0.0,
                },
                "allergens": allergens,
                "additives": additives,
            },
            "source": "Open Food Facts",
        }


default_client = FoodAPIClient()
