"""Contract test: CALCULATION_OVERFLOW guard for extreme-but-individually
-valid inputs.

``feed_per_tooth`` and ``target_rpm`` deliberately have no configurable
upper bound (FR-008/FR-018, spec.md Clarifications) — but an extreme value
in either can still make a downstream product (e.g. ``feed_rate_mm_min =
rpm * feed_per_tooth_mm * number_of_teeth``) overflow to ``inf``. Rather
than surface a result mixing finite and inf/nan fields, this must be
reported as a structured ``CALCULATION_OVERFLOW`` error (FR-012/FR-015
never-raises contract) for STANDARD and FIXED_RPM modes (POWER_CONSTRAINED
already has its own ``INFEASIBLE_POWER_BUDGET`` guard, covered by
tests/contract/test_library_api_milling_power_constrained_errors.py).
"""

from machine_calc import CalculationMode, calculate_end_milling, calculate_face_milling

_END_MILLING_ARGS = dict(
    diameter=10,
    axial_depth_of_cut=2,
    radial_depth_of_cut=5,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)

_FACE_MILLING_ARGS = dict(
    diameter=50,
    axial_depth_of_cut=1.5,
    width_of_cut=40,
    number_of_teeth=5,
    length_of_cut=200,
    material="Mild Steel",
    tool="Carbide",
)


def test_end_milling_extreme_feed_per_tooth_standard_mode_reports_overflow():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.material_removal_rate is None


def test_face_milling_extreme_feed_per_tooth_standard_mode_reports_overflow():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_end_milling_extreme_feed_per_tooth_fixed_rpm_mode_reports_overflow():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=1200,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_end_milling_normal_feed_per_tooth_does_not_overflow():
    """Sanity check: an ordinary, realistic feed_per_tooth is unaffected."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=0.05,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is None
    assert result.spindle_speed_rpm is not None
