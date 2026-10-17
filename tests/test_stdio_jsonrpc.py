# SPDX-License-Identifier: MIT
"""Native MCP protocol stdio JSON-RPC test for food-mcp."""

import asyncio
import os
import sys
import pytest

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_native_mcp_stdio_jsonrpc():
    """Verify end-to-end native MCP stdio communication over JSON-RPC."""
    env = dict(os.environ)
    env["PYTHONPATH"] = f"src:{env.get('PYTHONPATH', '')}"
    env["FOOD_MCP_TELEMETRY"] = "false"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "food_mcp.server"],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize
            init_res = await session.initialize()
            assert init_res.server_info.name == "food-mcp"

            # 2. List Tools
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            expected_tools = {
                "lookup_food",
                "get_food_chemistry",
                "formulate_recipe",
                "optimize_recipe_macros",
                "lookup_barcode",
                "doctor",
                "skills_list",
                "skill_read",
                "check_for_updates",
            }
            assert expected_tools.issubset(tool_names)

            # 3. Call doctor tool
            doc_res = await session.call_tool("doctor", {})
            assert len(doc_res.content) > 0
            doc_text = doc_res.content[0].text
            assert "datasets" in doc_text
            assert "ifct_ninja_icmr" in doc_text

            # 4. Call skills_list tool
            skills_res = await session.call_tool("skills_list", {})
            assert len(skills_res.content) > 0
            skills_text = skills_res.content[0].text
            assert "recipe-formulation" in skills_text

            # 5. Call lookup_food tool
            food_res = await session.call_tool("lookup_food", {"query": "ragi"})
            assert len(food_res.content) > 0
            food_text = food_res.content[0].text
            assert "Finger Millet" in food_text
