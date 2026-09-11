"""Opt-in input-to-redraw latency check for the text GUI
(018-tui-splitpane-redesign spec.md SC-006, tasks.md T030).

017's version of this test measured a dialog *round trip* (input sent,
`Application.run()` returns) -- which never actually observed a redraw at
all: the old dialog chain computed and displayed a result exactly once,
when the screen exited, not reactively (spec's Carried-Over Items table:
"the old version's timer started before input and stopped at dialog exit,
never observing an actual redraw"). This feature introduces the first
*real* reactive redraw (FR-007: the right pane recomputes on every
committed left-pane change, with no separate "calculate" action).

Revision note (round-3 code-review finding on PR #96): an earlier version
of this file drove `split_pane.render_right_pane` directly against a
hand-built `DrillingSessionState`/row list, entirely bypassing `app.py`'s
real `Application`, key-binding dispatch table, and `_current_pane_rows()`
memoization cache -- so it could never have caught a regression in any of
those. This version instead builds the real `Application` (`app.py`'s
`build_app`) and drives it through its actual key bindings -- the same
`KeyProcessor.feed`/`process_keys` calls prompt-toolkit's own input loop
makes on a real keystroke, run synchronously inside one `asyncio` call
rather than through `_tui_test_support.run_headless`'s threaded,
staggered-delay pipe-input harness (deliberately unsuitable here: that
harness's own module docstring documents fixed ~0.65s per-batch delays
needed for reliability, which would swamp a latency budget measured in
milliseconds) -- then times the literal `FormattedTextControl.text`
callable prompt-toolkit's renderer invokes for the right pane
(`app.py`'s `_render_right_pane`, identified by name off the real,
live `Layout`), immediately after a real, distinct diameter edit commits
through the real key-binding path. This measures the real input-to-redraw
cost SC-006 is about, not just the pure calculation function underneath it.

Skipped by default; run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/test_tui_redraw_latency.py \\
        -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.output import DummyOutput

from mfgparams.console.i18n import get_locale
from mfgparams.console.tui import app as app_mod
from mfgparams.i18n import get_raw_locale

#: SC-006's target, in seconds -- "responsive, perceived instantaneous".
_REDRAW_LATENCY_BUDGET_SECONDS = 0.2

#: Five distinct diameters -- each forces a genuinely fresh `calculate()`
#: call (verified empirically: each produces a different spindle speed),
#: so this can't pass on a stale cached value the way a single repeated
#: measurement could.
_DIAMETERS = ("11", "12", "13", "14", "15")


def _feed(key_processor, *tokens: str) -> None:
    special = {"enter": Keys.Enter, "escape": Keys.Escape, "backspace": Keys.Backspace}
    for token in tokens:
        if token in special:
            key_processor.feed(KeyPress(special[token]))
        else:
            for char in token:
                key_processor.feed(KeyPress(char))
    key_processor.process_keys()


async def _measure_real_right_pane_redraws() -> list[float]:
    """Drives the real `Application` to a completed Drilling screen (the
    same key sequence `test_tui_app_run.py`'s
    `_OPEN_DRILLING_COMPLETE_AND_EXIT` prefix uses, up through landing on
    Available power), then edits the diameter `len(_DIAMETERS)` times,
    timing the real right-pane control's `.text()` call once per edit."""

    timings: list[float] = []
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            application, ui, _view = app_mod.build_app(None, get_locale(), get_raw_locale())
            kp = application.key_processor
            feed: Callable[..., None] = lambda *tokens: _feed(kp, *tokens)  # noqa: E731

            feed("m", "j", "enter")  # Machining -> Drilling, opens directly
            feed("j", "j", "l")  # Unit system -> Mode -> Material type, cycle
            feed("j", "l")  # Material, cycle
            feed("j", "l")  # Tool, cycle
            feed("j")  # Diameter
            feed("10")
            feed("j")  # Depth -- commits Diameter
            feed("20")
            feed("j")  # Available power -- commits Depth
            assert ui.open_operation is not None

            controls = application.layout.find_all_controls()
            right_controls = [
                c
                for c in controls
                if isinstance(c, FormattedTextControl)
                and getattr(c.text, "__name__", "") == "_render_right_pane"
            ]
            assert (
                len(right_controls) == 1
            ), f"expected exactly one right-pane control, found {len(right_controls)}"
            right_control = right_controls[0]

            feed("k", "k")  # back up to Diameter
            for diameter_text in _DIAMETERS:
                feed("backspace", "backspace", "backspace", "backspace", "backspace")
                feed(diameter_text)
                feed("j")  # commits the new Diameter, moves to Depth

                start = time.perf_counter()
                fragments = right_control.text()
                timings.append(time.perf_counter() - start)

                text = "".join(t for _, t in fragments)
                assert (
                    text.strip()
                ), "right-pane control produced no content -- the timing would be meaningless"
                feed("k")  # back up to Diameter for the next edit

            diameters_seen = {float(d) for d in _DIAMETERS}
            assert ui.open_operation.session_state.diameter in diameters_seen
    return timings


def test_right_pane_redraw_is_within_budget():
    timings = asyncio.run(_measure_real_right_pane_redraws())
    worst = max(timings)
    assert worst <= _REDRAW_LATENCY_BUDGET_SECONDS, (
        f"right-pane redraw took {worst:.4f}s > {_REDRAW_LATENCY_BUDGET_SECONDS}s budget "
        f"(all runs: {[f'{t:.4f}' for t in timings]})"
    )
