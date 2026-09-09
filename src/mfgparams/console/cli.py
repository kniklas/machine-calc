"""Console entry point: launches the text GUI, or exits with a clear message
if this terminal cannot support it (specs/017-console-text-gui).

The REPL this module used to hold is deleted entirely (FR-001, FR-007) --
not hidden behind a flag, not kept for scripting. See spec.md's "Entry-point
precedence" note in Context for why, and contracts/console-tui-contract.md
§1 for the full entry-point contract.

`main()` here is the FR-006/User Story 3 negative-path implementation
itself, not a stub deferred elsewhere (/speckit-analyze finding F2): it
calls `terminal_capability.check()` (research.md #2) *before* importing or
constructing anything prompt-toolkit-related, and exits via the catalog
message on failure.
"""

from __future__ import annotations

import argparse
import sys

from mfgparams.console.tui import terminal_capability
from mfgparams.i18n import get_locale, translate
from mfgparams.logging_setup import configure_logging


def _report_unsupported_terminal(capability: terminal_capability.TerminalCapability) -> int:
    """Print the FR-006 message and return the exit status."""

    locale = get_locale()
    if not capability.has_tty:
        reason = translate(locale, "console.tui_unavailable.reason.no_tty")
    else:
        reason = translate(
            locale,
            "console.tui_unavailable.reason.too_small",
            columns=capability.columns,
            lines=capability.lines,
            min_columns=terminal_capability.MIN_COLUMNS,
            min_lines=terminal_capability.MIN_LINES,
        )
    message = translate(
        locale,
        "console.tui_unavailable",
        reason=reason,
        min_columns=terminal_capability.MIN_COLUMNS,
        min_lines=terminal_capability.MIN_LINES,
    )
    print(message, file=sys.stderr)
    return 1


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments (currently just ``--materials-config``)."""

    parser = argparse.ArgumentParser(prog="mfgparams")
    parser.add_argument(
        "--materials-config",
        dest="materials_config",
        default=None,
        metavar="PATH",
        help=(
            "Optional path to a TOML file adding/overriding materials and "
            "drilling tools (see contracts/materials-config-schema.md)."
        ),
    )
    return parser.parse_args(argv)


def main() -> int:
    """Console-script entry point (``mfgparams`` / ``python -m mfgparams``).

    Returns the process exit status: ``1`` if this terminal cannot support
    the text GUI (FR-006), otherwise whatever the text GUI returns once it
    has run to completion (``0`` when it returns nothing).

    Argument parsing runs *before* the terminal-capability gate, not after:
    ``--help``/``-h`` (and an invalid argument) must work over a pipe like
    any ordinary CLI tool's does -- `argparse` exits on its own for both
    before this function would otherwise reach the gate, and gating first
    would incorrectly block a `--help` request piped through `| less` or a
    CI script with the FR-006 message instead of the help text.
    """

    configure_logging()
    args = _parse_args()

    capability = terminal_capability.check()
    if not capability.supported:
        return _report_unsupported_terminal(capability)

    from mfgparams.console.tui.app import run

    try:
        run(materials_config_path=args.materials_config)
    except (KeyboardInterrupt, EOFError):
        print()
    return 0
