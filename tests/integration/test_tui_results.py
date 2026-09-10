"""Integration test: the right pane's three-state machine and automatic
refresh (018-tui-splitpane-redesign User Story 3, tasks.md T025).

FR-006/FR-006a's three states -- placeholder, result, error -- never a
fourth (contract §3), exercised against both Drilling and Milling through
the shared `split_pane.render_right_pane`. FR-007's automatic refresh is
exercised by changing an input and confirming the *next* render reflects
it, with no separate "calculate" action.
"""

from __future__ import annotations

from mfgparams import UnitSystem
from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen, SessionUI
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState
from mfgparams.console.tui.screens.drilling import calculate_result as drilling_calculate
from mfgparams.console.tui.screens.drilling import rows_for as drilling_rows_for
from mfgparams.console.tui.screens.milling import calculate_result as milling_calculate
from mfgparams.console.tui.screens.milling import rows_for as milling_rows_for

_LABELS = forms.UNIT_LABELS[UnitSystem.METRIC]


def _drilling_screen() -> OperationScreen:
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    split_pane.sync_buffer(drilling_rows_for(screen, None, "en", "en"), screen)
    return screen


def _row(rows, field_id: FieldId):
    return next(row for row in rows if row.field_id is field_id)


def _fill_drilling(screen: OperationScreen) -> None:
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.MATERIAL_TYPE).on_select("metal")
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.MATERIAL).on_select("Mild Steel")
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.TOOL).on_select("HSS")
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.DIAMETER).on_edit("10")
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.DEPTH).on_edit("20")


def _render_right(screen: OperationScreen) -> str:
    rows = drilling_rows_for(screen, None, "en", "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    fragments = split_pane.render_right_pane(
        rows, screen, lambda: drilling_calculate(state, None, "en"), _LABELS, "en"
    )
    return "".join(t for _, t in fragments)


def test_right_pane_shows_placeholder_while_input_is_incomplete():
    """Acceptance Scenario 1."""

    screen = _drilling_screen()
    text = _render_right(screen)
    assert translate("en", "tui.result.placeholder") in text


def test_right_pane_shows_a_result_the_instant_the_last_input_completes_it():
    """Acceptance Scenario 2 -- no separate confirmation step."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    text = _render_right(screen)
    assert translate("en", "tui.result.title") in text
    assert translate("en", "tui.result.placeholder") not in text


def test_right_pane_refreshes_automatically_when_an_input_changes():
    """Acceptance Scenario 3, FR-007 -- changing diameter changes the
    displayed spindle speed on the very next render, with no separate
    "calculate" action."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    first_text = _render_right(screen)

    # `NumberRow.on_edit` is the same commit callback a keystroke drives
    # (`split_pane.edit_selected`/`backspace_selected`) -- calling it
    # directly with the new full value is equivalent to a user retyping the
    # field, without needing to replay individual keystrokes here (that
    # replay behavior is `test_tui_field_editing.py`'s job).
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_edit("5")

    second_text = _render_right(screen)
    assert second_text != first_text


def test_right_pane_shows_an_error_for_a_complete_but_rejected_combination_not_a_blank_pane():
    """Acceptance Scenario 3's error branch (FR-006a)."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_edit("0")

    text = _render_right(screen)
    assert text.strip()
    assert translate("en", "tui.result.error.title") in text


def test_milling_shares_the_same_three_state_contract():
    """FR-009: Milling follows the identical pattern."""

    from mfgparams.console.tui.app import MenuBar
    from mfgparams.console.tui.screens.milling import MillingSessionState

    ui = SessionUI(menu_bar=MenuBar(entries=()))
    screen = OperationScreen(
        operation="milling",
        session_state=ui.milling_states[__import__("mfgparams").MillingSubOperation.END_MILLING],
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = milling_rows_for(ui, screen, None, "en", "en")
    fragments = split_pane.render_right_pane(
        rows,
        screen,
        lambda: milling_calculate(ui, screen.session_state, None, "en"),
        _LABELS,
        "en",
    )
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.result.placeholder") in text

    state = screen.session_state
    assert isinstance(state, MillingSessionState)
    state.material_type = "metal"
    state.material = "Mild Steel"
    state.tool = "HSS"
    state.diameter = 10.0
    state.axial_depth_of_cut = 2.0
    state.radial_engagement = 1.0
    state.feed_per_tooth = 0.05
    state.number_of_teeth = 4.0
    state.length_of_cut = 50.0

    rows = milling_rows_for(ui, screen, None, "en", "en")
    fragments = split_pane.render_right_pane(
        rows,
        screen,
        lambda: milling_calculate(ui, screen.session_state, None, "en"),
        _LABELS,
        "en",
    )
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.result.title") in text


def test_the_left_and_right_pane_windows_wrap_long_lines():
    """FR-018: prompt-toolkit's own `Window` defaults to `wrap_lines=False`
    -- without explicitly overriding it, a result line wider than the pane
    would overflow/truncate instead of wrapping. Checked against the real,
    built `Layout` (not just re-reading the source), since this is exactly
    the kind of default that's easy to silently lose in a future refactor."""

    from mfgparams.console.tui import app as app_mod

    application, ui, view = app_mod.build_app(None, "en", "en")
    ui.open_operation = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    view.body_mode = "drilling"

    def _wraps(window) -> bool:
        wrap = window.wrap_lines
        return bool(wrap()) if callable(wrap) else bool(wrap)

    wrapping_windows = [w for w in application.layout.find_all_windows() if _wraps(w)]
    # Exactly the left and right pane content windows -- not the bar or the
    # bar/body separator, which render fixed decorative content that never
    # needs wrapping.
    assert len(wrapping_windows) == 2
