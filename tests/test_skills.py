# SPDX-License-Identifier: MIT
"""Unit tests for dynamic skills layer."""

import json

from food_mcp.skills import (
    list_available_skills,
    read_skill_content,
    skill_read,
    skills_list,
)


def test_list_available_skills():
    """Verify that all three core skills are discovered."""
    skills = list_available_skills()
    assert "recipe-formulation" in skills
    assert "amino-acid-optimization" in skills
    assert "ultra-processed-food-audit" in skills


def test_skills_list_json():
    """Verify skills_list returns valid JSON with descriptions."""
    out = skills_list()
    data = json.loads(out)
    assert "skills" in data
    names = {s["name"] for s in data["skills"]}
    assert "recipe-formulation" in names
    assert "amino-acid-optimization" in names
    assert "ultra-processed-food-audit" in names


def test_skill_read_bundled():
    """Verify reading local bundled skill markdown content."""
    content = skill_read("recipe-formulation")
    assert "Precision Recipe Formulation" in content
    assert "Na:K" in content or "Sodium-to-Potassium" in content
    assert "Glycemic Load" in content

    aa_content = skill_read("amino-acid-optimization")
    assert "WHO/FAO 2007" in aa_content
    assert "Leucine" in aa_content

    upf_content = skill_read("ultra-processed-food-audit")
    assert "NOVA" in upf_content


def test_skill_read_unknown():
    """Verify graceful handling for non-existent skill."""
    content, success = read_skill_content("non-existent-skill-xyz")
    assert success is False
    assert "[INPUT_FIXABLE]" in content
    assert "Unknown skill" in content
