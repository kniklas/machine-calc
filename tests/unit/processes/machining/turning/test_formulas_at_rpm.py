"""Unit tests for calculate_turning_metrics_at_rpm() and the power-scaling
helper, mirroring
tests/unit/processes/machining/drilling/test_formulas_at_rpm.py.

Covers: nominal-equals-standard case, boundary case where available power
exactly equals nominal power (asserting the no-reduction/no-op path,
math.isclose(rel_tol=1e-9)), reduced-RPM case, and zero/negative available
power. Added per Copilot review finding: formulas.py previously had no
direct unit tests.
"""

import math

import pytest

from mfgparams.processes.machining.turning.formulas import (
    calculate_turning_metrics,
    calculate_turning_metrics_at_rpm,
    calculate_turning_power_constrained_metrics,
)
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material


def test_at_rpm_matches_standard_when_given_the_nominal_rpm():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    at_rpm = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, nominal.spindle_speed_rpm)

    assert math.isclose(at_rpm.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(at_rpm.torque_nm, nominal.torque_nm, rel_tol=1e-9)
    assert math.isclose(at_rpm.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_at_rpm_cutting_force_and_torque_independent_of_spindle_speed():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    low = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 100)
    high = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 5000)

    # Cutting force and torque depend only on diameter/depth-of-cut/
    # material/tool, not spindle speed (research.md #1).
    assert math.isclose(low.cutting_force_n, high.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(low.torque_nm, high.torque_nm, rel_tol=1e-9)
    assert low.power_kw < high.power_kw


def test_power_constrained_reduces_spindle_speed_when_budget_below_nominal():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    budget_kw = nominal.power_kw * 0.5

    adjusted = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, budget_kw)

    assert adjusted.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(adjusted.power_kw, budget_kw, rel_tol=1e-9)
    # Cutting force/torque are unchanged — they do not depend on spindle speed.
    assert math.isclose(adjusted.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(adjusted.torque_nm, nominal.torque_nm, rel_tol=1e-9)


def test_power_constrained_no_op_when_budget_comfortably_exceeds_nominal():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    budget_kw = nominal.power_kw * 2.0

    result = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, budget_kw)

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_power_constrained_no_op_at_exact_equality_boundary():
    """An available_power exactly equal to nominal power (within
    math.isclose's default rel_tol=1e-9) is "sufficient" — never triggers
    the reduction (mirrors drilling's spec.md Clarifications 2026-07-11)."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)

    result = calculate_turning_power_constrained_metrics(
        40, 2, 100, material, tool, nominal.power_kw
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(result.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)


def test_power_constrained_zero_or_negative_budget_raises_by_design():
    """calculate_turning_power_constrained_metrics() does not itself
    validate available_power_kw (per its docstring, mirroring drilling's
    equivalent): a zero budget produces a zero adjusted spindle speed,
    which triggers a ZeroDivisionError in the shared machining-time
    formula. This is why processes/machining/turning's calculate_turning()
    entry point MUST reject non-positive budgets as INFEASIBLE_POWER_BUDGET
    BEFORE calling this helper — this test documents and locks in that
    contract."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    with pytest.raises(ZeroDivisionError):
        calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, 0.0)


def test_power_constrained_tiny_budget_yields_tiny_positive_rpm():
    """No floor is imposed on the adjusted spindle speed; an extremely
    small but positive budget still yields a valid, positive result rather
    than being rejected."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    tiny_budget_kw = nominal.power_kw * 1e-6

    result = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, tiny_budget_kw)

    assert result.spindle_speed_rpm > 0
    assert math.isclose(result.power_kw, tiny_budget_kw, rel_tol=1e-9)
