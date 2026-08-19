"""Contract test: power-constrained mode INFEASIBLE_POWER_BUDGET error
response (T012).

Per contracts/library-api-milling-modes-delta.md; mirrors
tests/contract/test_library_api_power_constrained_errors.py (drilling) for
both milling sub-operations.
"""

from machine_calc import CalculationMode, calculate_end_milling, calculate_face_milling

_END_MILLING_ARGS = dict(
    diameter=10,
    axial_depth_of_cut=2,
    radial_depth_of_cut=5,
    feed_per_tooth=0.05,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)

_FACE_MILLING_ARGS = dict(
    diameter=50,
    axial_depth_of_cut=1.5,
    width_of_cut=40,
    feed_per_tooth=0.15,
    number_of_teeth=5,
    length_of_cut=200,
    material="Mild Steel",
    tool="Carbide",
)


def test_end_milling_zero_available_power_is_infeasible():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.material_removal_rate is None


def test_end_milling_negative_available_power_is_infeasible():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-1.0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.machining_time is None
    assert result.torque is None
    assert result.power_required is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_end_milling_infeasible_error_does_not_raise():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-100.0,
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"


def test_face_milling_zero_available_power_is_infeasible():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.material_removal_rate is None


def test_face_milling_negative_available_power_is_infeasible():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-1.0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_face_milling_infeasible_error_does_not_raise():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-100.0,
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
