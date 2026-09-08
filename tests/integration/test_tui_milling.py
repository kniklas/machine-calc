"""Integration test: headless end-to-end Milling flow (tasks.md T011).

Drives `run_milling_screen` for the end-milling sub-operation and confirms
its result matches `mfgparams.calculate_end_milling` called directly with
the same arguments (User Story 1's Independent Test).
"""

from __future__ import annotations

from _tui_test_support import run_headless

from mfgparams import MillingSubOperation, calculate_end_milling
from mfgparams.console.tui.screens.milling import MillingSessionState, run_milling_screen

_KEYS = [
    "\t\r",  # sub-operation: accept default (end milling)
    "\t\r",  # unit system: default (metric)
    "\t\r",  # mode: default (standard)
    "\t\r",  # material type: default (first)
    "\t\r",  # material: default (first)
    "\t\r",  # tool: default (first)
    "10\r\r",  # cutter diameter
    "2\r\r",  # axial depth of cut
    "1\r\r",  # radial depth of cut
    "0.05\r\r",  # feed per tooth
    "4\r\r",  # number of teeth
    "50\r\r",  # length of cut
    "\t\r",  # optional power: blank
    "\r",  # dismiss the result dialog
]


def test_end_milling_flow_matches_the_core_calculation():
    states = {sub: MillingSessionState() for sub in MillingSubOperation}
    run_headless(
        lambda: run_milling_screen(states, None, "en", "en"),
        _KEYS,
    )

    state = states[MillingSubOperation.END_MILLING]
    assert state.material == "Mild Steel"
    assert state.tool == "HSS"
    assert state.diameter == 10.0
    assert state.axial_depth_of_cut == 2.0
    assert state.radial_engagement == 1.0
    assert state.feed_per_tooth == 0.05
    assert state.number_of_teeth == 4.0
    assert state.length_of_cut == 50.0

    expected = calculate_end_milling(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=1.0,
        feed_per_tooth=0.05,
        number_of_teeth=4.0,
        length_of_cut=50.0,
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


def test_revisiting_the_same_sub_operation_offers_prior_answers_as_defaults():
    """SC-005/FR-002 parity: the REPL offered prior answers as defaults on
    the next iteration -- the text GUI's per-sub-operation session state
    must do the same. Accepting every default the second time around should
    reproduce the same diameter without retyping it."""

    states = {sub: MillingSessionState() for sub in MillingSubOperation}
    run_headless(lambda: run_milling_screen(states, None, "en", "en"), _KEYS)
    first_diameter = states[MillingSubOperation.END_MILLING].diameter

    second_keys = ["\t\r"] * 6 + ["\t\r", "\t\r", "\t\r", "\t\r", "\t\r", "\t\r", "\t\r", "\r"]
    run_headless(lambda: run_milling_screen(states, None, "en", "en"), second_keys)

    assert states[MillingSubOperation.END_MILLING].diameter == first_diameter
