# Phase 0 Research: Console TUI Split-Pane Redesign

**Feature**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10

Two genuine unknowns remained after `/speckit-clarify` resolved spec.md's three flagged
Assumptions (Configuration scope; drilling-type/sub-operation reading; tool-selection placement +
tree-collapse coupling — none of those needed further technical research, only a product
decision). This phase resolves the two that do (items 1-2 below).

**Revision (this plan re-run)**: `/speckit-clarify` was reopened after implementation, per user
feedback on PR #96 preferring the pre-plan prototype's UI over what shipped — FR-004's floating
window and FR-005's `RadioList` rendering are new requirements that raise two further technical
unknowns, resolved as items 3-4 below.

## 1. Terminal-size floor for the complete layout

**Question**: spec.md's revised terminal-size Assumption estimates the complete layout (menu bar +
expanded Machining tree + an operation's left/right panes) "plausibly pushes the real total past
25 rows," based on the throwaway prototype's measured pane height alone (menu bar and tree were
deliberately out of scope for that prototype). What should `MIN_COLUMNS`/`MIN_LINES` actually be?

**Decision**: Raise `MIN_LINES` from 25 to **30**; keep `MIN_COLUMNS` at 80 (unaffected — the
prototype's combined pane width, 76-91 chars including the floating frame's own border, already
fits comfortably within 80, and neither the menu bar (one row) nor the tree (a handful of short
labels) add meaningful width).

**Rationale**: Reconstructing the prototype's own row math (spec.md's Assumption) for Milling,
the larger of the two operations: 16-17 rows for the left pane's 13-14 fields (already including
its title line) + 1 divider + 1-2 for the merged status row + 2-3 for the floating frame's
border/shadow = 20-22 rows for the operation screen alone. Adding FR-001's menu bar (1 row) and an
expanded Machining tree (FR-002: Machining + Milling + Drilling, 3 rows, flat — item #4 below
retired Drilling's tree-level tool-selection shortcut, so there is no further sub-expansion row to
add here) gives 24-25 rows. 30 leaves an explicit ~5-6 row margin above that upper estimate — enough
to absorb the imprecision
the original Assumption already flagged (its own numbers are "a reasoned estimate... not a verified
measurement of the full screen... together") without needing a second prototype pass purely to
shave rows off an already-tight floor. A too-small floor fails open into FR-006's-equivalent
degradation message (`terminal_capability.check()`, unchanged mechanism, FR-013) rather than a
silent rendering bug, so erring slightly generous here is the safe direction — the cost of getting
it wrong is a rejected small terminal, not a broken large one.

**Alternatives considered**:
- **Keep 25** (the literal current value): rejected — the prototype's own math already exceeds it
  for Milling before the menu bar/tree are even added; shipping unchanged risks admitting terminals
  that can't actually show every FR-005 input simultaneously, which FR-013 explicitly forbids doing
  "despite a layout that may no longer fit it."
- **Run a second full prototype pass** (menu bar + tree + operation screen actually assembled) to
  get an exact number before committing: rejected for this plan — the first prototype's numbers are
  concrete and specific enough to reason from directly (not a rough guess), and the margin (30 vs.
  an estimated 24-27) already absorbs the kind of small discrepancy a second pass would surface.
  Revisit if `tasks.md`'s own acceptance walkthrough (spec's Carried-Over Items table, 017's
  tasks.md T037 folded in here) finds 30 still too tight in a real terminal.
- **A larger round number (e.g. 35 or 40)**: rejected as unjustified padding — nothing in the
  measured data supports needing that much slack, and Principle V's legacy-hardware framing (older
  terminals, not necessarily large ones) argues against inflating the floor further than the
  evidence requires.

## 2. Headless-testing support for a single persistent `Application`

**Question**: `tests/integration/_tui_test_support.py`'s existing helper is documented as driving
"a chain of prompt-toolkit dialogs internally" — a sequence of separate, completed `.run()` calls.
This feature replaces that with one long-lived `Application`/`Layout` constructed once per session
(`app.py`, rewritten). Does the existing helper's background-thread-plus-`contextvars` technique
still apply, or does it need a different shape?

