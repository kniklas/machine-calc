"""Regression test for `_tui_test_support.run_headless` itself (Copilot
review on PR #94): it previously only checked that the worker thread had
*stopped*, so a screen that crashed outright still made it return
normally, and every test built on it would report a false success. This
confirms a crash on the worker thread is now re-raised on the calling
(test) thread instead of being swallowed.
"""

from __future__ import annotations

import pytest
from _tui_test_support import run_headless


class _Boom(RuntimeError):
    pass


def test_a_crashing_target_is_reraised_not_swallowed():
    def crashing_target() -> None:
        raise _Boom("simulated screen crash")

    with pytest.raises(_Boom, match="simulated screen crash"):
        run_headless(crashing_target, [])


def test_a_normally_completing_target_still_returns_cleanly():
    completed = []

    def target() -> None:
        completed.append(True)

    run_headless(target, [])
    assert completed == [True]
