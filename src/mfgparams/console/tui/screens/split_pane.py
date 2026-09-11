"""Shared left/right split-pane engine for the Drilling and Milling operation
screens (018-tui-splitpane-redesign FR-004/FR-005/FR-009).

Instant-edit numeric fields (FR-016), Left/Right nudge (FR-017), and the
right pane's three-state result machine (FR-006/FR-006a/FR-006b) all live
here once; `screens/drilling.py`/`screens/milling.py` (T022/T023) each
supply only their own field list (`rows_for`, mirroring
`machining_menu.tree_rows`' "recompute every render" approach, since a
later row's visibility can depend on an earlier row's value -- e.g.
`material` only appears once `material_type` is chosen, `target_rpm` only
in Fixed RPM mode) and their own `calculate()` call, per FR-009's
identical-pattern requirement.

FR-006a's design collapses cleanly here: unlike the old dialog chain (which
pre-validated each field with e.g. `validate_diameter_mm` before ever
calling `calculate()`), this module does no range validation of its own --
`calculate()`/`calculate_end_milling()`/`calculate_face_milling()` already
re-validate every field internally regardless of caller (confirmed in
spec.md's FR-006a rationale), so once a field parses as a number this
module's only job is to call `calculate()` and display whatever `ErrorInfo`
it returns. The one case `calculate()` cannot cover is FR-006b: text that
never parses as a number at all, so it can never reach `calculate()` in the
first place.

**Revision (tasks.md T048/Phase 8)**: radio fields render as a
`prompt_toolkit.widgets.RadioList`-alike -- vertically-stacked, one option
per line, using that widget's own default markers (`(*)`/`( )`) -- for
whichever field is currently selected; every other radio field collapses to
a one-line summary (research.md #4's accordion pattern). This module does
not embed an actual live `RadioList` widget instance: this codebase's whole
`tui/` architecture (mirroring `machining_menu.py`/`menu.py`) renders every
screen as a pure function of plain-dataclass state recomputed fresh each
render, not a tree of stateful, incrementally-updated widget objects: a
real `RadioList` manages its own internal selected-index state across
renders, which doesn't fit that model without introducing long-lived
per-field widget instances this module has nowhere consistent to cache
between the `rows_for()` calls that rebuild the row list from scratch every
time. `field_buffer` -- already the "not-yet-committed state of the
selected field" for numeric fields -- is reused for radio fields' own
highlighted-but-not-yet-committed option, matching `RadioList`'s real
two-step Up/Down-then-Enter/Space interaction (navigating away without
confirming leaves the field's last-committed value untouched, unlike
`NumberRow`'s commit-on-every-keystroke).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.models import CalculationResult

#: FR-017: "a small fixed step" -- 1 display unit (already in the field's
#: current unit system, e.g. 1 mm or 1 in for a length field), matching the
#: pre-plan prototype's own validated step size (spec's Recommended Next
#: Steps).
NUDGE_STEP = 1.0


@dataclass(frozen=True)
class RadioRow:
    """One FR-005 radio field (unit system, mode, material type, material,
    tool, milling sub-operation). `options` is the ordered
    ``(value, display_label)`` set currently available -- callers rebuild it
    every render since a later row's options can depend on an earlier row's
    value (e.g. `material`'s options depend on `material_type`).
    `on_select` commits the chosen value immediately (FR-016's "no separate
    confirm step" applies here too, not just to numeric fields)."""

    field_id: FieldId
    label: str
    options: list[tuple[str, str]]
    value: str | None
    on_select: Callable[[str], None]


@dataclass(frozen=True)
class NumberRow:
    """One FR-005/FR-016 plain numeric field. `required` distinguishes a
    field that gates FR-006's readiness (diameter, depth, ...) from one
    that's present but optional (available power outside Power-Constrained
    mode) -- both are simultaneously visible/editable per FR-005, but only
    the former blocks the right pane's result state."""

    field_id: FieldId
    label: str
    unit: str
    value: float | None
    required: bool
    on_edit: Callable[[str], None]
    on_nudge: Callable[[int], None]


Row = Union[RadioRow, NumberRow]


def power_and_rpm_rows(
    *,
    power_constrained: bool,
    fixed_rpm: bool,
    power_row: Callable[[str, bool], NumberRow],
    rpm_row: Callable[[], NumberRow],
) -> list[Row]:
    """The mode-dependent trailing rows Drilling and Milling both build the
    same way (FR-009's identical-pattern requirement, applied to this one
    previously-duplicated branch): Power-Constrained needs available power
    (required); Fixed RPM needs target RPM (required) plus available power
    (optional); Standard needs only available power (optional). Callers
    supply small factories (`power_row(label_key, required)`, `rpm_row()`)
    since the row's label/unit/current value/commit closures are
    screen-specific."""

    if power_constrained:
        return [power_row("tui.label.power_required", True)]
    if fixed_rpm:
        return [rpm_row(), power_row("tui.label.power", False)]
    return [power_row("tui.label.power", False)]


def is_complete(rows: list[Row]) -> bool:
    """FR-006's readiness gate: every row in the *current* row list either
    holds a value, or is an optional `NumberRow` (an operation-dependent
    row list is how a caller expresses "not applicable right now" -- e.g.
    the specific-material row is simply absent until `material_type` has a
    value, rather than present-but-required)."""

    for row in rows:
        if isinstance(row, RadioRow) and row.value is None:
            return False
        if isinstance(row, NumberRow) and row.required and row.value is None:
            return False
    return True


def selected_row(rows: list[Row], screen: OperationScreen) -> Row | None:
    for row in rows:
        if row.field_id is screen.selected_field:
            return row
    return None


def _format(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def sync_buffer(rows: list[Row], screen: OperationScreen) -> None:
    """Re-syncs `field_buffer` to the currently-selected row's own current
    state -- called whenever selection changes (including when a screen is
    first opened), so editing/navigating always starts from what's
    actually on screen, not a buffer left over from a previously-selected
    field.

    For a `NumberRow`, that's the formatted committed value (FR-016). For
    a `RadioRow`, `field_buffer` becomes the *highlighted* option --
    starting on the committed value if one exists, or the first option
    otherwise (matching `RadioList`'s own default-to-index-0 behavior) --
    not yet committed to `session_state` until `radio_commit`."""

    row = selected_row(rows, screen)
    if isinstance(row, NumberRow):
        screen.field_buffer = _format(row.value)
    elif isinstance(row, RadioRow):
        if row.value is not None:
            screen.field_buffer = row.value
        elif row.options:
            screen.field_buffer = row.options[0][0]
        else:
            screen.field_buffer = ""
    else:
        screen.field_buffer = ""


def move_selection(rows: list[Row], screen: OperationScreen, delta: int) -> None:
    """Moves `screen.selected_field` to the next/previous row (wrapping)."""

    if not rows:
        return
    ids = [row.field_id for row in rows]
    try:
        index = ids.index(screen.selected_field)
    except ValueError:
        index = 0
    screen.selected_field = ids[(index + delta) % len(ids)]
    sync_buffer(rows, screen)


def edit_selected(rows: list[Row], screen: OperationScreen, char: str) -> None:
    """FR-016: typing immediately edits the selected numeric field -- no
    separate "start editing" action. Appends to whatever's already in
    `field_buffer` (pre-filled with the field's current value when
    selection last moved here, `sync_buffer`); a no-op on a `RadioRow`
    (radios only ever change via `nudge_selected`, never free text)."""

    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        return
    screen.field_buffer += char
    row.on_edit(screen.field_buffer)


def backspace_selected(rows: list[Row], screen: OperationScreen) -> None:
    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        return
    screen.field_buffer = screen.field_buffer[:-1]
    row.on_edit(screen.field_buffer)


def nudge_selected(rows: list[Row], screen: OperationScreen, direction: int) -> None:
    """FR-017: numeric fields only -- +/-`NUDGE_STEP`, floor-at-zero clears
    to unset (contract §4's implementation detail). Radio fields no longer
    respond to Left/Right (research.md #4, revision) -- a no-op here for
    anything but a `NumberRow`; use `radio_navigate`/`radio_commit`
    instead."""

    row = selected_row(rows, screen)
    if not isinstance(row, NumberRow):
        return
    row.on_nudge(direction)
    screen.field_buffer = _format(row.value)


def radio_navigate(rows: list[Row], screen: OperationScreen, direction: int) -> None:
    """Up/Down on an expanded `RadioRow`: moves the *highlighted* option
    (`field_buffer`) by one step, without committing it (research.md #4 --
    `RadioList`'s own Up/Down behavior). Clamps at the first/last option
    rather than continuing on to an adjacent field -- a real `RadioList`
    fully consumes Up/Down for its own navigation and never escapes to a
    sibling widget on it; moving to a different field is Tab/Shift-Tab's
    job instead (contract §4), unconditionally, regardless of the current
    row's type. A no-op if the selected row isn't a `RadioRow` with
    options at all."""

    row = selected_row(rows, screen)
    if not isinstance(row, RadioRow) or not row.options:
        return
    values = [value for value, _ in row.options]
    current = screen.field_buffer if screen.field_buffer in values else values[0]
    new_index = values.index(current) + direction
    screen.field_buffer = values[max(0, min(len(values) - 1, new_index))]


def radio_commit(rows: list[Row], screen: OperationScreen) -> None:
    """Enter/Space on an expanded `RadioRow`: commits the currently-
    highlighted option (`field_buffer`) into `session_state`, matching
    `RadioList`'s own Enter/Space binding. A no-op on anything but a
    `RadioRow`."""

    row = selected_row(rows, screen)
    if not isinstance(row, RadioRow):
        return
    if screen.field_buffer:
        row.on_select(screen.field_buffer)


def parses_as_number(buffer: str) -> bool:
    """Empty is "unset" (FR-006's incomplete-input case), not FR-006b's
    "unparseable text" case -- the two are distinct right-pane states."""

    if not buffer.strip():
        return True
    try:
        float(buffer)
    except ValueError:
        return False
    return True


def _render_expanded_radio(row: RadioRow, highlighted: str, *, focused: bool) -> StyleAndTextTuples:
    """The selected `RadioRow`'s full option list, one per line, using
    `RadioList`'s own default markers -- `(*)` for the committed
    (`row.value`) option, `( )` otherwise -- with the *highlighted*
    (`field_buffer`) option reverse-video only while the pane has focus."""

    label_style = "class:selected" if focused else ""
    fragments: StyleAndTextTuples = [(label_style, f"{row.label}:\n")]
    for value, label in row.options:
        marker = "(*)" if value == row.value else "( )"
        style = "class:selected" if focused and value == highlighted else ""
        fragments.append((style, f"  {marker} {label}\n"))
    return fragments


def render_left_pane(
    rows: list[Row], screen: OperationScreen, title: str, locale: str, *, focused: bool
) -> StyleAndTextTuples:
    """FR-005's simultaneously-visible-and-editable left pane. The
    currently-selected `NumberRow` shows the live, possibly-mid-edit
    `field_buffer` (FR-016) rather than its last-committed value; the
    currently-selected `RadioRow` expands into its full option list
    (research.md #4); every other row shows a one-line summary of its
    committed value."""

    fragments: StyleAndTextTuples = [("class:pane-title", f"{title}\n")]
    for row in rows:
        is_selected = row.field_id is screen.selected_field
        style = "class:selected" if focused and is_selected else ""
        if isinstance(row, RadioRow) and is_selected:
            fragments.extend(_render_expanded_radio(row, screen.field_buffer, focused=focused))
        elif isinstance(row, RadioRow):
            checked_label = next((label for value, label in row.options if value == row.value), "-")
            fragments.append((style, f"{row.label}: {checked_label}\n"))
        else:
            shown = screen.field_buffer if is_selected else _format(row.value)
            unit_suffix = f" {row.unit}" if row.unit else ""
            fragments.append((style, f"{row.label}: {shown}{unit_suffix}\n"))
    return fragments


def render_right_pane(
    rows: list[Row],
    screen: OperationScreen,
    calculate: Callable[[], CalculationResult],
    labels: dict[str, str],
    locale: str,
) -> StyleAndTextTuples:
    """FR-006/FR-006a/FR-006b's three-state machine, in the one place both
    operations share it: (a) FR-006b's unparseable-text state, checked
    first since it pre-empts even asking whether the input set is
    "complete"; (b) FR-006's placeholder, while incomplete; (c) a result or
    FR-006a's `calculate()`-rejected error, memoized against the exact
    input tuple that produced it (`OperationScreen.last_result_key`) so an
    unrelated re-render doesn't recompute (SC-006)."""

    row = selected_row(rows, screen)
    if isinstance(row, NumberRow) and not parses_as_number(screen.field_buffer):
        return [
            ("class:pane-title", f"{translate(locale, 'tui.result.title')}\n\n"),
            ("class:error", translate(locale, "tui.prompt.number.invalid")),
        ]

    if not is_complete(rows):
        return [("class:hint", translate(locale, "tui.result.placeholder"))]

    calculation_key = tuple(row.value for row in rows)
    if screen.last_result is None or screen.last_result_key != calculation_key:
        screen.last_result = calculate()
        screen.last_result_key = calculation_key

    result = screen.last_result
    is_error = result.error is not None
    title_key = "tui.result.error.title" if is_error else "tui.result.title"
    style = "class:error" if is_error else ""
    return [
        ("class:pane-title", f"{translate(locale, title_key)}\n\n"),
        (style, forms.format_result(result, labels, locale)),
    ]