**Decision**: The core technique (a background thread running `contextvars.copy_context().run(...)`
against a `DummyOutput`/pipe-input pair created via `prompt_toolkit.application.create_app_session`)
**stays** — that mechanism is about propagating prompt-toolkit's ambient input/output context across
a thread boundary, which is unrelated to how many `Application.run()` calls happen inside the
driven function. What changes is the **call shape being driven and the assertion style**: the old
helper's callers invoke it once per dialog-chain screen (`run_drilling_screen`, etc.), asserting on
each dialog's own return value as the chain progresses. The new helper drives **one call** to the
persistent `app.py` entry point for the whole session, and assertions read the *rendered* left/right
pane content at chosen points in the keystroke sequence (matching FR-006a's/FR-006b's spec-level
requirement to assert against "the actual rendered/displayed result," not an intermediate return
value) — `prompt_toolkit.output.DummyOutput` doesn't capture drawn content on its own, so this needs
a capturing `Output` (e.g. wrapping/subclassing `DummyOutput` to record the last-rendered screen, or
driving the `Application`'s `Layout` directly to read a control's own text) resolved during
implementation, not fixed here.

**Rationale**: Keeping the underlying propagation technique avoids re-solving an already-debugged
problem (the helper's own docstring documents the specific failure mode — falling back to real
stdin/stdout — that the current approach was built to avoid); the part that must change is exactly
the part that's tied to the old chain-of-screens shape, not the thread/contextvars plumbing itself.

**Alternatives considered**:
- **Rewrite the helper from scratch**: rejected — the thread/`contextvars` propagation problem it
  solves is orthogonal to single-`Application`-vs-dialog-chain and would be redundant work.
- **Drive the `Application` via its own `key_processor` directly, bypassing the pipe-input
  mechanism**: rejected — would diverge from the spike's own validated headless-testing method
  (spike-tui-framework.md) that this repo has used consistently since 017, for no clear benefit.

## 3. Floating-window construction and interaction with the bar/tree underneath it

**Question**: `/speckit-clarify` (revision session, reopened after implementation per PR #96
feedback) resolved FR-004 to a centered, bordered/shadowed floating window over the persistent
menu bar/tree, matching the pre-plan prototype's own confirmed finding — but the prototype itself
never had a menu bar/tree to float *over* (it was a standalone script, spec's Carried-Over Items
table). What prompt-toolkit primitive builds this, and does the bar/tree stay visible and
interactive behind/around the float, or does opening an operation screen hide them the way a modal
would?

**Decision**: `prompt_toolkit.layout.FloatContainer` wraps the existing bar+tree `HSplit` as its
`content`, with a single `Float` (holding the operation screen's own `HSplit`/`VSplit`, wrapped in
a `Frame` for the border) added to its `floats` list only while `SessionUI.open_operation` is set.
The bar and tree remain visible underneath and keep their own state (FR-005a) — the float does not
hide or replace them, only draws over the region it occupies, consistent with FR-004's "overlaid on
top of... rather than replacing them inline." Keyboard focus moves to the float's content on open
(mirroring 017's own per-dialog-focus precedent) and back to the bar on Escape (unchanged from the
already-implemented focus model), so the bar/tree being visually present does not imply they are
simultaneously *interactive* while the float has focus — only that collapsing/expanding the tree
before or after the float is open never discards its state (FR-005a, unchanged guarantee).

**Rationale**: `FloatContainer`/`Float` is prompt-toolkit's own primitive for exactly this shape
(a layer drawn on top of a base layout, sized/positioned independently) — no custom overlay
compositing needed. Keeping the bar/tree as the `FloatContainer`'s `content` (rather than, say,
swapping the whole `Layout.container` when a float opens) means `SessionUI.tree`'s state genuinely
never needs to be torn down or rebuilt across an operation screen opening/closing, which is what
makes FR-005a's independence guarantee hold structurally, not just by convention.

**Alternatives considered**:
- **A second, nested `Application`** for the floating window: rejected outright — prompt-toolkit
  does not support a nested `Application.run()` call (the same constraint that motivated 017's
  About/Help/Configuration becoming pure render functions rather than their own dialogs remains
  true here).
- **Nothing floats; keep the current embedded `DynamicContainer` body-swap, only add a visible
  border around it**: rejected per the revision's own explicit resolution (FR-004) — a bordered
  embedded pane still replaces the bar/tree inline, which is exactly what this revision changes.

## 4. RadioList integration: does the whole form fit if every radio field renders as a full list?

**Question**: FR-005 (revised) requires every radio field (unit system, mode, material type,
material, tool) to render as `prompt_toolkit.widgets.RadioList` — which draws **one row per
option**, always, not a collapsed one-line summary. Drilling's material list alone (six bundled
metals/woods, more with a `--materials-config` override) would need that many rows just for one
field. If every radio field on the left pane expands simultaneously, the row math research.md #1
already did (which assumed each field was a single summary line) no longer holds, and the 30-row
floor is not enough for a form with several multi-option fields all open at once.

