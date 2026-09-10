"""The About screen: program name, version, license pointer.

018-tui-splitpane-redesign FR-001: reachable from the persistent menu bar
now, not a full-screen top-level menu item -- content is unchanged, but a
modal `message_dialog().run()` cannot be nested inside an already-running
persistent `Application` (prompt-toolkit does not support a second nested
event loop that way), so this is now a pure render function embedded as
body content by `app.py`, like every other body view.
"""

from __future__ import annotations

from prompt_toolkit.formatted_text import StyleAndTextTuples

import mfgparams
from mfgparams.console.i18n import translate


def render_about(locale: str) -> StyleAndTextTuples:
    text = translate(locale, "tui.about.text", name="mfgparams", version=mfgparams.__version__)
    return [
        ("class:pane-title", f"{translate(locale, 'tui.about.title')}\n\n"),
        ("", text),
    ]
