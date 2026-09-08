"""Integration test: piped/no-TTY invocation exits with a clear message, no
traceback, no hang (tasks.md T031, spec.md User Story 3, FR-006, SC-005).

There is no REPL to fall back to any more -- the console must exit cleanly
instead, per the "Entry-point precedence" note in spec.md's Context.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

import mfgparams.console.cli as cli


def _terminal_size(columns: int, lines: int) -> os.terminal_size:
    return os.terminal_size((columns, lines))


@pytest.fixture(autouse=True)
def _isolate_argv(monkeypatch):
    """`cli.main()` now parses `sys.argv` before the FR-006 gate (so
    `--help` works over a pipe) -- calling it in-process, as these tests do,
    would otherwise choke on pytest's own argv."""

    monkeypatch.setattr("sys.argv", ["mfgparams"])


def test_main_exits_1_with_a_clear_message_when_stdin_is_not_a_tty(capsys):
    with (
        mock.patch("sys.stdin.isatty", return_value=False),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 25)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert captured.err.strip(), "expected a message on stderr, got nothing"
    assert "traceback" not in captured.err.lower()


def test_main_exits_1_with_a_clear_message_when_stdout_is_not_a_tty(capsys):
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("sys.stdout.isatty", return_value=False),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 25)),
    ):
        status = cli.main()

    assert status == 1
    captured = capsys.readouterr()
    assert captured.err.strip()


def test_main_never_raises_on_a_completely_uncapable_environment(capsys):
    """Piped input/output together (the common CI/scripted-invocation shape)."""

    with (
        mock.patch("sys.stdin.isatty", return_value=False),
        mock.patch("sys.stdout.isatty", return_value=False),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(0, 0)),
    ):
        try:
            status = cli.main()
        except Exception as exc:  # pragma: no cover - the assertion below is the real check
            pytest.fail(f"main() raised {exc!r} instead of exiting cleanly")

    assert status == 1


def test_the_message_does_not_mention_a_repl_fallback(capsys):
    """FR-006: must not attempt to fall back to a REPL -- there is none."""

    with (
        mock.patch("sys.stdin.isatty", return_value=False),
        mock.patch("sys.stdout.isatty", return_value=True),
        mock.patch("shutil.get_terminal_size", return_value=_terminal_size(80, 25)),
    ):
        cli.main()

    captured = capsys.readouterr()
    assert "repl" not in captured.err.lower()