**Decision**: Only the **currently-selected/focused** radio field renders as a full `RadioList`
(every option, one per row, arrow-key-navigable); every other radio field on the same screen
collapses to a single-line `Label: current value` summary, exactly like the shipped implementation
already does for every field — expanding to the full list only when navigation brings focus to it,
collapsing back to the summary line when focus moves away. This is the accordion pattern: at most
one field is ever "open" on a given left pane at a time.

**Rationale**: This is the only reading of "match the prototype exactly" that keeps the terminal
floor math from research.md #1 intact — the prototype's own confirmed 16-17-row estimate for
Milling's left pane (Assumptions, spec.md) already implies a single summary line per field
(13-14 fields in ~16-17 rows is only possible if fields are mostly one row each), so the prototype
itself cannot have shown every option of every radio field simultaneously either; the *widget*
that changed is `RadioList` replacing the current inline `(•) label` renderer for whichever field
is focused, not the overall one-line-per-field layout for the rest of the screen. FR-016's
"the moment it is selected/highlighted" framing already establishes that a field's presentation
changing on selection is expected, native behavior for this feature, not new.

**Consequence for the keyboard contract (§4)**: `RadioList`'s own native bindings are Up/Down to
move the highlighted option and Enter/Space to select it — not Left/Right cycling. While a radio
field is focused and expanded, Up/Down navigates its options (replacing the shipped
implementation's Left/Right-cycles-the-value behavior for radio fields specifically); Left/Right
continue to nudge a focused *numeric* field by a step (FR-017, unchanged). Moving to a different
left-pane field (collapsing the current one back to its summary line) uses the same Up/Down or
Tab navigation already used to move between fields today — at the first/last option of an open
`RadioList`, Up/Down continues past it to the previous/next field rather than stopping, so a
single consistent key still moves both within and between fields.

**Alternatives considered**:
- **Show every option of every radio field simultaneously, all the time**: rejected — blows the
  terminal floor past any reasonable size for a form with several multi-option fields, and was
  ruled out by the row-math cross-check above regardless.
- **Keep Left/Right cycling even for the new `RadioList` widget** (fighting the widget's own
  native bindings): rejected — `RadioList` is a real, pre-built prompt-toolkit widget specifically
  because it already has correct, tested Up/Down/Enter/Space handling; re-wiring it to ignore that
  and respond to Left/Right instead reintroduces custom key-binding code for behavior the widget
  already provides, undermining the point of adopting it.

## Consolidated decisions for Phase 1

| Item | Decision |
|---|---|
| `terminal_capability.MIN_LINES` | 25 → 30 |
| `terminal_capability.MIN_COLUMNS` | 80 (unchanged) |
| `_tui_test_support.py` | Keep thread/`contextvars` propagation; adapt call shape to one persistent `Application` + rendered-content assertions |
| `forms.py` split | Keep unchanged: `UNIT_LABELS`, `convert_length`, `convert_power`, `render_error`, `display_label`, `material_type_label`, `unique_labels`, `format_result`. Replace: `ask_choice`, `ask_number`, `ask_required_number`, `ask_optional_number`, `ask_unit_system`, `ask_mode`, `ask_material_type`, `ask_material`, `ask_tool`, `ask_drilling_tool`, `show_result`, and the `Cancelled`/`CANCELLED` sentinel (no longer needed once fields commit-on-navigate rather than an explicit per-dialog Back/Cancel button — confirmed by the prototype). |
| `menu.py`'s `_assign_mnemonics` | Reusable as-is for the new menu bar's items and the tree's leaves — logic is about picking pairwise-unique accelerator characters from a label list, not tied to full-screen dialog rendering. |
| Contract test file | Rewrite `tests/contract/test_console_tui_contract.py` in place against the new `contracts/console-tui-splitpane-contract.md` (017's contract described the now-replaced dialog-chain menu structure; no value in a second, differently-named contract test file for the same subsystem). |
| Operation screen container | `prompt_toolkit.layout.FloatContainer` wrapping the existing bar+tree `HSplit`, with a `Float` (holding a bordered `Frame`) added/removed as `SessionUI.open_operation` is set/cleared (research.md #3). |
| Radio field rendering | `prompt_toolkit.widgets.RadioList` for the currently-focused radio field only; every other radio field on the same screen shows a one-line `Label: value` summary (research.md #4, accordion pattern) — not every option of every field simultaneously. |
| Radio field keyboard contract | Up/Down navigates an open `RadioList`'s options (its own native binding); Left/Right continues to nudge a focused numeric field only (FR-017, unchanged) — this revises contract §4's earlier "radio fields cycle on Left/Right" line, which described the now-superseded inline-summary renderer (research.md #4). |
| Machining tree | Flattens: `MachiningTree` loses its `drilling_expanded` field entirely (Drilling has no tree-level sub-expansion any more, FR-003 retired) — `expanded` is now its only field. |
