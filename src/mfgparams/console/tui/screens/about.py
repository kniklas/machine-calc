"""The About screen: program name, version, license pointer."""

from __future__ import annotations

from prompt_toolkit.shortcuts import message_dialog

import mfgparams
from mfgparams.console.i18n import translate


def run_about_screen(locale: str) -> None:
    text = translate(
        locale, "tui.about.text", name="mfgparams", version=mfgparams.__version__
    )
    message_dialog(
        title=translate(locale, "tui.about.title"),
        text=text,
        ok_text=translate(locale, "tui.action.ok"),
    ).run()
