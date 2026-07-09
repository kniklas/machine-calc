"""Unit tests for the material and drilling-tool registries (T018)."""

from machine_calc.operations.drilling.tools import TOOL_REGISTRY, get_tool, list_tools
from machine_calc.registry import MATERIAL_REGISTRY, get_material, list_materials


def test_material_names_are_unique():
    names = list_materials()
    assert len(names) == len(set(names))
    assert len(names) >= 1


def test_all_materials_have_positive_reference_values():
    for material in MATERIAL_REGISTRY.values():
        assert material.reference_cutting_speed_m_min > 0
        assert material.reference_feed_per_rev_mm > 0
        assert material.specific_cutting_force_kc > 0


def test_get_material_returns_none_for_unknown():
    assert get_material("Unobtainium") is None


def test_get_material_returns_expected_entry():
    material = get_material("Mild Steel")
    assert material is not None
    assert material.name == "Mild Steel"


def test_tool_names_are_unique():
    names = list_tools()
    assert len(names) == len(set(names))
    assert len(names) >= 1


def test_all_tools_have_positive_factors():
    for tool in TOOL_REGISTRY.values():
        assert tool.cutting_speed_factor > 0
        assert tool.feed_factor > 0


def test_get_tool_returns_none_for_unknown():
    assert get_tool("Diamond-Coated Unobtainium") is None


def test_get_tool_returns_expected_entry():
    tool = get_tool("Carbide")
    assert tool is not None
    assert tool.name == "Carbide"


def test_material_validate_rejects_non_positive_fields():
    import pytest

    from machine_calc.registry import WorkpieceMaterial
    from machine_calc.registry import _validate as validate_material

    with pytest.raises(ValueError):
        validate_material(WorkpieceMaterial("Bad", 0, 0.2, 1900.0))
    with pytest.raises(ValueError):
        validate_material(WorkpieceMaterial("Bad", 25.0, 0, 1900.0))
    with pytest.raises(ValueError):
        validate_material(WorkpieceMaterial("Bad", 25.0, 0.2, 0))


def test_tool_validate_rejects_non_positive_fields():
    import pytest

    from machine_calc.operations.drilling.tools import DrillingTool
    from machine_calc.operations.drilling.tools import _validate as validate_tool

    with pytest.raises(ValueError):
        validate_tool(DrillingTool("Bad", 0, 1.0))
    with pytest.raises(ValueError):
        validate_tool(DrillingTool("Bad", 1.0, 0))
