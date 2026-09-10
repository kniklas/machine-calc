"""Shared headless-testing helper for the text GUI's integration tests.

Not a test module itself (no ``test_*`` functions) -- pytest does not collect
it, matching this repo's convention of test-support modules living directly
in the directory that uses them.

Drives a synchronous, blocking text-GUI call with a scripted key sequence,
entirely offscreen: `prompt_toolkit.output.DummyOutput` renders nowhere, and
`prompt_toolkit.input.create_pipe_input` feeds keystrokes instead of a real
keyboard -- the same technique the pre-plan technical spike used
(spike-tui-framework.md) to probe framework candidates headlessly.

**018-tui-splitpane-redesign (research.md #2)**: 017's dialog-chain screens
were a *sequence* of separate, completed `Application.run()` calls, so a
test only ever needed the *final* state once `target()` returned. This
feature's persistent, single `Application` (`tui/app.py`) makes that
insufficient on its own -- e.g. confirming the right pane shows a
placeholder mid-session, before every field is complete, needs inspecting
state *while* the app is still running, not just after it exits. `run_headless`
below gained an optional `on_batch` hook for exactly this: it does not
capture rendered terminal output itself (a `DummyOutput` records nothing to
read back) -- instead, a caller closes over its own state object and a pure
render function (mirroring the pre-plan prototype's own pattern: rendering
is a plain function of state, independent of the `Application`/`Layout`
wiring) and asserts against that. The underlying thread/`contextvars`
mechanism is identical for both shapes; only the assertion pattern differs.

**Why a background thread with explicit `contextvars` propagation**: the
target call is synchronous and blocking (it calls `.run()` on a chain of
prompt-toolkit dialogs internally), so driving it requires running it
somewhere other than the thread doing the key-feeding. A plain
`threading.Thread` does **not** inherit `prompt_toolkit.application
.create_app_session`'s ambient input/output (that context is carried via
`contextvars`, which Python does not propagate to a new OS thread by
default) -- found empirically while writing this helper: an un-propagated
thread silently falls back to the *real* stdin/stdout, prints raw ANSI to
the test's actual terminal, and hangs waiting for real keystrokes that never
arrive. `contextvars.copy_context().run(...)` inside the thread target is
what makes the dialog chain see the same `DummyOutput`/pipe input the main
thread set up.

**Why staggered sends, not one upfront `send_text()`**: sending every
keystroke into the pipe before any dialog has started (rather than one
small batch per dialog, with a short pause between) was found to reliably
hang prompt-toolkit's `RadioList`-based dialogs (though not plain text-input
dialogs) the second time one runs in the same session -- a race in how a
freshly-started `Application` attaches its input reader relative to bytes
already sitting in the pipe, specific to `RadioList`'s extra key-binding
surface. Real terminal input is never delivered as one instantaneous burst,
so this is a headless-test-harness artifact, not a product defect --
verified directly: driving the real `run_drilling_screen` this way produces
a fully and correctly populated result every time, while the "send it all
at once" version hangs before completing the second dialog.
"""

from __future__ import annotations

import contextvars
import threading
from typing import Callable

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

#: Empirically reliable; see the module docstring's "staggered sends" note.
#: A longer chain of dialogs (e.g. milling's six geometry fields) showed
#: occasional flakiness at 0.08s under sandboxed-environment load, so this
#: errs generous -- it only adds wall-clock time to headless tests, not to
#: the shipped product. Bumped from 0.4 to 0.65 while adding `app.py`'s
#: Back-navigation fix (Copilot review on PR #94): re-entering the *same*
#: hand-rolled menu Application consecutively (e.g. cancelling back through
#: several menu levels in a row) needs more margin than the original
#: dialog-chain patterns did -- 0.4s reproduced the same "second instance in
#: a session doesn't see its input" race the module docstring already
#: documents for `RadioList`, just for this Application shape instead;
#: 0.5s still occasionally hung 3 consecutive instances, 0.6s+ did not
#: across repeated local runs, so 0.65s keeps a margin.
_STEP_DELAY_SECONDS = 0.65
_JOIN_TIMEOUT_SECONDS = 20.0


def run_headless(
    target: Callable[[], None],
    key_batches: list[str],
    *,
    on_batch: Callable[[], None] | None = None,
) -> None:
    """Run ``target`` (a no-argument callable wrapping the real screen/app
    call) against a scripted, staggered sequence of key batches, headlessly.

    ``on_batch``, if given, is called once before each batch is sent --
    reflecting the *previous* batch's now-settled effect (or the app's
    initial state, before the first batch), using the same
    :data:`_STEP_DELAY_SECONDS` wait that already happens there, so this
    adds no extra wall-clock cost. Also called once more after the final
    batch settles, so the last batch's effect is inspectable too. This is
    the 018-tui-splitpane-redesign mid-session-inspection hook (module
    docstring): a caller closes over its own state object/pure render
    function and asserts inside ``on_batch``, since this module has no way
    to capture rendered terminal output itself and stays deliberately
    unaware of what "state" means for the screen being driven. Not called
    if ``target`` has already returned (nothing left to inspect).

    Raises ``AssertionError`` if ``target`` has not returned within
    :data:`_JOIN_TIMEOUT_SECONDS` of the last batch being sent -- almost
    always means the key script under-supplies a step (a dialog/the app is
    still open, waiting), not a hang in the product code itself.

    Re-raises, on the calling thread, any exception ``target`` itself
    raised on its worker thread (Copilot review on PR #94: this previously
    only checked that the worker thread had *stopped*, so a screen that
    crashed outright -- as opposed to hanging -- still made this function
    return normally, and every test built on it would report success).
    """

    captured: list[BaseException] = []

    def _run_and_capture() -> None:
        # Deliberately broad: re-raised on the caller's thread below (see
        # `if captured:`), not swallowed.
        try:
            target()
        except BaseException as exc:  # noqa: BLE001
            captured.append(exc)

    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            ctx = contextvars.copy_context()
            thread = threading.Thread(target=lambda: ctx.run(_run_and_capture), daemon=True)
            thread.start()
            for batch in key_batches:
                thread.join(timeout=_STEP_DELAY_SECONDS)
                if not thread.is_alive():
                    break
                if on_batch is not None:
                    on_batch()
                pipe_input.send_text(batch)
            else:
                # Only reached if the loop completed without `break` (i.e.
                # `target` was still alive through the last batch) -- let
                # that last batch settle, then give `on_batch` one final
                # look, mirroring the per-batch call above.
                if on_batch is not None:
                    thread.join(timeout=_STEP_DELAY_SECONDS)
                    if thread.is_alive():
                        on_batch()
            thread.join(timeout=_JOIN_TIMEOUT_SECONDS)
            assert not thread.is_alive(), (
                "target did not complete -- the key-batch script likely "
                "under-supplies a step (a dialog/the app is still open, waiting for input)"
            )
    if captured:
        raise captured[0]
