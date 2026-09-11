# Contract: Console TUI Split-Pane Structure, Interaction & Message Ownership

**Feature**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10

Mirrors this repo's existing contract style (e.g.
`specs/017-console-text-gui/contracts/console-tui-contract.md`, which this contract supersedes for
the menu/navigation structure it described): a durable, test-enforced statement of the interface
this feature exposes, not narrative documentation.

## 1. Entry points

| Invocation | Behavior after this feature |
|---|---|
| `mfgparams` (console script) | Launches the text GUI, now the persistent menu-bar/tree/pane layout instead of 017's dialog chain. |
| `python -m mfgparams` | Same — delegates to `mfgparams.__main__.main`, unchanged wiring. |
| `python -m mfgparams.console` | Same — delegates to `mfgparams.__main__.main`, unchanged wiring. |
| `mfgparams[console]` not installed | Unchanged: the existing, generic missing-extra message (`mfgparams/__main__.py`'s guard) — no change required here. |
| No TTY / terminal too small | Exits with a clear, localized, catalog-sourced message and a non-zero, documented exit status — **before** any prompt-toolkit `Application` is constructed (FR-013's gating-mechanism-unchanged requirement). The size floor itself changes: **<30×80**, raised from 017's <25×80 (research.md #1) — the complete layout (menu bar + tree + an operation's left/right panes) no longer reliably fits the old floor. |

## 2. Menu bar + Machining tree structure (FR-001/FR-002)

```
Menu bar (always visible, one row): Exit | Machining | Configuration | About | Help
                                              │
                                    (selecting expands, in place)
                                              ▼
                                    Machining tree
                                    ├── Milling   (flat leaf — opens its floating window, FR-004)
                                    └── Drilling  (flat leaf — opens its floating window, FR-004)
```

**Invariant**: the menu bar's entry set is exact — Exit, Machining, Configuration, About, Help, in
that order (FR-001). Adding a future top-level concern adds a new bar entry; it does not restructure
the other four. Enforced by `tests/contract/test_console_tui_contract.py`.

**Invariant**: the Machining tree's structure is exact — Milling and Drilling as Machining's only
children, both flat leaves with no further sub-expansion under either (FR-002; FR-003 retired via
`/speckit-clarify`, reopened after implementation). Adding a future operation (Constitution
Principle VI) adds a new leaf under Machining; it does not restructure the bar or the other leaf.
Enforced by the same contract test.

**Invariant**: collapsing/expanding the tree never changes whether an open operation screen's own
fields are reachable (FR-005a; data-model.md's `SessionUI`/`MachiningTree`/`OperationScreen`
independence). Now trivially true — the operation screen floats over the tree in a
`FloatContainer` (research.md #3), not inside it — but still enforced by an integration test that
collapses the tree with Drilling's screen open and asserts every FR-005 field, including tool
selection, is still visible and editable.

**Invariant**: every bar entry's and tree leaf's mnemonics are pairwise distinct within their own
level (reusing `menu.py`'s existing `_assign_mnemonics` validation rule, research.md). Enforced by
the same contract test.

## 3. Left/right split-pane contract (FR-004 through FR-009a)

- Selecting a leaf operation (Milling or Drilling) opens **one persistent, centered, bordered
  floating window** — a `prompt_toolkit.layout.Float` overlaid on the menu bar/tree, research.md
  #3, not an embedded pane replacing them — with a left pane (every FR-005 input, simultaneously
  visible and editable) and a right pane (the live result), without a full-screen transition
  (FR-004).
- The right pane holds exactly one of two states at any time (FR-006/FR-006a), never a third:
  **(a)** empty/placeholder (operation-specific wording), while required inputs are incomplete;
  **(b)** a valid result, once every required input holds a valid, `calculate()`-accepted value, or
  a clear, actionable, localized error from `calculate()` rejecting a complete-but-invalid
  combination (FR-006a). The right pane MUST NOT show a stale result computed from a different,
  no-longer-current input set (FR-006).
- FR-006b's unparseable-text case (revision, matching the pre-plan prototype exactly, per
  user feedback that the shipped implementation's look and feel needed to match it exactly) is
  **not** one of the right pane's states at all: an unparseable buffer never reaches
  `session_state`, so it can never reach `calculate()` either. It surfaces instead in a status bar
  beneath both panes (§4), only once the user tries to navigate away from the offending field —
  never while still typing, and never in the right pane.
- The right pane refreshes automatically on every committed left-pane input change, with no
  separate manual "calculate" action (FR-007).
- After a result is shown, the user can change inputs and see an updated result, or return to the
  menu bar/tree, without exiting and relaunching (FR-008).
- Milling and Drilling share this identical contract (FR-009); they differ only in which FR-005
  fields the left pane presents, and Milling additionally requires a reachable End-Milling/
  Face-Milling choice (FR-009a) following the same placement resolution as Drilling's tool
  selection (FR-005a).

## 4. Keyboard contract (FR-010, FR-016, FR-017)

Revision note (matching the pre-plan prototype exactly, per user feedback that the shipped
implementation's look and feel needed to match it, not a secondhand description of it): this
section replaces the `RadioList`-expansion/Tab-Shift-Tab design a prior revision of this contract
described. The keyboard model below is taken directly from the prototype's own key bindings
(`prototype_drilling_splitpane.py`/`prototype_milling_splitpane.py`), not reconstructed from
spec.md's prose.

- Every action MUST be reachable by sequential navigation (arrow keys, or their `h`/`j`/`k`/`l`
  equivalents) alone; no mouse/pointer interaction is ever required (FR-010, unchanged from 017).
- Every menu bar entry and tree leaf additionally has a direct mnemonic/accelerator key, visibly
  hinted on-screen (§2).
- **Up/Down (and `j`/`k`) always move between left-pane fields, unconditionally**, regardless of
  the current or next field's type — there is no per-field-type dispatch, and no "expanded" state
  for a radio field to consume Up/Down instead.
- A radio left-pane field (unit system, mode, material type, material, tool, milling sub-operation)
  is **always** a single `Label: value` line — it never expands into an option list (FR-005).
  **Left/Right (and `h`/`l`/Space) cycle its value with wraparound and commit it immediately**, with
  no separate confirm step.
- A numeric left-pane field becomes editable the instant it is selected/highlighted — no separate
  "start editing" keystroke (FR-016): typing a digit (or `.`/`-`) or Backspace edits
  `OperationScreen.field_buffer` immediately, and Left/Right on a selected numeric field nudges the
  buffer's value by a small step (a nudge that would land at or below zero clears the buffer to
  unset rather than producing a non-positive value). **None of this touches `session_state`.** The
  buffer commits to `session_state` only when the user navigates away from the field (Up/Down); a
  buffer that still doesn't parse as a number at that point is discarded (the field keeps its
  last-committed value) and the status bar (§3) shows the unparseable-text message until corrected.
- A "return to the main menu" action is available from any open operation screen (FR-008), and does
  not require the tree to be collapsed first (FR-005a).

## 5. Message-catalog ownership (FR-011)

- Every new message key introduced by this feature is namespaced `tui.*`, the same namespace 017
  already established — no new namespace needed, and no `tui.*` key from 017 is retired solely by
  this feature (menu bar/tree/pane labels reuse or extend that catalog; only the widgets rendering
  them change). **Named exceptions** (each a case where the widget rendering a key is removed
  entirely, not just changed, so the key's *continued existence with no consumer* would itself be
  Principle VIII drift — an orphaned catalog entry — not a way of honoring this rule):
  - `tui.configuration.select_material_type` ("View materials for type:") is retired — it labeled
    017's Configuration dialog's per-type selection prompt, and FR-014's view-only resolution
    replaced that whole interactive flow with a single static listing covering all three registries
    (FR-015), so the prompt it labeled no longer exists anywhere for it to label.
  - `tui.machining_menu.drilling_tool` ("Tool") is retired — it labeled the Machining tree's
    Drilling tool-selection shortcut row, and FR-003's retirement (this feature's own
    `/speckit-clarify` revision, reopened after implementation) removes that row entirely; Drilling
    is now a flat leaf like Milling, with no further tree-level expansion for the key to label.
- `tests/static/test_console_catalogue_ownership.py` already scans every non-`locales` file under
  `mfgparams/console/` (017's generalization) — no further generalization needed; new files this
  feature adds under `tui/` are covered automatically.
- FR-006b's "value is invalid" message is a new `tui.*` key (e.g.
  `tui.validation.unparseable_number`), localized like every other `tui.*` string — not a core/
  `mfgparams.i18n` key, since it is purely a text-GUI-layer input-parsing concern with no meaning
  outside this interface (contrast with the no-TTY/too-small-terminal message, which stays owned by
  core per 017's contract §4, unchanged here).

## 6. Feature-parity contract (FR-009, SC-004)

Every calculation the previous dialog-chain interface exposed remains reachable, calling the same
core function with the same parameter set: Drilling (`calculate()`), End Milling
(`calculate_end_milling()`), and Face Milling (`calculate_face_milling()`). For identical inputs,
this feature's results MUST be identical to PR #94's (SC-004) — this is a presentation-layer
contract change only; the calculation contract itself is unchanged and out of scope for this
feature's own tests to re-verify beyond the existing core test suite.

## 7. Versioning contract (Constitution Principle IV, Plan's Constitution Check row IV)

- This is a **MINOR** version bump, not MAJOR: `mfgparams.console` has no scriptable/programmatic
  contract to break (017 already made it TTY-only, interactive-only, with no scripting/automation
  entry point), and `--materials-config` is unchanged, so no public API breaks.
- `src/mfgparams/__init__.py`'s `__version__` MUST read `"2.1.0"` in the commit that ships this
  feature (single source of truth, Constitution Principle IV — no other file hardcodes the
  version).
- `CHANGELOG.md`'s `[Unreleased]` section MUST gain a `### Changed` entry describing the navigation
  model change (persistent menu bar/tree/split-pane replacing the sequential dialog chain), and
  MUST note the raised terminal-size floor (25×80 → 30×80) as a user-visible constraint change,
  consistent with the formatting of 017's own `### Removed` entry already in that file.
