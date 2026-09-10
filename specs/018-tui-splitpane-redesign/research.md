# Phase 0 Research: Console TUI Split-Pane Redesign

**Feature**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10

Two genuine unknowns remained after `/speckit-clarify` resolved spec.md's three flagged
Assumptions (Configuration scope; drilling-type/sub-operation reading; tool-selection placement +
tree-collapse coupling — none of those needed further technical research, only a product
decision). This phase resolves the two that do.

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
expanded Machining tree (FR-002/FR-003: Machining + Milling + Drilling + the drilling-type/
tool-selection shortcut leaf, 3-4 rows including the tree's own visual nesting) gives 24-27 rows.
30 leaves an explicit ~3-6 row margin above that upper estimate — enough to absorb the imprecision
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

## Consolidated decisions for Phase 1

| Item | Decision |
|---|---|
| `terminal_capability.MIN_LINES` | 25 → 30 |
| `terminal_capability.MIN_COLUMNS` | 80 (unchanged) |
| `_tui_test_support.py` | Keep thread/`contextvars` propagation; adapt call shape to one persistent `Application` + rendered-content assertions |
| `forms.py` split | Keep unchanged: `UNIT_LABELS`, `convert_length`, `convert_power`, `render_error`, `display_label`, `material_type_label`, `unique_labels`, `format_result`. Replace: `ask_choice`, `ask_number`, `ask_required_number`, `ask_optional_number`, `ask_unit_system`, `ask_mode`, `ask_material_type`, `ask_material`, `ask_tool`, `ask_drilling_tool`, `show_result`, and the `Cancelled`/`CANCELLED` sentinel (no longer needed once fields commit-on-navigate rather than an explicit per-dialog Back/Cancel button — confirmed by the prototype). |
| `menu.py`'s `_assign_mnemonics` | Reusable as-is for the new menu bar's items and the tree's leaves — logic is about picking pairwise-unique accelerator characters from a label list, not tied to full-screen dialog rendering. |
| Contract test file | Rewrite `tests/contract/test_console_tui_contract.py` in place against the new `contracts/console-tui-splitpane-contract.md` (017's contract described the now-replaced dialog-chain menu structure; no value in a second, differently-named contract test file for the same subsystem). |
