"""The Help screen: a placeholder in this feature's scope (FR-009) --
reachable and non-crashing even with no content beyond a stub."""

from __future__ import annotations

from prompt_toolkit.shortcuts import message_dialog

from mfgparams.console.i18n import translate


def run_help_screen(locale: str) -> None:
    message_dialog(
        title=translate(locale, "tui.help.title"),
        text=translate(locale, "tui.help.text"),
        ok_text=translate(locale, "tui.action.ok"),
    ).run()
