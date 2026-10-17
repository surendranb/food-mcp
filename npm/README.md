# food-mcp

> Global unscoped npm package bridge for `food-mcp`: Precision food chemistry, global nutrition databases (USDA, Open Food Facts, IFCT), and recipe formulation for AI agents.

This npm package is a zero-overhead thin wrapper that invokes `uvx --from food-mcp food-mcp`.

## Quick Start

### Run with npx
```bash
npx food-mcp
```

### Claude Desktop / Cursor / Antigravity Configuration
Add to your `mcpServers` config:

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

Or directly via `uvx`:

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

## Features
- **30+ South Asian Staples (ICMR-NIN IFCT 2017)**: Ragi, Jowar, Bajra, Toor dal, Moong dal, Paneer, Ghee, Moringa, Turmeric, Cumin, etc.
- **USDA FoodData Central**: Curated global proteins, healthy fats, and modern formulation swaps.
- **Open Food Facts API**: Instant global barcode scanning and product search.
- **Amino Acid Completeness**: WHO/FAO 2007 reference adult pattern and 2.5g Leucine MPS threshold clearing.
- **Micronutrient Synergy**: $Na:K$ ratio, $Ca:Mg$ ratio, and Iron bioavailability analysis.
- **Glycemic Load & NOVA Score**: Meal GI/GL calculation and ultra-processed food detection.

See full documentation at [GitHub](https://github.com/surendranb/food-mcp).
