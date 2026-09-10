"""Integration test: the Drilling operation screen (018-tui-splitpane-redesign
US2, tasks.md T014).

Drives `screens.drilling.rows_for`/`calculate_result` directly -- the same
functions `app.py`'s key bindings call on every keystroke -- rather than
through the full headless `Application` (`test_tui_navigation.py` covers
that wiring layer separately, per spec's "Do not invest further in the
soon-to-be-deleted dialog-chain tests" recommendation to write fresh
coverage from the start). Each row's `on_select`/`on_edit`/`on_nudge`
closure *is* what a keystroke invokes, so calling it directly is a faithful,
non-flaky simulation without prompt_toolkit's timing-sensitive pipe-input
harness.
"""

from __future__ import annotations

from mfgparams import CalculationMode, UnitSystem, calculate
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState, calculate_result, rows_for


def _screen(state: DrillingSessionState | None = None) -> OperationScreen:
    return OperationScreen(
        operation="drilling",
        session_state=state or DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )


def _rows(screen: OperationScreen) -> list[split_pane.Row]:
    return rows_for(screen, None, "en", "en")


def _row(rows: list[split_pane.Row], field_id: FieldId) -> split_pane.Row:
    return next(row for row in rows if row.field_id is field_id)


def _fill_metal_mild_steel_hss(screen: OperationScreen) -> None:
    """Metal/Mild Steel/HSS, 10mm diameter, 20mm depth -- the same
    known-good combination 017's drilling test used (confirmed above to
    produce a valid, non-error `calculate()` result)."""

    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    _row(_rows(screen), FieldId.MATERIAL).on_select("Mild Steel")
    _row(_rows(screen), FieldId.TOOL).on_select("HSS")
    _row(_rows(screen), FieldId.DIAMETER).on_edit("10")
    _row(_rows(screen), FieldId.DEPTH).on_edit("20")


def test_every_fr005_field_is_visible_simultaneously_without_a_screen_transition():
    """Acceptance Scenario 1."""

    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    field_ids = {row.field_id for row in _rows(screen)}
    assert field_ids == {
        FieldId.UNIT_SYSTEM,
        FieldId.MODE,
        FieldId.MATERIAL_TYPE,
        FieldId.MATERIAL,
        FieldId.TOOL,
        FieldId.DIAMETER,
        FieldId.DEPTH,
        FieldId.AVAILABLE_POWER,
    }


def test_material_type_selection_expands_a_further_material_radio_choice():
    """Acceptance Scenario 2."""

    screen = _screen()
    assert FieldId.MATERIAL not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MATERIAL_TYPE).on_select("metal")
    assert FieldId.MATERIAL in {row.field_id for row in _rows(screen)}


def test_unit_system_change_converts_diameter_rather_than_discarding_it():
    """Acceptance Scenario 3, mirroring PR #94's unit-carryover fix."""

    screen = _screen()
    _row(_rows(screen), FieldId.DIAMETER).on_edit("10")
    _row(_rows(screen), FieldId.UNIT_SYSTEM).on_select("imperial")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.unit_system is UnitSystem.IMPERIAL
    assert state.diameter is not None
    assert round(state.diameter, 4) == round(10 / 25.4, 4)


def test_standard_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    assert result.error is None

    expected = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.STANDARD,
        target_rpm=None,
    )
    assert result.spindle_speed_rpm == expected.spindle_speed_rpm
    assert result.feed_rate == expected.feed_rate


def test_target_rpm_field_only_present_in_fixed_rpm_mode():
    screen = _screen()
    assert FieldId.TARGET_RPM not in {row.field_id for row in _rows(screen)}
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert FieldId.TARGET_RPM in {row.field_id for row in _rows(screen)}


def test_fixed_rpm_mode_reaches_a_result_matching_the_core_calculation():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    _row(_rows(screen), FieldId.TARGET_RPM).on_edit("500")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert split_pane.is_complete(_rows(screen))

    result = calculate_result(state, None, "en")
    expected = calculate(
        diameter=10.0,
        depth=20.0,
        material="Mild Steel",
        tool="HSS",
        unit_system=UnitSystem.METRIC,
        available_power=None,
        locale="en",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500.0,
    )
    assert result.error == expected.error
    if result.error is None:
        assert result.spindle_speed_rpm == expected.spindle_speed_rpm


def test_power_constrained_mode_requires_available_power_to_be_complete():
    screen = _screen()
    _fill_metal_mild_steel_hss(screen)
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    assert not split_pane.is_complete(_rows(screen))
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_edit("2")
    assert split_pane.is_complete(_rows(screen))


def test_switching_mode_clears_the_previous_modes_power_or_rpm_value():
    """Mirrors the pre-018 dialog chain's `mode_changed` guard: a mode's
    power/RPM field(s) must not silently default to a value entered under a
    *different* mode."""

    screen = _screen()
    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.POWER_CONSTRAINED.value)
    _row(_rows(screen), FieldId.AVAILABLE_POWER).on_edit("5")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    assert state.available_power == 5.0

    _row(_rows(screen), FieldId.MODE).on_select(CalculationMode.FIXED_RPM.value)
    assert state.available_power is None
    assert state.target_rpm is None
