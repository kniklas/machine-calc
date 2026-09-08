"""Integration test: `tui/app.py`'s `run()` end-to-end -- the actual entry
point every other test in this suite exercises one layer below (calling a
screen function directly). Drives the real menu -> Machining -> Drilling ->
result -> back-to-menu -> exit loop (Acceptance Scenario 3: starting
another calculation without exiting and relaunching)."""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams.console.tui.app import run

_ONE_DRILLING_CALCULATION_THEN_EXIT = [
    "m",  # top-level menu: mnemonic to Machining
    "d",  # machining submenu: mnemonic to Drilling
    "\t\r",  # unit system: default
    "\t\r",  # mode: default
    "\t\r",  # material type: default
    "\t\r",  # material: default
    "\t\r",  # tool: default
    "10\r\r",  # diameter
    "20\r\r",  # depth
    "\t\r",  # optional power: blank
    "\r",  # dismiss the result dialog
    "\x1b",  # back at the top-level menu: exit the app
]


def test_full_session_completes_one_drilling_calculation_then_exits(monkeypatch):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    run_headless(lambda: run(materials_config_path=None), _ONE_DRILLING_CALCULATION_THEN_EXIT)
    # run_headless's own assertion (the thread completed) is the real check:
    # `run()` returned on its own after Escape at the root menu, rather than
    # hanging or raising.


_TWO_CALCULATIONS_THEN_EXIT = _ONE_DRILLING_CALCULATION_THEN_EXIT[:-1] + [
    "m",
    "d",
    "\t\r",
    "\t\r",
    "\t\r",
    "\t\r",
    "\t\r",
    "\t\r",  # diameter: blank accepts the remembered default from the first run
    "\t\r",  # depth: blank accepts the remembered default
    "\t\r",
    "\r",
    "\x1b",
]


def test_session_supports_running_a_second_calculation_without_exiting(monkeypatch):
    """Acceptance Scenario 3: the user can start another calculation
    without exiting and relaunching the text GUI."""

    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    run_headless(lambda: run(materials_config_path=None), _TWO_CALCULATIONS_THEN_EXIT)
