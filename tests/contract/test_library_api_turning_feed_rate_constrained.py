"""Contract test: turning feed-rate-constrained mode success response shape
(specs/020-turning-feed-per-rotation).

Per contracts/library-api-turning-feed-per-rotation-delta.md: spindle speed
is derived exactly as standard mode, `feed_per_rotation` echoes the supplied
value, and dependent metrics (cutting force, torque, power) are recomputed
from it. Mirrors tests/contract/test_library_api_turning_fixed_rpm.py.
"""

import math

from mfgparams import CalculationMode, UnitSystem, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_turning_feed_rate_constrained_success_response_shape():
    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.5
    )

    assert result.error is None
    assert result.mode is CalculationMode.FEED_RATE_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    # FR-005: spindle speed is derived exactly as standard mode's.
    assert math.isclose(result.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    # feed_per_rotation echoes the supplied value directly.
    assert result.feed_per_rotation == 0.5
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.cutting_force is not None


def test_turning_feed_rate_constrained_dependent_metrics_recomputed_from_supplied_feed():
    """Unlike FIXED_RPM's torque/cutting_force (unchanged from nominal),
    feed-rate-constrained mode's cutting_force/torque/power_required DO
    change from the nominal value, because turning's cutting force depends
    directly on feed per revolution."""

    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.5
    )

    assert not math.isclose(result.cutting_force, standard.cutting_force, rel_tol=1e-9)
    assert not math.isclose(result.torque, standard.torque, rel_tol=1e-9)
    assert not math.isclose(result.feed_rate, standard.feed_rate, rel_tol=1e-9)


def test_turning_feed_rate_constrained_feasibility_warning_when_power_exceeded():
    """FR-008: available_power remains optional/advisory in feed-rate-
    constrained mode -- a warning is included if exceeded, absent if not."""

    exceeded = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        available_power=0.1,
    )
    assert exceeded.error is None
    assert exceeded.feasibility_warning is not None

    sufficient = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        available_power=1000.0,
    )
    assert sufficient.error is None
    assert sufficient.feasibility_warning is None
