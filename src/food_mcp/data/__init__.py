# SPDX-License-Identifier: MIT
"""Curated food nutrition datasets (IFCT and USDA)."""

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

__all__ = [
    "IFCT_DATABASE",
    "get_ifct_food",
    "list_ifct_foods",
    "search_ifct_foods",
    "USDA_DATABASE",
    "get_usda_food",
    "list_usda_foods",
    "search_usda_foods",
]
