"""Integration test: FR-006a/FR-006b's two distinct invalid-input states
(018-tui-splitpane-redesign User Story 2 Acceptance Scenario 5, tasks.md
T017).

FR-006a (a value `calculate()` itself rejects, e.g. diameter 0) and FR-006b
(text that never parses as a number at all, e.g. "abc") are deliberately
different code paths -- FR-006a reuses `calculate()`'s own `ErrorInfo`,
FR-006b never reaches `calculate()` in the first place. Both leave the
field immediately correctable, never crash, and never silently show a
stale/wrong result.
"""

from __future__ import annotations

from mfgparams.console.i18n import translate
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState, calculate_result, rows_for


def _screen() -> OperationScreen:
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    split_pane.sync_buffer(rows_for(screen, None, "en", "en"), screen)
    return screen


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _row(rows, field_id: FieldId):
    return next(row for row in rows if row.field_id is field_id)


def _fill_metal_mild_steel_hss_except_diameter(screen: OperationScreen) -> None:
    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(screen), FieldId.DEPTH).on_edit("20")


def test_unparseable_text_stays_editable_shows_a_message_and_never_reaches_calculate():
    """FR-006b."""

    screen = _screen()
    _fill_metal_mild_steel_hss_except_diameter(screen)
    calls = []

    def _calculate():
        calls.append(1)
        raise AssertionError("calculate() must not be called for unparseable input")

    screen.selected_field = FieldId.DIAMETER
    rows = _rows(screen)
    split_pane.sync_buffer(rows, screen)
    split_pane.edit_selected(rows, screen, "a")
    split_pane.edit_selected(_rows(screen), screen, "b")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    # The buffer carries the invalid text; state itself is untouched (still
    # unset), not corrupted with a bogus number.
    assert screen.field_buffer == "ab"
    assert state.diameter is None

    labels = {"diameter": "mm", "depth": "mm", "power": "kW"}
    fragments = split_pane.render_right_pane(_rows(screen), screen, _calculate, labels, "en")
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.prompt.number.invalid") in text
    assert not calls


def test_calculate_rejected_combination_shows_calculates_own_error():
    """FR-006a: diameter 0 parses fine as a number, but `calculate()`
    itself rejects it -- a *different* code path from FR-006b, reusing
    `calculate()`'s own `ErrorInfo` rather than a local message."""

    screen = _screen()
    _fill_metal_mild_steel_hss_except_diameter(screen)
    _row(_rows(screen), FieldId.DIAMETER).on_edit("0")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    assert result.error is not None
    assert result.error.message_key == "error.invalid_diameter.zero"

    labels = {"diameter": "mm", "depth": "mm", "power": "kW"}
    fragments = split_pane.render_right_pane(
        _rows(screen), screen, lambda: calculate_result(state, None, "en"), labels, "en"
    )
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.result.error.title") in text
    assert "0" not in translate("en", "tui.prompt.number.invalid")  # sanity: distinct message
    assert result.error.message in text


def test_an_empty_field_is_incomplete_not_invalid():
    """A blank field is FR-006's "incomplete" placeholder state, not
    FR-006b's "unparseable text" state -- the two must not be conflated."""

    screen = _screen()
    _fill_metal_mild_steel_hss_except_diameter(screen)
    screen.selected_field = FieldId.DIAMETER
    split_pane.sync_buffer(_rows(screen), screen)
    assert screen.field_buffer == ""

    labels = {"diameter": "mm", "depth": "mm", "power": "kW"}
    fragments = split_pane.render_right_pane(
        _rows(screen), screen, lambda: (_ for _ in ()).throw(AssertionError), labels, "en"
    )
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.result.placeholder") in text
