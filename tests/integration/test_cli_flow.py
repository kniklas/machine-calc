"""Integration test: full REPL prompt sequence with valid input (T020).

Asserts displayed values and unit labels match the underlying library
result (FR-013, FR-016).
"""

import builtins

from machine_calc import UnitSystem, calculate
from machine_calc.cli import run


def test_repl_displays_values_matching_direct_calculate(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",  # unit system
            "",  # calculation mode (default: standard)
            "Mild Steel",  # material
            "Carbide",  # tool
            "10",  # diameter
            "25",  # depth
            "",  # available power (blank/unknown)
            "n",  # do not run another calculation
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out

    expected = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.METRIC,
    )

    assert f"{expected.spindle_speed_rpm:.1f} RPM" in out
    assert f"{expected.feed_rate:.1f} mm/min" in out
    assert f"{expected.machining_time:.2f} min" in out
    assert f"{expected.torque:.1f} N\u00b7m" in out
    assert f"{expected.power_required:.2f} kW" in out
