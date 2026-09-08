"""Shared headless-testing helper for the text GUI's integration tests.

Not a test module itself (no ``test_*`` functions) -- pytest does not collect
it, matching this repo's convention of test-support modules living directly
in the directory that uses them.

Drives a synchronous, blocking text-GUI call (e.g. `run_drilling_screen`)
with a scripted key sequence, entirely offscreen: `prompt_toolkit.output
.DummyOutput` renders nowhere, and `prompt_toolkit.input.create_pipe_input`
feeds keystrokes instead of a real keyboard -- the same technique the
pre-plan technical spike used (spike-tui-framework.md) to probe framework
candidates headlessly.

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
#: the shipped product.
_STEP_DELAY_SECONDS = 0.4
_JOIN_TIMEOUT_SECONDS = 20.0


def run_headless(target: Callable[[], None], key_batches: list[str]) -> None:
    """Run ``target`` (a no-argument callable wrapping the real screen call)
    against a scripted, staggered sequence of key batches, headlessly.

    Raises ``AssertionError`` if ``target`` has not returned within
    :data:`_JOIN_TIMEOUT_SECONDS` of the last batch being sent -- almost
    always means the key script under-supplies a step (a dialog is still
    open, waiting), not a hang in the product code itself.
    """

    with create_pipe_input() as pipe_input:
        with create_app_session(input=pipe_input, output=DummyOutput()):
            ctx = contextvars.copy_context()
            thread = threading.Thread(target=lambda: ctx.run(target), daemon=True)
            thread.start()
            for batch in key_batches:
                thread.join(timeout=_STEP_DELAY_SECONDS)
                if not thread.is_alive():
                    break
                pipe_input.send_text(batch)
            thread.join(timeout=_JOIN_TIMEOUT_SECONDS)
            assert not thread.is_alive(), (
                "target did not complete -- the key-batch script likely "
                "under-supplies a step (a dialog is still open)"
            )
