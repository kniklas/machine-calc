"""Integration test: REPL validation error handling (T021).

Invalid diameter/depth and missing material/tool selections must re-prompt
rather than crash or proceed with bad input.
"""

import builtins

from machine_calc.cli import run


def test_invalid_diameter_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",
            "",  # calculation mode (default: standard)
            "Mild Steel",
            "Carbide",
            "not-a-number",  # invalid diameter -> reprompt
            "-5",  # invalid diameter (out of range) -> reprompt
            "10",  # valid diameter
            "25",  # valid depth
            "",  # available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a numeric value." in out
    assert "Drill diameter must be greater than 0." in out
    assert "RPM" in out  # eventually succeeds


def test_invalid_material_choice_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",
            "",  # calculation mode (default: standard)
            "Unknown Material",  # invalid -> reprompt
            "Mild Steel",  # valid
            "Carbide",
            "10",
            "25",
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please choose one of" in out
    assert "RPM" in out
