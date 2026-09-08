"""Opt-in input-to-redraw latency check for the text GUI (tasks.md T036a,
spec.md SC-002, /speckit-analyze finding E1).

Measures wall-clock time from a dialog receiving its input to producing a
result, using the same headless `DummyOutput`/pipe-input technique the
pre-plan spike and this feature's other integration tests use -- but
*without* those tests' artificial inter-step delay (added there to work
around a timing race specific to *sequential* `RadioList` dialogs sharing
one pre-buffered pipe input, documented in
`tests/integration/_tui_test_support.py`; a single isolated dialog, as
measured here, is not subject to that race, so the elapsed time genuinely
reflects the framework's own response latency rather than a test-harness
artifact).

Skipped by default; run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/test_tui_redraw_latency.py \\
        -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

import time

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import input_dialog, radiolist_dialog

#: SC-002's target, in seconds.
_REDRAW_LATENCY_BUDGET_SECONDS = 0.2

_REPEATS = 5


def _time_input_dialog_round_trip() -> float:
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            pipe_input.send_text("10\r\r")
            start = time.perf_counter()
            result = input_dialog(title="Drilling", text="Drill diameter (mm)").run()
            elapsed = time.perf_counter() - start
    assert result == "10"
    return elapsed


def _time_radiolist_dialog_round_trip() -> float:
    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            pipe_input.send_text("\t\r")
            start = time.perf_counter()
            result = radiolist_dialog(
                title="Unit system", values=[("metric", "metric"), ("imperial", "imperial")]
            ).run()
            elapsed = time.perf_counter() - start
    assert result == "metric"
    return elapsed


def test_input_dialog_round_trip_is_within_budget():
    timings = [_time_input_dialog_round_trip() for _ in range(_REPEATS)]
    worst = max(timings)
    assert worst <= _REDRAW_LATENCY_BUDGET_SECONDS, (
        f"input_dialog round trip took {worst:.4f}s > {_REDRAW_LATENCY_BUDGET_SECONDS}s "
        f"budget (all runs: {[f'{t:.4f}' for t in timings]})"
    )


def test_radiolist_dialog_round_trip_is_within_budget():
    timings = [_time_radiolist_dialog_round_trip() for _ in range(_REPEATS)]
    worst = max(timings)
    assert worst <= _REDRAW_LATENCY_BUDGET_SECONDS, (
        f"radiolist_dialog round trip took {worst:.4f}s > {_REDRAW_LATENCY_BUDGET_SECONDS}s "
        f"budget (all runs: {[f'{t:.4f}' for t in timings]})"
    )
