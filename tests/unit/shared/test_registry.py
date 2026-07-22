"""Unit tests for the material and drilling-tool registries (T018)."""

import math

import pytest

from machine_calc.operations.drilling.tools import TOOL_REGISTRY, get_tool, list_tools
from machine_calc.registry import MATERIAL_REGISTRY, WorkpieceMaterial, get_material, list_materials
from machine_calc.registry_config import RegistryConfigError


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


# --- User Story 1: zero-config regression parity (T015) ---

_EXPECTED_BUNDLED_MATERIALS = {
    "Mild Steel": (25.0, 0.20, 1900.0),
    "Stainless Steel": (15.0, 0.15, 2400.0),
    "Aluminum": (60.0, 0.25, 700.0),
    "Cast Iron": (20.0, 0.20, 1500.0),
    "Brass": (45.0, 0.20, 800.0),
    "Titanium": (12.0, 0.10, 2100.0),
}


def test_list_materials_zero_config_matches_pre_feature_names_and_values():
    names = list_materials()
    assert names == list(_EXPECTED_BUNDLED_MATERIALS.keys())
    for name, (speed, feed, force) in _EXPECTED_BUNDLED_MATERIALS.items():
        material = get_material(name)
        assert material is not None
        assert math.isclose(material.reference_cutting_speed_m_min, speed, rel_tol=1e-9)
        assert math.isclose(material.reference_feed_per_rev_mm, feed, rel_tol=1e-9)
        assert math.isclose(material.specific_cutting_force_kc, force, rel_tol=1e-9)


def test_get_material_zero_config_none_path_matches_no_config_path():
    assert get_material("Mild Steel", None) == get_material("Mild Steel")


# --- User Story 2: override/append via user-supplied config file (T026) ---


def test_material_override_takes_effect(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text(
        """
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 28.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0
        """
    )
    overridden = get_material("Mild Steel", str(path))
    assert overridden is not None
    assert math.isclose(overridden.reference_cutting_speed_m_min, 28.0, rel_tol=1e-9)
    # Bundled-only lookup is unaffected.
    default_material = get_material("Mild Steel")
    assert math.isclose(default_material.reference_cutting_speed_m_min, 25.0, rel_tol=1e-9)


def test_material_append_new_name(tmp_path):
    path = tmp_path / "add.toml"
    path.write_text(
        """
        [[materials]]
        name = "Bronze"
        reference_cutting_speed = 45.0
        reference_feed_per_rev = 0.18
        specific_cutting_force = 750.0
        """
    )
    names = list_materials(config_path=str(path))
    assert "Bronze" in names
    assert "Mild Steel" in names
    assert "Bronze" not in list_materials()


def test_material_unaffected_built_ins_untouched(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text(
        """
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 28.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0
        """
    )
    aluminum = get_material("Aluminum", str(path))
    assert aluminum is not None
    assert math.isclose(aluminum.reference_cutting_speed_m_min, 60.0, rel_tol=1e-9)


def test_material_config_omitting_flag_reproduces_zero_config():
    assert list_materials(config_path=None) == list_materials()


# --- User Story 3: display_name / translations (T035, T037) ---


def test_display_name_returns_translation_when_present():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0, translations={"fr": "Essai"})
    assert material.display_name("fr") == "Essai"


def test_display_name_falls_back_to_english_when_locale_absent():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0, translations={"fr": "Essai"})
    assert material.display_name("de") == "Test"


def test_display_name_falls_back_to_english_when_no_translations():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0)
    assert material.display_name("fr") == "Test"


def test_translation_merge_preserves_untouched_locale(tmp_path):
    path = tmp_path / "translations.toml"
    path.write_text(
        """
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 25.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0

        [materials.translations]
        de = "Weichstahl"
        """
    )
    material = get_material("Mild Steel", str(path))
    assert material is not None
    assert material.translations.get("de") == "Weichstahl"


# --- User Story 4: imperial-declared unit conversion (T040) ---


def test_imperial_declared_material_converts_to_expected_metric(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text(
        """
        [[materials]]
        name = "Bronze Imperial"
        reference_cutting_speed = 250.0
        reference_feed_per_rev = 0.008
        specific_cutting_force = 130000.0
        unit_system = "imperial"
        """
    )
    material = get_material("Bronze Imperial", str(path))
    assert material is not None
    assert material.unit_system == "imperial"
    assert math.isclose(material.reference_cutting_speed_m_min, 76.2, rel_tol=1e-3)
    assert math.isclose(material.reference_feed_per_rev_mm, 0.2032, rel_tol=1e-3)
    assert math.isclose(material.specific_cutting_force_kc, 896.3, rel_tol=1e-3)


def test_imperial_declared_material_matches_metric_authored_equivalent(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text(
        """
        [[materials]]
        name = "Bronze Imperial"
        reference_cutting_speed = 250.0
        reference_feed_per_rev = 0.008
        specific_cutting_force = 130000.0
        unit_system = "imperial"

        [[materials]]
        name = "Bronze Metric"
        reference_cutting_speed = 76.2
        reference_feed_per_rev = 0.2032
        specific_cutting_force = 896.3
        """
    )
    imperial = get_material("Bronze Imperial", str(path))
    metric = get_material("Bronze Metric", str(path))
    assert imperial is not None and metric is not None
    assert math.isclose(
        imperial.reference_cutting_speed_m_min,
        metric.reference_cutting_speed_m_min,
        rel_tol=1e-3,
    )
    assert math.isclose(
        imperial.reference_feed_per_rev_mm, metric.reference_feed_per_rev_mm, rel_tol=1e-3
    )
    assert math.isclose(
        imperial.specific_cutting_force_kc, metric.specific_cutting_force_kc, rel_tol=1e-3
    )


def test_invalid_entry_raises_registry_config_error(tmp_path):
    path = tmp_path / "missing_field.toml"
    path.write_text(
        """
        [[materials]]
        name = "Incomplete"
        reference_cutting_speed = 25.0
        specific_cutting_force = 1900.0
        """
    )
    with pytest.raises(RegistryConfigError):
        get_material("Incomplete", str(path))
