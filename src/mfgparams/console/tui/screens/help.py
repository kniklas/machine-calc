"""The Help screen: a placeholder in this feature's scope (FR-009) --
reachable and non-crashing even with no content beyond a stub.

018-tui-splitpane-redesign: same rendering-mechanism change as about.py --
a pure render function embedded as body content, not a modal dialog.
"""

from __future__ import annotations

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import translate


def render_help(locale: str) -> StyleAndTextTuples:
    return [
        ("class:pane-title", f"{translate(locale, 'tui.help.title')}\n\n"),
        ("", translate(locale, "tui.help.text")),
    ]
