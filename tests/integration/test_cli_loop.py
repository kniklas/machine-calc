"""Integration test: REPL loop, changing one input and recalculating without
restarting the process (T022; FR-014, spec Acceptance Scenario 4).
"""

import builtins

from machine_calc.cli import run


def test_loop_allows_changing_tool_and_recalculating(monkeypatch, capsys):
    inputs = iter(
        [
            "metric",
            "Mild Steel",
            "HSS",
            "10",
            "25",
            "",
            "y",  # run another calculation
            "metric",  # unit system unchanged (default reused)
            "",  # material unchanged (reuse previous default)
            "Carbide",  # switch drilling tool
            "",  # diameter unchanged
            "",  # depth unchanged
            "",  # power unchanged
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    # Two full result blocks should have been printed (one per calculation).
    assert out.count("Spindle speed:") == 2
