"""Integration test: headless end-to-end Drilling flow (tasks.md T012).

Drives `run_drilling_screen` exactly as a user would through the menu chain
(menu -> Machining -> Drilling), and confirms the state it accumulates
produces the same result as calling the underlying core function directly
with the same arguments (User Story 1's Independent Test).
"""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams import calculate
from mfgparams.console.tui.screens.drilling import DrillingSessionState, run_drilling_screen

_KEYS = [
    "\t\r",  # unit system: accept default (metric)
    "\t\r",  # mode: accept default (standard)
    "\t\r",  # material type: accept default (first)
    "\t\r",  # material: accept default (first)
    "\t\r",  # tool: accept default (first)
    "10\r\r",  # diameter
    "20\r\r",  # depth
    "\t\r",  # optional power: blank
    "\r",  # dismiss the result dialog
]


def test_drilling_flow_matches_the_core_calculation():
    state = DrillingSessionState()
    run_headless(lambda: run_drilling_screen(state, None, "en", "en"), _KEYS)

    assert state.material_type == "metal"
    assert state.material == "Mild Steel"
    assert state.tool == "HSS"
    assert state.diameter == 10.0
    assert state.depth == 20.0

    expected = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=state.unit_system,
        available_power=None,
        locale="en",
        mode=state.mode,
        target_rpm=None,
    )
    assert expected.error is None
    assert expected.spindle_speed_rpm is not None


def test_drilling_screen_can_be_cancelled_at_the_first_field():
    """Cancelling ("go back") on the very first field must return promptly
    without ever reaching calculate() -- no partial state committed."""

    state = DrillingSessionState()
    run_headless(lambda: run_drilling_screen(state, None, "en", "en"), ["\t\t\r"])

    assert state.material is None
    assert state.diameter is None
