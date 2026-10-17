# SPDX-License-Identifier: MIT
"""FastMCP server for precision food chemistry, global nutrition databases (USDA, Open Food Facts, IFCT), and recipe formulation."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(
        "food-mcp",
        title="Precision Food Chemistry & Global Nutrition MCP Server",
        version="0.1.0",
        website_url="https://github.com/surendranb/food-mcp",
    )
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("food-mcp")
    except ImportError:
        class DummyMCP:
            def tool(self, *args, **kwargs):
                def dec(fn):
                    return fn
                return dec
            def run(self):
                pass
        mcp = DummyMCP()

from food_mcp.client import default_client
from food_mcp.data.ifct_data import get_ifct_food, list_ifct_foods, search_ifct_foods
from food_mcp.data.usda_data import get_usda_food, list_usda_foods, search_usda_foods
from food_mcp.engine.recipe import formulate_recipe as _formulate_recipe
from food_mcp.engine.recipe import optimize_recipe_macros as _optimize_recipe_macros
from food_mcp.skills import (
    list_available_skills,
    read_skill_content,
    skill_read as _skill_read,
    skills_list as _skills_list,
)
from food_mcp.telemetry import (
    MCP_SERVER_VERSION,
    classify_exception,
    track_event,
    track_tool_call,
)

# ---------------------------------------------------------------------------
# Universal fleet update checker (async, non-blocking, 24h TTL)
# ---------------------------------------------------------------------------
_FLEET_CACHE_FILE = Path.home() / ".cache" / "mcp_fleet_updates.json"
_UPDATE_CHECK_TTL = 86400  # 24 hours


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        clean = re.sub(r"[^\d.]", "", str(v))
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def check_server_update(package_name: str, current_version: str, force_check: bool = False) -> dict:
    """Checks PyPI for latest version and returns update status and instructions."""
    now = time.time()
    cache: dict[str, Any] = {}
    if _FLEET_CACHE_FILE.exists():
        try:
            cache = json.loads(_FLEET_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    entry = cache.get(package_name, {})
    last_check = entry.get("last_checked", 0)
    latest_version = entry.get("latest_version", current_version)

    if force_check or (now - last_check > _UPDATE_CHECK_TTL):
        try:
            req = urllib.request.Request(
                f"https://pypi.org/pypi/{package_name}/json",
                headers={"User-Agent": f"{package_name}/{current_version}"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_version = data.get("info", {}).get("version", current_version)
                    cache[package_name] = {"latest_version": latest_version, "last_checked": now}
                    _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    _FLEET_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
        except Exception:
            pass

    cur_tuple = _parse_version(current_version)
    lat_tuple = _parse_version(latest_version)
    is_outdated = lat_tuple > cur_tuple

    return {
        "package": package_name,
        "current_version": current_version,
        "latest_version": latest_version,
        "is_outdated": is_outdated,
        "upgrade_command": f"uvx --upgrade {package_name}" if is_outdated else None,
    }


def get_upgrade_nudge(package_name: str, current_version: str) -> str:
    """Returns in-band upgrade directive if outdated, else empty string."""
    try:
        status = check_server_update(package_name, current_version)
        if status.get("is_outdated"):
            lat = status.get("latest_version")
            return f"\n\n[NOTICE: Update available for {package_name}: {current_version} -> {lat}. Run: {status.get('upgrade_command')}]"
    except Exception:
        pass
    return ""


def _external_resolver(ref: str) -> Optional[Dict[str, Any]]:
    """Helper to resolve barcode or external product via Open Food Facts client."""
    clean = ref.strip()
    if clean.startswith("off:"):
        clean = clean[4:]
    if clean.isdigit() and 8 <= len(clean) <= 14:
        prod = default_client.fetch_barcode(clean)
        if prod:
            return prod
    return None


# ---------------------------------------------------------------------------
# MCP Tool: lookup_food
# ---------------------------------------------------------------------------
@mcp.tool()
def lookup_food(query: str, region: str = "global", limit: int = 5) -> str:
    """Searches food chemistry databases across ICMR-NIN IFCT, USDA, and Open Food Facts.

    Returns matched foods with food IDs and per-100g macro previews.
    """
    t0 = time.perf_counter()
    tool_name = "lookup_food"
    try:
        q = query.strip()
        if not q:
            out = json.dumps({"error": "[INPUT_FIXABLE] Query cannot be empty", "results": []}, indent=2)
            track_tool_call(tool_name, 0.0, status="error", error_category="ValidationError", error_message="Empty query")
            return out

        max_results = max(1, min(limit, 25))
        reg = region.lower().strip()
        results: List[Dict[str, Any]] = []
        seen_ids = set()

        def add_preview(food_dict: Dict[str, Any]):
            fid = food_dict.get("id")
            if fid in seen_ids:
                return
            seen_ids.add(fid)
            p100 = food_dict.get("per_100g", {})
            results.append({
                "id": fid,
                "name": food_dict.get("name"),
                "category": food_dict.get("category", ""),
                "source": food_dict.get("source", ""),
                "per_100g_preview": {
                    "calories": p100.get("calories", 0.0),
                    "protein_g": p100.get("protein_g", 0.0),
                    "fat_g": p100.get("fat_g", 0.0),
                    "carbohydrates_g": p100.get("carbohydrates_g", 0.0),
                    "fiber_g": p100.get("fiber_g", 0.0),
                    "net_carbs_g": p100.get("net_carbs_g", 0.0),
                    "glycemic_index": p100.get("glycemic_index", 50),
                    "nova_group": p100.get("nova_group", 1),
                    "nutri_score": p100.get("nutri_score", "A"),
                },
            })

        if reg in ("india", "south_asia", "in"):
            for f in search_ifct_foods(q, limit=max_results):
                add_preview(f)
            if len(results) < max_results:
                for f in search_usda_foods(q, limit=max_results - len(results)):
                    add_preview(f)
        else:
            # Global: Search IFCT, USDA, and Open Food Facts
            for f in search_ifct_foods(q, limit=max_results):
                add_preview(f)
            for f in search_usda_foods(q, limit=max_results):
                add_preview(f)
            if len(results) < max_results:
                off_prods = default_client.search_open_food_facts(q, limit=max_results - len(results))
                for f in off_prods:
                    add_preview(f)

        final_results = results[:max_results]
        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps({
            "query": query,
            "region": region,
            "count": len(final_results),
            "foods": final_results,
        }, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)

        track_tool_call(tool_name, duration_ms, status="success", rows_returned=len(final_results), result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] lookup_food failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: get_food_chemistry
# ---------------------------------------------------------------------------
@mcp.tool()
def get_food_chemistry(food_id_or_barcode: str) -> str:
    """Returns the full molecular profile for a food ID or packaged barcode:

    macros, micros, amino acids, fatty acids, NOVA group (1 to 4), Nutri-Score, allergens, and additives.
    """
    t0 = time.perf_counter()
    tool_name = "get_food_chemistry"
    try:
        ref = food_id_or_barcode.strip()
        if not ref:
            return json.dumps({"error": "[INPUT_FIXABLE] food_id_or_barcode cannot be empty"}, indent=2)

        # 1. Check IFCT
        profile = None
        if ref.startswith("ifct:") or get_ifct_food(ref):
            profile = get_ifct_food(ref)

        # 2. Check USDA
        if not profile and (ref.startswith("usda:") or get_usda_food(ref)):
            profile = get_usda_food(ref)

        # 3. Check Open Food Facts Barcode
        clean_code = ref[4:] if ref.startswith("off:") else ref
        if not profile and clean_code.isdigit() and 8 <= len(clean_code) <= 14:
            profile = default_client.fetch_barcode(clean_code)

        # 4. Search fallback
        if not profile:
            matches = search_ifct_foods(ref, limit=1)
            if matches:
                profile = matches[0]
        if not profile:
            matches = search_usda_foods(ref, limit=1)
            if matches:
                profile = matches[0]

        if not profile:
            duration_ms = (time.perf_counter() - t0) * 1000
            track_tool_call(tool_name, duration_ms, status="error", error_category="NotFoundError", error_message="Food profile not found")
            return json.dumps({
                "error": f"[INPUT_FIXABLE] Food profile '{ref}' not found.",
                "hint": "Try searching via lookup_food(query='<name>') to find the exact food ID or barcode.",
            }, indent=2)

        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps(profile, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", rows_returned=1, result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] get_food_chemistry failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: formulate_recipe
# ---------------------------------------------------------------------------
@mcp.tool()
def formulate_recipe(ingredients: List[dict], servings: int = 1, title: Optional[str] = None) -> str:
    """Formulates a multi-ingredient recipe and returns aggregate and per-serving macros,

    caloric distribution, amino acid completeness (WHO/FAO 2007 pattern + 2.5g Leucine MPS threshold),
    micronutrient synergies (Na:K ratio, Ca:Mg ratio, Iron bioavailability),
    glycemic impact (GI and Glycemic Load), and cleanliness score (weighted NOVA).
    """
    t0 = time.perf_counter()
    tool_name = "formulate_recipe"
    try:
        if not ingredients or not isinstance(ingredients, list):
            return json.dumps({"error": "[INPUT_FIXABLE] ingredients must be a non-empty list of dicts (e.g. [{'name': 'Ragi', 'grams': 100}])"}, indent=2)

        report = _formulate_recipe(
            ingredients=ingredients,
            servings=servings,
            title=title,
            external_lookup_fn=_external_resolver,
        )

        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps(report, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", rows_returned=len(report.get("ingredients", [])), result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] formulate_recipe failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: optimize_recipe_macros
# ---------------------------------------------------------------------------
@mcp.tool()
def optimize_recipe_macros(
    ingredients: List[dict],
    target_protein_g: float = 40.0,
    max_carbs_g: float = 30.0,
    servings: int = 1,
) -> str:
    """Analyzes a recipe and suggests precise gram adjustments or nutrient-dense swaps

    (e.g., swapping flour for lupin/almond flour, adding hemp seeds, paneer, nutritional yeast)
    to hit target macros and clear the 2.5g Leucine MPS threshold.
    """
    t0 = time.perf_counter()
    tool_name = "optimize_recipe_macros"
    try:
        if not ingredients or not isinstance(ingredients, list):
            return json.dumps({"error": "[INPUT_FIXABLE] ingredients must be a non-empty list of dicts"}, indent=2)

        report = _optimize_recipe_macros(
            ingredients=ingredients,
            target_protein_g=target_protein_g,
            max_carbs_g=max_carbs_g,
            servings=servings,
            external_lookup_fn=_external_resolver,
        )

        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps(report, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", rows_returned=len(report.get("optimization_recommendations", [])), result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] optimize_recipe_macros failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: lookup_barcode
# ---------------------------------------------------------------------------
@mcp.tool()
def lookup_barcode(barcode: str) -> str:
    """Instant lookup of any global packaged food barcode via Open Food Facts API."""
    t0 = time.perf_counter()
    tool_name = "lookup_barcode"
    try:
        clean = barcode.strip().replace(" ", "").replace("-", "")
        if not clean:
            return json.dumps({"error": "[INPUT_FIXABLE] Barcode cannot be empty"}, indent=2)

        prod = default_client.fetch_barcode(clean)
        if not prod:
            duration_ms = (time.perf_counter() - t0) * 1000
            track_tool_call(tool_name, duration_ms, status="error", error_category="NotFoundError", error_message="Barcode not found")
            return json.dumps({
                "error": f"[INPUT_FIXABLE] Barcode '{clean}' was not found in Open Food Facts.",
                "barcode": clean,
            }, indent=2)

        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps(prod, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", rows_returned=1, result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] lookup_barcode failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: doctor
# ---------------------------------------------------------------------------
@mcp.tool()
def doctor() -> str:
    """Tests connectivity to Open Food Facts, USDA, and local IFCT dataset."""
    t0 = time.perf_counter()
    tool_name = "doctor"
    try:
        # Check local datasets
        ifct_count = len(list_ifct_foods())
        usda_count = len(list_usda_foods())

        # Check Open Food Facts connectivity
        off_ok = False
        off_latency_ms = 0.0
        try:
            pt0 = time.perf_counter()
            req = urllib.request.Request(
                "https://world.openfoodfacts.org",
                headers={"User-Agent": "food-mcp/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                off_ok = resp.status in (200, 301, 302)
                off_latency_ms = round((time.perf_counter() - pt0) * 1000, 1)
        except Exception:
            off_ok = False

        status_report = {
            "status": "healthy" if ifct_count > 0 and usda_count > 0 else "degraded",
            "server_version": MCP_SERVER_VERSION,
            "datasets": {
                "ifct_ninja_icmr": {
                    "status": "ok" if ifct_count >= 30 else "incomplete",
                    "staples_count": ifct_count,
                    "description": "ICMR-NIN Indian Food Composition Tables 2017 embedded",
                },
                "usda_curated": {
                    "status": "ok" if usda_count >= 10 else "incomplete",
                    "staples_count": usda_count,
                    "description": "USDA FoodData Central curated reference whole foods & swaps",
                },
            },
            "connectivity": {
                "open_food_facts": {
                    "endpoint": "https://world.openfoodfacts.org",
                    "reachable": off_ok,
                    "latency_ms": off_latency_ms,
                },
            },
            "skills": {
                "available": list_available_skills(),
            },
        }

        duration_ms = (time.perf_counter() - t0) * 1000
        out = json.dumps(status_report, indent=2) + get_upgrade_nudge("food-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": f"[SYSTEM_ERROR] doctor failed: {err_msg}"}, indent=2)


# ---------------------------------------------------------------------------
# MCP Tool: skills_list
# ---------------------------------------------------------------------------
@mcp.tool()
def skills_list() -> str:
    """List available food chemistry and recipe optimization skills."""
    t0 = time.perf_counter()
    tool_name = "skills_list"
    try:
        out = _skills_list()
        duration_ms = (time.perf_counter() - t0) * 1000
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return json.dumps({"error": err_msg})


# ---------------------------------------------------------------------------
# MCP Tool: skill_read
# ---------------------------------------------------------------------------
@mcp.tool()
def skill_read(name: str) -> str:
    """Read a specific food chemistry skill/playbook by name."""
    t0 = time.perf_counter()
    tool_name = "skill_read"
    try:
        out = _skill_read(name)
        duration_ms = (time.perf_counter() - t0) * 1000
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: check_for_updates
# ---------------------------------------------------------------------------
@mcp.tool()
def check_for_updates(force: bool = False) -> str:
    """Check PyPI for the latest version of food-mcp."""
    t0 = time.perf_counter()
    tool_name = "check_for_updates"
    try:
        status = check_server_update("food-mcp", MCP_SERVER_VERSION, force_check=force)
        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(status, indent=2)
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out_str))
        return out_str
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


def main():
    """Main entrypoint for MCP server execution over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
