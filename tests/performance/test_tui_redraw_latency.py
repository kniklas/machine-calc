"""Opt-in input-to-redraw latency check for the text GUI
(018-tui-splitpane-redesign spec.md SC-006, tasks.md T030).

017's version of this test measured a dialog *round trip* (input sent,
`Application.run()` returns) -- which never actually observed a redraw at
all: the old dialog chain computed and displayed a result exactly once,
when the screen exited, not reactively (spec's Carried-Over Items table:
"the old version's timer started before input and stopped at dialog exit,
never observing an actual redraw"). This feature introduces the first
*real* reactive redraw (FR-007: the right pane recomputes on every
committed left-pane change, with no separate "calculate" action) -- so this
measures exactly that: `split_pane.render_right_pane`'s wall-clock cost for
a fully up-to-date, complete input set. That function is what
`app.py`'s `right_control` FormattedTextControl calls on every render, so
timing it directly measures the real per-keystroke redraw cost without a
timing-fragile threaded pipe-input harness around it.

Skipped by default; run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/test_tui_redraw_latency.py \\
        -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

import time

from mfgparams.console.tui import forms
from mfgparams.console.tui.app import FieldId, OperationScreen
from mfgparams.console.tui.screens import split_pane
from mfgparams.console.tui.screens.drilling import DrillingSessionState, calculate_result, rows_for

#: SC-006's target, in seconds -- "responsive, perceived instantaneous".
_REDRAW_LATENCY_BUDGET_SECONDS = 0.2

_REPEATS = 5


def _completed_drilling_screen() -> OperationScreen:
    screen = OperationScreen(
        operation="drilling",
        session_state=DrillingSessionState(),
        selected_field=FieldId.UNIT_SYSTEM,
    )
    rows = rows_for(screen, None, "en", "en")
    next(r for r in rows if r.field_id is FieldId.MATERIAL_TYPE).on_select("metal")
    rows = rows_for(screen, None, "en", "en")
    next(r for r in rows if r.field_id is FieldId.MATERIAL).on_select("Mild Steel")
    rows = rows_for(screen, None, "en", "en")
    next(r for r in rows if r.field_id is FieldId.TOOL).on_select("HSS")
    rows = rows_for(screen, None, "en", "en")
    next(r for r in rows if r.field_id is FieldId.DIAMETER).on_edit("10")
    rows = rows_for(screen, None, "en", "en")
    next(r for r in rows if r.field_id is FieldId.DEPTH).on_edit("20")
    return screen


def _time_right_pane_redraw(screen: OperationScreen) -> float:
    """One redraw, forced to actually recompute (not served from the
    `last_result_key` cache) by invalidating it first -- the cache is a
    real optimization (SC-006), but this test wants the uncached cost."""

    screen.last_result = None
    screen.last_result_key = None
    rows = rows_for(screen, None, "en", "en")
    state = screen.session_state
    assert isinstance(state, DrillingSessionState)
    labels = forms.UNIT_LABELS[state.unit_system]

    start = time.perf_counter()
    fragments = split_pane.render_right_pane(
        rows, screen, lambda: calculate_result(state, None, "en"), labels, "en"
    )
    elapsed = time.perf_counter() - start

    text = "".join(t for _, t in fragments)
    assert text.strip(), "render_right_pane produced no content -- the timing would be meaningless"
    return elapsed


def test_right_pane_redraw_is_within_budget():
    screen = _completed_drilling_screen()
    timings = [_time_right_pane_redraw(screen) for _ in range(_REPEATS)]
    worst = max(timings)
    assert worst <= _REDRAW_LATENCY_BUDGET_SECONDS, (
        f"right-pane redraw took {worst:.4f}s > {_REDRAW_LATENCY_BUDGET_SECONDS}s budget "
        f"(all runs: {[f'{t:.4f}' for t in timings]})"
    )
