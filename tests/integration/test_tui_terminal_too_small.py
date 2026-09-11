"""Integration test: a terminal below 30x80 exits with a clear message
(tasks.md T032, spec.md FR-008/FR-011/FR-013, quickstart.md Scenario 9 --
raised from 017's 25-row floor, research.md #1)."""

from __future__ import annotations

import os
from unittest import mock

import pytest

import mfgparams.console.cli as cli


def _terminal_size(columns: int, lines: int) -> os.terminal_size:
    return os.terminal_size((columns, lines))


@pytest.fixture(autouse=True)
def _isolate_argv(monkeypatch):
    """See test_tui_no_tty_fallback.py's identical fixture docstring."""

    monkeypatch.setattr("sys.argv", ["mfgparams"])


def test_main_exits_1_when_terminal_is_too_narrow(capsys):
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        # lines held at exactly the floor so this isolates a columns-only
        # failure, not a combined columns+lines one.
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(79, 30)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert "79" in captured.err
    assert "30" in captured.err  # the required minimum, per the message template


def test_main_exits_1_when_terminal_is_too_short(capsys):
    """29, not 24: below the *new* 30-row floor but at-or-above the *old*
    25-row one, so this specifically confirms the new floor is in effect
    (research.md #1) rather than merely re-testing the old boundary."""

    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 29)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert "29" in captured.err


def test_main_succeeds_at_exactly_the_minimum_size():
    """30x80 is the minimum *supported* size, not the threshold for
    rejection -- FR-011 is a target *at or above* which no scrolling is
    needed; exactly-minimum must not be treated as "too small"."""

    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 30)),
    ):
        from mfgparams.console.tui import terminal_capability

        result = terminal_capability.check()

    assert result.supported is True
