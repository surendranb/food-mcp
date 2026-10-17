# food-mcp

[![PyPI version](https://img.shields.io/pypi/v/food-mcp.svg)](https://pypi.org/project/food-mcp/)
[![npm version](https://img.shields.io/npm/v/food-mcp.svg)](https://www.npmjs.com/package/food-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Precision food chemistry, global nutrition databases (USDA, Open Food Facts, IFCT), and recipe formulation for AI agents.**

`food-mcp` equips LLMs and autonomous agents with exact molecular nutrition data: essential amino acid profiles (WHO/FAO 2007), Muscle Protein Synthesis (MPS) Leucine threshold verification, electrolyte and mineral synergy ($Na:K$ and $Ca:Mg$ ratios), Iron bioavailability dynamics, Glycemic Load (GL) calculation, and NOVA ultra-processed food detection.

---

## Quickstart

Run directly without manual installation using `uvx` (recommended) or `npx`:

```bash
# Python / uvx (zero install)
uvx food-mcp

# Or use the CLI alias
uvx --from food-mcp food-chemistry-mcp

# Node / npx (zero install thin bridge)
npx food-mcp
```

### MCP Client Configuration

Add `food-mcp` to your MCP client config (`claude_desktop_config.json`, `~/.cursor/mcp.json`, or Antigravity):

#### Using `uvx` (Recommended)
```json
{
  "mcpServers": {
    "food-mcp": {
      "command": "uvx",
      "args": ["--from", "food-mcp", "food-mcp"]
    }
  }
}
```

#### Using `npx`
```json
{
  "mcpServers": {
    "food-mcp": {
      "command": "npx",
      "args": ["-y", "food-mcp"]
    }
  }
}
```

---

## Architecture & Databases

| Database / Engine | Coverage | Highlights |
|---|---|---|
| **ICMR-NIN IFCT 2017** | 35+ core South Asian staples | Exact per-100g macros, calcium, iron, zinc, potassium, and full essential amino acid assays for Ragi, Jowar, Bajra, Toor dal, Moong dal, Paneer, Ghee, Moringa, Amla, etc. |
| **USDA FoodData Central** | Curated reference whole foods | High-yield proteins (Chicken breast, Wild Salmon, Eggs), plant lipids (Avocado, EVOO), and modern formulation staples (Hemp seeds, Lupin flour, Whey isolate, Nutritional yeast). |
| **Open Food Facts** | Global packaged barcodes & search | Millions of consumer products with real-time barcode lookup, ingredient lists, NOVA classification (1 to 4), and Nutri-Score. |
| **Molecular Nutrition Engine** | Mathematical formulation | WHO/FAO 2007 EAA pattern, 2.5g Leucine MPS threshold, $Na:K$ cardiovascular ratio, $Ca:Mg$ bone/vascular ratio, iron bioavailability pairing, and weighted Glycemic Load. |

---

## MCP Tools Reference

### 1. `lookup_food(query: str, region: str = "global", limit: int = 5)`
Searches across IFCT, USDA, and Open Food Facts. Returns matched food items with standard IDs (`ifct:ragi`, `usda:chicken_breast`, `off:737628064502`) and macro previews.
```json
{
  "query": "ragi",
  "region": "south_asia",
  "limit": 3
}
```

### 2. `get_food_chemistry(food_id_or_barcode: str)`
Returns the full molecular profile: per-100g calories, protein, fat, carbohydrates, fiber, net carbs, minerals ($Na, K, Ca, Mg, Fe, Zn$), 11 essential & semi-essential amino acids (mg), fatty acid breakdown, Glycemic Index, NOVA group, Nutri-Score, allergens, and additives.
```json
{
  "food_id_or_barcode": "ifct:ragi"
}
```

### 3. `formulate_recipe(ingredients: List[dict], servings: int = 1, title: Optional[str] = None)`
Evaluates a multi-ingredient dish or meal plan:
- **Aggregate & per-serving macros** (Calories, Protein, Fat, Carbs, Fiber, Net Carbs).
- **Caloric macro distribution** (% protein, % fat, % net carbs).
- **Amino Acid Completeness**: Compares against WHO/FAO 2007 adult scoring pattern, identifies limiting amino acid, and verifies if serving clears the **2.5g Leucine MPS threshold**.
- **Micronutrient Synergy**:
  - $Na:K$ ratio (evaluates against $< 1.0$ target).
  - $Ca:Mg$ ratio (evaluates against optimal $\approx 2:1$ physiological balance).
  - Iron bioavailability & ascorbic acid enhancement notes.
- **Glycemic Load (GL)**: Calculates weighted meal GI and categorizes GL ($\le 10$ Low, $11-19$ Medium, $\ge 20$ High).
- **Cleanliness / Processing Score**: Computes weighted NOVA score ($1.0 - 4.0$) and flags ultra-processed additives.

#### Example Input
```json
{
  "title": "High-Protein Millet & Paneer Bowl",
  "servings": 1,
  "ingredients": [
    { "name": "Ragi", "grams": 60 },
    { "name": "Toor Dal", "grams": 40 },
    { "name": "Paneer", "grams": 80 },
    { "name": "Moringa Leaves", "grams": 30 },
    { "name": "Ghee", "grams": 10 }
  ]
}
```

### 4. `optimize_recipe_macros(ingredients: List[dict], target_protein_g: float = 40.0, max_carbs_g: float = 30.0)`
Analyzes a recipe and provides actionable, quantitative adjustments:
- Recommends nutrient-dense swaps (e.g. swapping high-carb flours for lupin or almond flour, cauliflower rice).
- Recommends protein boosters (hemp seed hearts, nutritional yeast, paneer, whey isolate) to hit protein targets and clear the 2.5g Leucine threshold.
- Recommends mutual amino acid complementation (pairing Lysine-rich pulses with Methionine-rich seeds).
- Simulates projected post-optimization macros.

### 5. `lookup_barcode(barcode: str)`
Direct lookup of any global packaged food barcode via Open Food Facts API (`https://world.openfoodfacts.org/api/v2/product/{barcode}.json`).

### 6. `doctor()`
Runs diagnostic checks across local IFCT datasets, USDA database, Open Food Facts API latency, and skills availability.

### 7. `skills_list()` and `skill_read(name: str)`
Inspects and loads dynamic food chemistry playbooks directly into the agent's context.

### 8. `check_for_updates(force: bool = False)`
Checks PyPI for latest version and upgrade directives.

---

## Dynamic Skills

`food-mcp` includes decoupled playbooks that provide domain guidance:

1. **`recipe-formulation`**: Deep dive into caloric distribution, $Na:K$ and $Ca:Mg$ mineral ratios, iron bioavailability levers, and Glycemic Load categorization.
2. **`amino-acid-optimization`**: WHO/FAO 2007 reference adult pattern, Liebig's law of the minimum, 2.5g Leucine MPS threshold mechanics, and South Asian mutual supplementation.
3. **`ultra-processed-food-audit`**: NOVA classification rules, industrial cosmetic additives (emulsifiers, artificial sweeteners, maltodextrin), and gut mucosal implications.

Call `skill_read(name="recipe-formulation")` from your agent to load any skill.

---

## Telemetry & Privacy

`food-mcp` collects anonymous usage telemetry (tool name, latency, error taxonomy, OS/Python version) to prioritize dataset expansion and bug fixes:
- No ingredients, recipe titles, meal names, or user content are ever collected or logged.
- Opt out anytime by setting any of the following environment variables:
  ```bash
  export FOOD_MCP_TELEMETRY=false
  # or
  export MCP_TELEMETRY_OPT_OUT=1
  # or
  export DO_NOT_TRACK=1
  ```

---

## License

MIT License. Copyright (c) 2026 Surendran B.
