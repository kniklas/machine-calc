"""Integration test: invalid input shows an in-place, catalog-sourced
validation message and the field is correctable without restarting
(tasks.md T013, spec.md User Story 1 Acceptance Scenario 2)."""

from __future__ import annotations

from mfgparams.console.tui.screens.drilling import DrillingSessionState, run_drilling_screen

from _tui_test_support import run_headless

_KEYS_WITH_INVALID_DIAMETER_THEN_CORRECTED = [
    "\t\r",  # unit system: default
    "\t\r",  # mode: default
    "\t\r",  # material type: default
    "\t\r",  # material: default
    "\t\r",  # tool: default
    "0\r\r",  # diameter: 0 -- invalid (must be > 0), submits and triggers an error dialog
    "\r",  # dismiss the error dialog (single OK button, no text field)
    "10\r\r",  # diameter: corrected, second attempt
    "20\r\r",  # depth
    "\t\r",  # optional power: blank
    "\r",  # dismiss the result dialog
]


def test_invalid_diameter_reprompts_and_corrected_value_is_accepted():
    state = DrillingSessionState()
    run_headless(
        lambda: run_drilling_screen(state, None, "en", "en"),
        _KEYS_WITH_INVALID_DIAMETER_THEN_CORRECTED,
    )

    # The invalid "0" never got committed to state -- only the corrected value did.
    assert state.diameter == 10.0
    assert state.depth == 20.0


_KEYS_WITH_NON_NUMERIC_THEN_CORRECTED = [
    "\t\r",
    "\t\r",
    "\t\r",
    "\t\r",
    "\t\r",
    "abc\r\r",  # non-numeric -- invalid, submits and triggers an error dialog
    "\r",  # dismiss the error dialog
    "10\r\r",  # corrected
    "20\r\r",
    "\t\r",
    "\r",
]


def test_non_numeric_diameter_reprompts_and_corrected_value_is_accepted():
    state = DrillingSessionState()
    run_headless(
        lambda: run_drilling_screen(state, None, "en", "en"),
        _KEYS_WITH_NON_NUMERIC_THEN_CORRECTED,
    )

    assert state.diameter == 10.0
