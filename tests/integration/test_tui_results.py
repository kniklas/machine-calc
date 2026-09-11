"""Integration test: the right pane's two-state machine and automatic
refresh (018-tui-splitpane-redesign User Story 3, tasks.md T025).

FR-006/FR-006a's two states -- placeholder, or a result/error once complete
-- never a third, exercised against both Drilling and Milling through the
shared `split_pane.render_right_pane`. (Revision, matching the pre-plan
prototype exactly: FR-006b's unparseable-text state moved entirely to the
bottom status bar -- see `test_tui_validation.py` -- so it is no longer one
of the right pane's own states.) FR-007's automatic refresh is exercised by
changing an input and confirming the *next* render reflects it, with no
separate "calculate" action.
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
_DRILLING_PLACEHOLDER = translate("en", "tui.drilling.placeholder")
_MILLING_PLACEHOLDER = translate("en", "tui.milling.placeholder")


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
    _row(rows, FieldId.DIAMETER).on_commit(10.0)
    rows = drilling_rows_for(screen, None, "en", "en")
    _row(rows, FieldId.DEPTH).on_commit(20.0)


def _render_right(screen: OperationScreen) -> str:
    rows = drilling_rows_for(screen, None, "en", "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    fragments = split_pane.render_right_pane(
        rows,
        screen,
        lambda: drilling_calculate(state, None, "en"),
        _LABELS,
        "en",
        placeholder=_DRILLING_PLACEHOLDER,
    )
    return "".join(t for _, t in fragments)


def test_right_pane_shows_placeholder_while_input_is_incomplete():
    """Acceptance Scenario 1."""

    screen = _drilling_screen()
    text = _render_right(screen)
    assert _DRILLING_PLACEHOLDER in text


def test_right_pane_shows_a_result_the_instant_the_last_input_completes_it():
    """Acceptance Scenario 2 -- no separate confirmation step."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    text = _render_right(screen)
    assert translate("en", "tui.result.title") in text
    assert _DRILLING_PLACEHOLDER not in text


def test_right_pane_refreshes_automatically_when_an_input_changes():
    """Acceptance Scenario 3, FR-007 -- changing diameter changes the
    displayed spindle speed on the very next render, with no separate
    "calculate" action."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    first_text = _render_right(screen)

    # `NumberRow.on_commit` is the same commit callback `move_selection`
    # drives once the user navigates away from a field -- calling it
    # directly with the new full value is equivalent to a user retyping the
    # field and then leaving it, without needing to replay individual
    # keystrokes here (that replay behavior is `test_tui_field_editing.py`'s
    # job).
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_commit(5.0)

    second_text = _render_right(screen)
    assert second_text != first_text


def test_right_pane_shows_an_error_for_a_complete_but_rejected_combination_not_a_blank_pane():
    """Acceptance Scenario 3's error branch (FR-006a)."""

    screen = _drilling_screen()
    _fill_drilling(screen)
    _row(drilling_rows_for(screen, None, "en", "en"), FieldId.DIAMETER).on_commit(0.0)

    text = _render_right(screen)
    assert text.strip()
    assert translate("en", "tui.result.error.title") in text


def test_milling_shares_the_same_two_state_contract():
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
        placeholder=_MILLING_PLACEHOLDER,
    )
    text = "".join(t for _, t in fragments)
    assert _MILLING_PLACEHOLDER in text

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
        placeholder=_MILLING_PLACEHOLDER,
    )
    text = "".join(t for _, t in fragments)
    assert translate("en", "tui.result.title") in text


def test_content_windows_in_app_py_set_wrap_lines_true():
    """FR-018: prompt-toolkit's own `Window` defaults to `wrap_lines=False`
    -- without explicitly overriding it, a result line wider than the pane
    would overflow/truncate instead of wrapping.

    Checked via source inspection rather than a live
    `Layout.find_all_windows()` count (revision, tasks.md T049): the
    floating operation window (research.md #3) makes the *count* of
    wrapping windows in the tree sensitive to incidental structural detail
    unrelated to this guarantee -- `Frame`'s own title `Label` wraps by
    its own default, and the background body window now stays permanently
    present (and wrapping) alongside the float rather than being swapped
    out while one is open. An AST check of `Window(content=..., ...)`
    call sites stays precise regardless of how many *other* windows the
    layout happens to contain."""

    import ast
    import inspect

    from mfgparams.console.tui import app as app_mod

    source = inspect.getsource(app_mod)
    tree = ast.parse(source)
    missing = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Window"
        ):
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords}
        if "content" not in kwargs:
            continue
        content_repr = ast.dump(kwargs["content"])
        if "bar_control" in content_repr:
            continue  # the bar is intentionally single-line; it never wraps.
        wrap = kwargs.get("wrap_lines")
        if not (isinstance(wrap, ast.Constant) and wrap.value is True):
            missing.append(content_repr)

    assert not missing, f"Window(content=...) missing wrap_lines=True: {missing}"
