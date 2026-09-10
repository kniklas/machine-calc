"""UI-state entities and application wiring for the text GUI
(018-tui-splitpane-redesign).

See data-model.md's `SessionUI`/`MachiningTree`/`OperationScreen` entities.
Unlike 017's dialog chain (a sequence of short-lived, separately-constructed
`Application`s, one per screen), `run()` below constructs a single
persistent `Application`/`Layout` for the whole session: the menu bar, the
Machining tree, and an open operation screen are all fields on one
`SessionUI` object rather than a "current screen" stack, and can coexist
(FR-005a) rather than being mutually exclusive.

Note on FR-013a (terminal resize): 017's `NavigationState`-based module
docstring reasoned that prompt-toolkit's own resize handling needed no
opt-in, since no screen there ever constructed a *new* `Application`
mid-resize. That reasoning doesn't carry over unexamined here -- this
feature's single, long-lived `Application` is a materially different shape
(constructed once, not per screen), so whether in-progress left-pane input
survives a resize needs re-verifying against *this* shape specifically
(tasks.md T029), not assumed from 017's now-superseded architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal, cast

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams.console.i18n import get_locale
from mfgparams.console.tui.menu import MenuEntry
from mfgparams.i18n import get_raw_locale
from mfgparams.i18n import translate as _translate_core
from mfgparams.models import CalculationResult, MillingSubOperation
from mfgparams.registry_config import RegistryConfigError

if TYPE_CHECKING:
    # Deferred to type-checking only: `screens/drilling.py`/`screens/milling.py`
    # import `FieldId`/`OperationScreen` *from this module* at their own
    # module level (T022/T023), so importing them back here eagerly would be
    # a circular import. Safe as a type-only import because
    # `from __future__ import annotations` (above) means `OperationScreen`'s
    # `session_state` annotation below is never evaluated at runtime.
    from prompt_toolkit.application import Application

    from mfgparams.console.tui.screens.drilling import DrillingSessionState
    from mfgparams.console.tui.screens.milling import MillingSessionState


# -- 018-tui-splitpane-redesign: UI-state entities (data-model.md) --------
#
# Supersedes 017's `ScreenId`/`NavigationState`, which modeled a mutually-
# exclusive, one-screen-at-a-time dialog chain (each screen its own
# short-lived `Application`). This feature's single persistent `Application`
# can show the menu bar, the Machining tree, and an open operation screen
# all at once, so `SessionUI` below is the single source of truth for that
# instead -- not a stack of "current screen"s.


class FieldId(Enum):
    """Every left-pane field either operation can present (FR-005/FR-009),
    the union across Drilling and Milling -- a screen's own field order
    (data-model.md's `OperationScreen`) selects the subset relevant to its
    operation and current mode, mirroring the pre-plan prototype's own
    field-ordering approach (spec's Recommended Next Steps)."""

    UNIT_SYSTEM = "unit_system"
    MODE = "mode"
    MATERIAL_TYPE = "material_type"
    MATERIAL = "material"
    TOOL = "tool"
    SUB_OPERATION = "sub_operation"
    DIAMETER = "diameter"
    DEPTH = "depth"
    AXIAL_DEPTH_OF_CUT = "axial_depth_of_cut"
    RADIAL_ENGAGEMENT = "radial_engagement"
    FEED_PER_TOOTH = "feed_per_tooth"
    NUMBER_OF_TEETH = "number_of_teeth"
    LENGTH_OF_CUT = "length_of_cut"
    TARGET_RPM = "target_rpm"
    AVAILABLE_POWER = "available_power"


@dataclass(frozen=True)
class MenuBar:
    """FR-001's persistent horizontal bar -- a fixed, closed entry set
    (unlike 017's `run_top_level_menu`, which built a *fresh* entry list per
    screen instance; this one never changes at runtime). Reuses `menu.py`'s
    existing `MenuEntry(value, label)` shape rather than inventing a new
    entry type."""

    entries: tuple[MenuEntry, ...]


@dataclass
class MachiningTree:
    """FR-002/FR-003's collapsible Milling/Drilling navigation, replacing
    `machining_menu.py`'s full-screen submenu. `drilling_expanded` is only
    meaningful while `expanded` is `True`; collapsing Machining implicitly
    collapses it too (data-model.md's validation rule) -- there is no
    independent sub-state to preserve across a Machining collapse/expand.

    Milling has no equivalent sub-expansion: FR-002/FR-003 define
    tree-level expansion for Drilling only (/speckit-analyze finding I1),
    so there is no `milling_expanded` field here.
    """

    expanded: bool = False
    drilling_expanded: bool = False

    def toggle_machining(self) -> None:
        """Acceptance Scenarios 2/4: expand if collapsed; collapse (and
        implicitly collapse the Drilling sub-node too) if expanded."""

        self.expanded = not self.expanded
        if not self.expanded:
            self.drilling_expanded = False

    def toggle_drilling(self) -> None:
        """Acceptance Scenario 3: only meaningful while `expanded`; a no-op
        otherwise (there is nothing to expand into if Machining itself is
        collapsed)."""

        if self.expanded:
            self.drilling_expanded = not self.drilling_expanded


@dataclass
class OperationScreen:
    """FR-004's left/right split-pane screen for whichever operation
    (Drilling or Milling, FR-009's identical pattern) is currently open.

    `last_result`/`last_result_key` implement FR-006's "MUST NOT display a
    result computed from a different, no-longer-current set of inputs" as
    a cache keyed on the exact input tuple that produced it (mirroring the
    pre-plan prototype's own `_last_result_key` pattern), not a bare flag.
    """

    operation: Literal["drilling", "milling"]
    session_state: DrillingSessionState | MillingSessionState
    selected_field: FieldId
    field_buffer: str = ""
    last_result: CalculationResult | None = None
    last_result_key: tuple[object, ...] | None = None


@dataclass
class SessionUI:
    """The single persistent session object `run()` owns for the whole run
    (018-tui-splitpane-redesign), replacing `NavigationState`. `tree` and
    `open_operation` are deliberately independent fields with no code path
    writing both from the same handler (FR-005a's invariant, enforced by
    construction -- see `test_session_ui.py`): collapsing/expanding the
    tree never affects which operation screen is open, and vice versa.
    """

    menu_bar: MenuBar
    tree: MachiningTree = field(default_factory=MachiningTree)
    open_operation: OperationScreen | None = None
    drilling_state: DrillingSessionState = field(default_factory=lambda: _default_drilling_state())
    milling_states: dict[MillingSubOperation, MillingSessionState] = field(
        default_factory=lambda: _default_milling_states()
    )
    locale: str = "en"
    materials_config_path: str | None = None


def _default_drilling_state() -> DrillingSessionState:
    """Deferred import (see the `TYPE_CHECKING` block above): only called at
    `SessionUI()` construction time, well after both modules have finished
    importing, so this cannot hit the drilling.py<->app.py import cycle a
    module-level import of `DrillingSessionState` would."""

    from mfgparams.console.tui.screens.drilling import DrillingSessionState

    return DrillingSessionState()


def _default_milling_states() -> dict[MillingSubOperation, MillingSessionState]:
    from mfgparams.console.tui.screens.milling import MillingSessionState

    return {sub: MillingSessionState() for sub in MillingSubOperation}


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


@dataclass
class _ViewState:
    """Which body is currently shown and which row is highlighted within
    it -- pure UI-presentation state, deliberately *not* part of
    :class:`SessionUI` (which holds session/business state that survives a
    body change, per FR-012). ``body_mode`` names what the body currently
    renders; it is independent of ``SessionUI.tree.expanded``/
    ``open_operation`` (FR-005a) -- e.g. selecting Configuration from the
    bar sets ``body_mode="configuration"`` without touching either.
    """

    body_mode: Literal["tree", "drilling", "milling", "configuration", "about", "help"] | None = (
        None
    )
    bar_selected: int = 0
    tree_selected: int = 0


def _render_body(ui: SessionUI, view: _ViewState, display_locale: str) -> StyleAndTextTuples:
    """Dispatch on ``view.body_mode`` for every body *except* an open
    operation screen -- that one is a split-pane (left+right), not a
    single-pane body, and is rendered separately by ``build_app``'s
    ``DynamicContainer`` (see its own docstring)."""

    from mfgparams.console.tui import machining_menu
    from mfgparams.console.tui.screens.about import render_about
    from mfgparams.console.tui.screens.configuration import render_configuration
    from mfgparams.console.tui.screens.help import render_help

    if view.body_mode == "tree":
        return machining_menu.render_tree(ui.tree, view.tree_selected, ui.locale, focused=True)
    if view.body_mode == "about":
        return render_about(ui.locale)
    if view.body_mode == "help":
        return render_help(ui.locale)
    if view.body_mode == "configuration":
        return render_configuration(ui.materials_config_path, ui.locale, display_locale)
    return [("class:hint", "Select Machining, Configuration, About, or Help.")]


def _open_milling(
    ui: SessionUI, view: _ViewState, materials_config_path: str | None, display_locale: str
) -> None:
    """Opens with whichever sub-operation's state was last active
    (defaulting to End Milling, FR-009a)."""

    from mfgparams.console.tui.screens import milling, split_pane

    state = ui.milling_states[MillingSubOperation.END_MILLING]
    screen = OperationScreen(
        operation="milling", session_state=state, selected_field=FieldId.UNIT_SYSTEM
    )
    ui.open_operation = screen
    view.body_mode = "milling"
    rows = milling.rows_for(ui, screen, materials_config_path, ui.locale, display_locale)
    split_pane.sync_buffer(rows, screen)


def _open_drilling(
    ui: SessionUI,
    *,
    selected_field: FieldId,
    materials_config_path: str | None,
    display_locale: str,
) -> OperationScreen:
    """Reuses the existing ``OperationScreen`` if Drilling is already open
    (FR-012 carryover -- re-entering must not discard it), only replacing
    ``selected_field`` so the tree's tool-selection shortcut (FR-005a)
    actually lands focus on that field rather than always resetting to the
    first one."""

    from mfgparams.console.tui.screens import drilling, split_pane

    existing = ui.open_operation
    if existing is not None and existing.operation == "drilling":
        screen = existing
        screen.selected_field = selected_field
    else:
        screen = OperationScreen(
            operation="drilling", session_state=ui.drilling_state, selected_field=selected_field
        )
        ui.open_operation = screen
    rows = drilling.rows_for(screen, materials_config_path, ui.locale, display_locale)
    split_pane.sync_buffer(rows, screen)
    return screen


def build_app(  # noqa: C901
    materials_config_path: str | None, locale: str, display_locale: str
) -> tuple[Application[None], SessionUI, _ViewState]:
    """Construct the persistent `Application` plus its `SessionUI`/
    `_ViewState`, without running it -- split out from `run()` so tests can
    drive the returned `Application` headlessly (`_tui_test_support.py`'s
    `on_batch` hook, research.md #2) while asserting directly against the
    returned `ui`/`view` objects via pure inspection, not by trying to
    capture rendered terminal output.

    Focus model (018-tui-splitpane-redesign; no direct 017 precedent -- see
    the design note recorded when this was decided): the bar and the body
    are two focus regions in one persistent `Layout`, not separate
    `Application`s. Escape from the body moves focus to the bar without
    touching any `SessionUI` state (`tree`/`open_operation` untouched) --
    this is how a user reaches the bar's Machining item to collapse the
    tree without losing an open operation's field values (FR-005a,
    quickstart.md Scenario 5). Escape from the bar itself closes the
    current operation and returns to a blank top level if one was open, or
    exits the app if nothing was open (mirroring 017's own
    Escape-at-the-root-exits precedent). The bar's own Exit entry always
    exits unconditionally.
    """

    # noqa: C901 justification -- this is a composition root, not deep
    # logic: it wires ~25 independently-trivial key-binding handlers (each
    # a few lines, no nested branching of its own) around one persistent
    # `Application`'s `ui`/`view`/`app`/`bar_control`/`left_control`/
    # `right_control` closures. Every self-contained decision block that
    # *was* extractable without fragmenting that shared closure state
    # already has been (`split_pane.power_and_rpm_rows`,
    # `milling._tool_registry_for`, the top-level
    # `_render_body`/`_open_milling`/`_open_drilling` helpers). Extracting
    # the key-binding registrations themselves would require threading 6+
    # shared mutable references through new top-level functions (or a
    # mutable-`Application`-ref indirection, since `app` does not exist
    # until after the bindings that close over it are defined) -- net less
    # readable than the current flat, docstring-annotated registration, not
    # more.
    from prompt_toolkit.application import Application
    from prompt_toolkit.filters import Condition
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import DynamicContainer, HSplit, Layout, VSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style

    from mfgparams.console.i18n import translate
    from mfgparams.console.tui import forms, machining_menu
    from mfgparams.console.tui.menu import _assign_mnemonics, default_entries, render_menu_bar
    from mfgparams.console.tui.screens import drilling, milling, split_pane

    bar_entries = default_entries(locale)
    bar_mnemonics = _assign_mnemonics(bar_entries)
    ui = SessionUI(
        menu_bar=MenuBar(entries=tuple(bar_entries)),
        locale=locale,
        materials_config_path=materials_config_path,
    )
    view = _ViewState()

    style = Style.from_dict({"mnemonic": "underline bold", "selected": "reverse", "hint": "italic"})

    bar_control = FormattedTextControl(
        lambda: render_menu_bar(bar_entries, bar_mnemonics, view.bar_selected, focused=on_bar()),
        focusable=True,
    )
    body_control = FormattedTextControl(
        lambda: _render_body(ui, view, display_locale), focusable=True
    )

    def on_bar() -> bool:
        return app.layout.has_focus(bar_control)

    def _current_tree_row_count() -> int:
        return len(machining_menu.tree_rows(ui.tree))

    def _current_pane_rows() -> list[split_pane.Row]:
        """The open operation's `split_pane.Row` list, recomputed fresh on
        every access (like `_current_tree_row_count`'s tree-row recompute)
        since a row's presence/options can depend on another row's just-
        committed value (T021's `rows_for` docstring)."""

        op = ui.open_operation
        if op is None:
            return []
        if op.operation == "drilling":
            return drilling.rows_for(op, materials_config_path, ui.locale, display_locale)
        return milling.rows_for(ui, op, materials_config_path, ui.locale, display_locale)

    def _render_left_pane() -> StyleAndTextTuples:
        op = ui.open_operation
        assert op is not None
        title_key = "tui.drilling.title" if op.operation == "drilling" else "tui.milling.title"
        return split_pane.render_left_pane(
            _current_pane_rows(),
            op,
            translate(ui.locale, title_key),
            ui.locale,
            focused=not on_bar(),
        )

    def _calculate_current_operation() -> CalculationResult:
        op = ui.open_operation
        assert op is not None
        if op.operation == "drilling":
            return drilling.calculate_result(
                cast("DrillingSessionState", op.session_state), materials_config_path, ui.locale
            )
        return milling.calculate_result(
            ui, cast("MillingSessionState", op.session_state), materials_config_path, ui.locale
        )

    def _render_right_pane() -> StyleAndTextTuples:
        op = ui.open_operation
        assert op is not None
        labels = forms.UNIT_LABELS[op.session_state.unit_system]
        return split_pane.render_right_pane(
            _current_pane_rows(), op, _calculate_current_operation, labels, ui.locale
        )

    left_control = FormattedTextControl(_render_left_pane, focusable=True)
    right_control = FormattedTextControl(_render_right_pane, focusable=False)

    def _current_body():
        if view.body_mode in ("drilling", "milling") and ui.open_operation is not None:
            return VSplit(
                [
                    Window(content=left_control),
                    Window(width=1, char="│"),
                    Window(content=right_control),
                ]
            )
        return Window(content=body_control)

    def _activate_bar_entry() -> None:
        entry = bar_entries[view.bar_selected]
        if entry.value == "exit":
            app.exit()
        elif entry.value == "machining":
            ui.tree.toggle_machining()
            if ui.tree.expanded:
                view.body_mode = "tree"
                view.tree_selected = 0
                app.layout.focus(body_control)
            elif view.body_mode == "tree":
                view.body_mode = None
        elif entry.value == "configuration":
            view.body_mode = "configuration"
            app.layout.focus(body_control)
        elif entry.value == "about":
            view.body_mode = "about"
            app.layout.focus(body_control)
        elif entry.value == "help":
            view.body_mode = "help"
            app.layout.focus(body_control)

    def _activate_tree_row() -> None:
        rows = machining_menu.tree_rows(ui.tree)
        row = rows[view.tree_selected]
        if row.action == "open_milling":
            _open_milling(ui, view, materials_config_path, display_locale)
            app.layout.focus(left_control)
        elif row.action == "toggle_drilling":
            ui.tree.drilling_expanded = not ui.tree.drilling_expanded
            view.tree_selected = min(view.tree_selected, _current_tree_row_count() - 1)
        elif row.action == "open_drilling_tool":
            _open_drilling(
                ui,
                selected_field=FieldId.TOOL,
                materials_config_path=materials_config_path,
                display_locale=display_locale,
            )
            view.body_mode = "drilling"
            app.layout.focus(left_control)

    bindings = KeyBindings()

    @bindings.add("escape", filter=Condition(on_bar))
    def _escape_bar(event) -> None:
        if ui.open_operation is not None:
            ui.open_operation = None
            # Acceptance Scenario 5: "land back at the menu bar/tree", not a
            # blank body -- if the tree is still expanded (it isn't touched
            # by closing an operation, FR-005a), show it rather than the
            # generic hint.
            view.body_mode = "tree" if ui.tree.expanded else None
        else:
            event.app.exit()

    @bindings.add("escape", filter=Condition(lambda: not on_bar()))
    def _escape_body(event) -> None:
        event.app.layout.focus(bar_control)

    @bindings.add("left", filter=Condition(on_bar))
    @bindings.add("h", filter=Condition(on_bar))
    def _bar_left(event) -> None:
        view.bar_selected = (view.bar_selected - 1) % len(bar_entries)

    @bindings.add("right", filter=Condition(on_bar))
    @bindings.add("l", filter=Condition(on_bar))
    def _bar_right(event) -> None:
        view.bar_selected = (view.bar_selected + 1) % len(bar_entries)

    @bindings.add("enter", filter=Condition(on_bar))
    def _bar_enter(event) -> None:
        _activate_bar_entry()

    for index, mnemonic in enumerate(bar_mnemonics):
        if mnemonic is None:
            continue

        def _bar_jump(event, target_index: int = index) -> None:
            view.bar_selected = target_index
            _activate_bar_entry()

        bindings.add(mnemonic, filter=Condition(on_bar))(_bar_jump)

    tree_focused = Condition(lambda: not on_bar() and view.body_mode == "tree")

    @bindings.add("up", filter=tree_focused)
    @bindings.add("k", filter=tree_focused)
    def _tree_up(event) -> None:
        view.tree_selected = (view.tree_selected - 1) % _current_tree_row_count()

    @bindings.add("down", filter=tree_focused)
    @bindings.add("j", filter=tree_focused)
    def _tree_down(event) -> None:
        view.tree_selected = (view.tree_selected + 1) % _current_tree_row_count()

    @bindings.add("enter", filter=tree_focused)
    def _tree_enter(event) -> None:
        _activate_tree_row()

    @bindings.add(Keys.Any, filter=tree_focused)
    def _tree_mnemonic(event) -> None:
        """Contract §4: tree leaves get mnemonics too, same as the bar's
        own entries -- but unlike the bar's fixed entry set, the tree's row
        set changes at runtime (`drilling_expanded`), so this can't be a
        fixed per-character binding assigned once at startup the way the
        bar's are; it re-derives the current rows'/mnemonics' mapping on
        every keypress and only acts if the pressed key matches one."""

        rows = machining_menu.tree_rows(ui.tree)
        mnemonics = machining_menu.tree_mnemonics(rows, ui.locale)
        pressed = event.data.lower()
        for index, mnemonic in enumerate(mnemonics):
            if mnemonic == pressed:
                view.tree_selected = index
                _activate_tree_row()
                return

    pane_focused = Condition(
        lambda: not on_bar()
        and view.body_mode in ("drilling", "milling")
        and ui.open_operation is not None
    )

    @bindings.add("up", filter=pane_focused)
    @bindings.add("k", filter=pane_focused)
    def _pane_up(event) -> None:
        assert ui.open_operation is not None
        split_pane.move_selection(_current_pane_rows(), ui.open_operation, -1)

    @bindings.add("down", filter=pane_focused)
    @bindings.add("j", filter=pane_focused)
    def _pane_down(event) -> None:
        assert ui.open_operation is not None
        split_pane.move_selection(_current_pane_rows(), ui.open_operation, 1)

    @bindings.add("left", filter=pane_focused)
    def _pane_left(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, -1)

    @bindings.add("right", filter=pane_focused)
    def _pane_right(event) -> None:
        assert ui.open_operation is not None
        split_pane.nudge_selected(_current_pane_rows(), ui.open_operation, 1)

    @bindings.add("backspace", filter=pane_focused)
    def _pane_backspace(event) -> None:
        assert ui.open_operation is not None
        split_pane.backspace_selected(_current_pane_rows(), ui.open_operation)

    @bindings.add(Keys.Any, filter=pane_focused)
    def _pane_char(event) -> None:
        """FR-016: typing a digit (or `.`/`-`) immediately edits the
        selected numeric field -- a no-op on a `RadioRow` (`edit_selected`'s
        own guard) and on any other character (radios never take free
        text; contract §4 has no mnemonic requirement for pane rows)."""

        assert ui.open_operation is not None
        data = event.data
        if data and (data.isdigit() or data in ".-"):
            split_pane.edit_selected(_current_pane_rows(), ui.open_operation, data)

    root = HSplit(
        [
            Window(content=bar_control, height=1),
            Window(height=1, char="─"),
            DynamicContainer(_current_body),
        ]
    )
    app: Application[None] = Application(
        layout=Layout(root, focused_element=bar_control),
        key_bindings=bindings,
        style=style,
        full_screen=True,
    )
    return app, ui, view


def run(materials_config_path: str | None = None) -> None:
    """Run the text GUI until the user exits from the menu bar.

    Resolves the active locale exactly once, at startup (mirrors the REPL's
    same FR-019c guarantee), and holds one session-lifetime state object per
    operation (drilling, and one per milling sub-operation) so revisiting a
    screen after a calculation offers the previous answers as defaults,
    exactly as the REPL's loop did (FR-002, SC-005 parity) -- Acceptance
    Scenario 3: the user can start another calculation without exiting and
    relaunching the text GUI. See `build_app` for the actual wiring.
    """

    locale = get_locale()
    display_locale = get_raw_locale()
    _resolve_materials_config(materials_config_path, locale)
    app, _ui, _view = build_app(materials_config_path, locale, display_locale)
    app.run()
