"""Unit tests for calculate_turning_feed_rate_constrained_metrics()
(specs/020-turning-feed-per-rotation FR-004/FR-005, research.md #2).

Mirrors tests/unit/processes/machining/turning/test_formulas_at_rpm.py's
style for the other two derived-metrics helpers.
"""

import math

from mfgparams.processes.machining.turning.formulas import (
    calculate_turning_feed_rate_constrained_metrics,
    calculate_turning_metrics,
)
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material


def test_spindle_speed_matches_standard_modes_derivation():
    """FR-005: spindle speed is derived exactly as standard mode does, from
    cutting speed and diameter -- not from the supplied feed rate."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    standard = calculate_turning_metrics(40, 2, 100, material, tool)
    constrained = calculate_turning_feed_rate_constrained_metrics(
        40, 2, 100, material, tool, target_feed_per_rev_mm=0.5
    )

    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)


def test_feed_per_rev_mm_echoes_the_supplied_value():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    constrained = calculate_turning_feed_rate_constrained_metrics(
        40, 2, 100, material, tool, target_feed_per_rev_mm=0.5
    )

    assert constrained.feed_per_rev_mm == 0.5


def test_dependent_metrics_recomputed_from_the_supplied_feed_rate():
    """cutting_force = Kc * ap * fn depends directly on feed per revolution
    (unlike drilling's/milling's torque), so it changes from the
    material/tool-derived nominal value when a different feed is supplied."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    standard = calculate_turning_metrics(40, 2, 100, material, tool)
    constrained = calculate_turning_feed_rate_constrained_metrics(
        40, 2, 100, material, tool, target_feed_per_rev_mm=0.5
    )

    assert not math.isclose(constrained.feed_per_rev_mm, standard.feed_per_rev_mm, rel_tol=1e-9)
    assert not math.isclose(constrained.cutting_force_n, standard.cutting_force_n, rel_tol=1e-9)
    assert not math.isclose(constrained.torque_nm, standard.torque_nm, rel_tol=1e-9)
    assert not math.isclose(constrained.feed_rate_mm_min, standard.feed_rate_mm_min, rel_tol=1e-9)
    # Fc = Kc * ap * fn = 1900 * 2 * 0.5
    assert math.isclose(constrained.cutting_force_n, 1900.0 * 2 * 0.5, rel_tol=1e-9)
    assert math.isclose(
        constrained.feed_rate_mm_min, constrained.spindle_speed_rpm * 0.5, rel_tol=1e-9
    )


def test_all_registered_materials_and_tools_produce_positive_results():
    from mfgparams.processes.machining.turning.tools import list_turning_tools
    from mfgparams.registry import list_materials

    for material_name in list_materials():
        for tool_name in list_turning_tools():
            material = get_material(material_name)
            tool = get_turning_tool(tool_name)
            metrics = calculate_turning_feed_rate_constrained_metrics(
                20, 1, 50, material, tool, target_feed_per_rev_mm=0.15
            )
            assert metrics.spindle_speed_rpm > 0
            assert metrics.feed_per_rev_mm == 0.15
            assert metrics.feed_rate_mm_min > 0
            assert metrics.machining_time_min > 0
            assert metrics.cutting_force_n > 0
            assert metrics.torque_nm > 0
            assert metrics.power_kw > 0
