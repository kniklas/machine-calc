"""Unit tests for the drilling calculate() orchestration (T013 coverage).

Complements the dedicated User Story 2 library contract tests (Phase 4);
these tests exercise the Foundational-phase orchestration logic directly
since both User Story 1 (CLI) and User Story 2 (library) depend on it.
"""

import math

from machine_calc import UnitSystem, calculate


def test_success_metric():
    result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    assert result.error is None
    assert result.spindle_speed_rpm is not None
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.unit_system is UnitSystem.METRIC


def test_success_imperial_converts_output():
    metric = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    imperial = calculate(
        diameter=10 / 25.4,
        depth=25 / 25.4,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
    )

    assert imperial.error is None
    # Spindle speed (RPM) and machining time (minutes) are unit-independent.
    assert math.isclose(imperial.spindle_speed_rpm, metric.spindle_speed_rpm, rel_tol=1e-6)
    assert math.isclose(imperial.machining_time, metric.machining_time, rel_tol=1e-6)
    # Feed rate/torque/power differ because they are converted to imperial units.
    assert imperial.feed_rate != metric.feed_rate
    assert imperial.torque != metric.torque
    assert imperial.power_required != metric.power_required


def test_missing_material_returns_structured_error():
    result = calculate(diameter=10, depth=25, material="", tool="Carbide")
    assert result.error is not None
    assert result.error.code == "MISSING_MATERIAL"
    assert result.spindle_speed_rpm is None


def test_missing_tool_returns_structured_error():
    result = calculate(diameter=10, depth=25, material="Mild Steel", tool="")
    assert result.error is not None
    assert result.error.code == "MISSING_TOOL"


def test_unknown_material_returns_structured_error():
    result = calculate(diameter=10, depth=25, material="Unobtainium", tool="Carbide")
    assert result.error is not None
    assert result.error.code == "MISSING_MATERIAL"


def test_unknown_tool_returns_structured_error():
    result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Diamond")
    assert result.error is not None
    assert result.error.code == "MISSING_TOOL"


def test_invalid_diameter_returns_structured_error():
    result = calculate(diameter=0, depth=25, material="Mild Steel", tool="Carbide")
    assert result.error is not None
    assert result.error.code == "INVALID_DIAMETER"
    assert result.spindle_speed_rpm is None


def test_invalid_depth_returns_structured_error():
    result = calculate(diameter=10, depth=0, material="Mild Steel", tool="Carbide")
    assert result.error is not None
    assert result.error.code == "INVALID_DEPTH"


def test_feasibility_warning_when_power_exceeded():
    result = calculate(
        diameter=10, depth=25, material="Mild Steel", tool="Carbide", available_power=0.1
    )
    assert result.error is None
    assert result.feasibility_warning is not None


def test_no_feasibility_warning_when_power_sufficient():
    result = calculate(
        diameter=10, depth=25, material="Mild Steel", tool="Carbide", available_power=1000.0
    )
    assert result.error is None
    assert result.feasibility_warning is None


def test_no_feasibility_warning_when_power_omitted():
    result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    assert result.error is None
    assert result.feasibility_warning is None


def test_feasibility_warning_imperial_power_conversion():
    result = calculate(
        diameter=10 / 25.4,
        depth=25 / 25.4,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
        available_power=0.1,
    )
    assert result.error is None
    assert result.feasibility_warning is not None


def test_config_path_overrides_default_bounds(tmp_path):
    config_file = tmp_path / "machine-calc.toml"
    config_file.write_text("max_diameter_mm = 150\nmax_depth_mm = 600\n")

    result = calculate(
        diameter=120,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        config_path=str(config_file),
    )
    assert result.error is None
