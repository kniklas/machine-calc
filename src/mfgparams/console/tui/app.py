"""Navigation state and application wiring for the text GUI.

See data-model.md's NavigationState entity. The actual screen-to-screen
transitions are driven by the dialog-chain each screen module implements
(a menu/form returns the next screen to show, or ``None`` for "go back");
:class:`NavigationState` mirrors that as an explicit, independently testable
data structure rather than being the sole dispatch mechanism -- useful for
introspection (e.g. an About screen or future breadcrumb) and for T008's
unit test to exercise push/pop/back semantics without needing a real
terminal.

Note on FR-008 (terminal resize, /speckit-analyze finding E2): every screen
here is a prompt-toolkit `Application`/dialog `.run()` call, and
prompt-toolkit's own event loop already redraws in place on a terminal
resize (SIGWINCH) without losing in-progress widget state -- there is
nothing this module needs to do to opt into that behavior. What matters is
that no screen constructs a *new* Application mid-resize (which would
discard not-yet-submitted input); this module never does, since each
screen's dialog chain is a sequence of separate, completed `.run()` calls,
not a resize-triggered reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from mfgparams.console.i18n import get_locale
from mfgparams.i18n import get_raw_locale
from mfgparams.i18n import translate as _translate_core
from mfgparams.models import MillingSubOperation
from mfgparams.registry_config import RegistryConfigError


class ScreenId(Enum):
    """Every screen the text GUI can show (contracts/console-tui-contract.md §2)."""

    MENU = "menu"
    MACHINING_MENU = "machining_menu"
    MILLING_FORM = "milling_form"
    DRILLING_FORM = "drilling_form"
    CONFIGURATION = "configuration"
    ABOUT = "about"
    HELP = "help"


@dataclass
class NavigationState:
    """The text GUI's single source of truth for "what's on screen and how did we get here."

    Not persisted (spec Assumptions: "No new persistence") -- held for the
    lifetime of one session only.
    """

    current_screen: ScreenId = ScreenId.MENU
    screen_stack: list[ScreenId] = field(default_factory=list)
    locale: str = "en"
    materials_config_path: str | None = None

    def push(self, screen: ScreenId) -> None:
        """Navigate to ``screen``, remembering the current one for "go back".

        ``MENU`` is the root and is never pushed onto its own stack (there is
        nothing to go back to from it).
        """

        if self.current_screen is not ScreenId.MENU:
            self.screen_stack.append(self.current_screen)
        self.current_screen = screen

    def pop(self) -> ScreenId:
        """Go back to the prior screen, or ``MENU`` if the stack is empty.

        Never raises -- an empty stack is a normal state (already at the
        menu, or one push deep), not an error.
        """

        self.current_screen = self.screen_stack.pop() if self.screen_stack else ScreenId.MENU
        return self.current_screen


def _resolve_materials_config(materials_config_path: str | None, locale: str) -> None:
    """Validate ``materials_config_path`` once at startup. Ported unchanged
    from `console/cli.py`'s `_resolve_materials_config` (research.md #3):
    raises `SystemExit` (after printing a translated error) if the file
    exists but is malformed, prints a translated non-fatal notice and
    proceeds with bundled defaults if the path is missing/unreadable, and
    does nothing if ``materials_config_path`` is ``None``.
    """

    from mfgparams import list_end_mill_tools, list_face_mill_tools, list_materials, list_tools
    from mfgparams.registry import materials_load_notice

    if materials_config_path is None:
        return

    try:
        list_materials(config_path=materials_config_path)
        list_tools(config_path=materials_config_path)
        list_end_mill_tools(config_path=materials_config_path)
        list_face_mill_tools(config_path=materials_config_path)
    except RegistryConfigError as exc:
        print(_translate_core(locale, exc.message_key, **exc.kwargs))
        raise SystemExit(1) from exc

    notice_key, notice_kwargs = materials_load_notice(materials_config_path)
    if notice_key:
        print(_translate_core(locale, notice_key, **dict(notice_kwargs)))


def run(materials_config_path: str | None = None) -> None:
    """Run the text GUI until the user exits from the top-level menu.

    Resolves the active locale exactly once, at startup (mirrors the REPL's
    same FR-019c guarantee), and holds one session-lifetime state object per
    operation (drilling, and one per milling sub-operation) so revisiting a
    screen after a calculation offers the previous answers as defaults,
    exactly as the REPL's loop did (FR-002, SC-005 parity) -- Acceptance
    Scenario 3: the user can start another calculation without exiting and
    relaunching the text GUI.
    """

    from mfgparams.console.tui.machining_menu import run_machining_menu
    from mfgparams.console.tui.menu import run_top_level_menu
    from mfgparams.console.tui.screens.about import run_about_screen
    from mfgparams.console.tui.screens.configuration import run_configuration_screen
    from mfgparams.console.tui.screens.drilling import DrillingSessionState, run_drilling_screen
    from mfgparams.console.tui.screens.help import run_help_screen
    from mfgparams.console.tui.screens.milling import MillingSessionState, run_milling_screen

    locale = get_locale()
    display_locale = get_raw_locale()

    _resolve_materials_config(materials_config_path, locale)

    state = NavigationState(locale=locale, materials_config_path=materials_config_path)
    drilling_state = DrillingSessionState()
    milling_states = {sub: MillingSessionState() for sub in MillingSubOperation}

    # Screens that just run once and pop back to whatever pushed them,
    # regardless of whether that run ended in cancellation or a completed
    # calculation -- MENU and MACHINING_MENU are handled separately below
    # since they instead decide *which* screen to push next.
    simple_screens: dict[ScreenId, Callable[[], None]] = {
        ScreenId.MILLING_FORM: lambda: run_milling_screen(
            milling_states, materials_config_path, locale, display_locale
        ),
        ScreenId.DRILLING_FORM: lambda: run_drilling_screen(
            drilling_state, materials_config_path, locale, display_locale
        ),
        ScreenId.CONFIGURATION: lambda: run_configuration_screen(materials_config_path, locale),
        ScreenId.ABOUT: lambda: run_about_screen(locale),
        ScreenId.HELP: lambda: run_help_screen(locale),
    }

    # Driven by `state.current_screen`/`push`/`pop` (Copilot review on PR #94:
    # this loop previously reset to MENU at the top of every iteration and
    # never called `pop()`, so "go back" from Drilling/Milling skipped the
    # Machining submenu entirely instead of returning to it one level at a
    # time, per contract §3).
    while True:
        if state.current_screen is ScreenId.MENU:
            choice = run_top_level_menu(locale=locale)
            if choice is None:
                return  # Escape/Ctrl-Q at the root: exit the app.
            _push_top_level_choice(state, choice)
            continue

        if state.current_screen is ScreenId.MACHINING_MENU:
            sub_choice = run_machining_menu(locale=locale)
            _push_machining_choice(state, sub_choice)
            continue

        simple_screens[state.current_screen]()
        state.pop()


def _push_top_level_choice(state: NavigationState, choice: str) -> None:
    """`run`'s MENU branch: which screen a top-level menu choice pushes.
    Extracted from `run` (Constitution Principle I / complexity gate)."""

    if choice == "machining":
        state.push(ScreenId.MACHINING_MENU)
    elif choice == "configuration":
        state.push(ScreenId.CONFIGURATION)
    elif choice == "about":
        state.push(ScreenId.ABOUT)
    elif choice == "help":
        state.push(ScreenId.HELP)


def _push_machining_choice(state: NavigationState, sub_choice: str | None) -> None:
    """`run`'s MACHINING_MENU branch: which screen a submenu choice pushes,
    or back to the top-level menu on cancel. Extracted from `run`
    (Constitution Principle I / complexity gate)."""

    if sub_choice == "milling":
        state.push(ScreenId.MILLING_FORM)
    elif sub_choice == "drilling":
        state.push(ScreenId.DRILLING_FORM)
    else:
        state.pop()  # Escape/Ctrl-Q: back to the top-level menu.
