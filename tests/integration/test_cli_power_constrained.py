"""Integration test: REPL power-constrained mode flow (T013).

Selecting the ``power-constrained`` mode prompts for a required available
power and displays the spindle speed with the "adjusted to fit available
power" suffix label (contracts/cli-repl-delta.md).
"""

import builtins

from machine_calc.cli import run


def test_power_constrained_mode_prompts_for_power_and_labels_result(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",  # unit system
            "power-constrained",  # calculation mode
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0.5",  # required available power (kW)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "0.50 kW" in out


def test_power_constrained_infeasible_budget_shows_error(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",
            "power-constrained",
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0",  # invalid available power (must be > 0) -> reprompt
            "0.5",  # valid available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for available power." in out
