"""The Machining submenu: Milling, Drilling (FR-009)."""

from __future__ import annotations

from mfgparams.console.i18n import translate
from mfgparams.console.tui.menu import MenuEntry, run_menu


def run_machining_menu(*, locale: str) -> str | None:
    """Returns ``"milling"``, ``"drilling"``, or ``None`` ("go back" to the
    top-level menu)."""

    entries = [
        MenuEntry("milling", translate(locale, "tui.machining_menu.milling")),
        MenuEntry("drilling", translate(locale, "tui.machining_menu.drilling")),
    ]
    return run_menu(
        title=translate(locale, "tui.machining_menu.title"), entries=entries, locale=locale
    )
