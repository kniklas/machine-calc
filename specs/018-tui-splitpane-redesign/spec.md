# Feature Specification: Console TUI Split-Pane Redesign

**Feature Branch**: `018-tui-splitpane-redesign`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Redesign the console text GUI's navigation and input model, as a
follow-up to PR #94 (specs/017-console-text-gui, merged 2026-09-09). Replace the current sequential
full-screen dialog-chain wizard with a persistent horizontal menu bar (Exit, Machining,
Configuration, Help), a collapsible tree under Machining (Milling / Drilling, with Drilling further
expandable), a left pane holding all input widgets for the selected operation simultaneously, and a
right pane showing results that refreshes once inputs are complete, with an option to repeat the
calculation or return to the main menu. Milling follows the same left/right-pane pattern as
Drilling."

## Context

[PR #94](https://github.com/kniklas/mfgparams/pull/94) (`specs/017-console-text-gui`, merged
2026-09-09) replaced `mfgparams.console`'s REPL with a full-screen text GUI: a sequential chain of
full-screen `prompt-toolkit` `shortcuts` dialogs (`radiolist_dialog`/`input_dialog`), one field per
screen — for Drilling, for example, unit system, calculation mode, material type, material, tool,
diameter, hole depth, and power/RPM are each their own screen, answered one at a time before a
result is shown.

That interaction model works but is not user-friendly for this feature's target audience (users
unfamiliar with computers, per 017's own FR-009–FR-012 novice-usability framing): each field
requires a full screen transition, there is no way to see or adjust an earlier answer without
backing out field-by-field, and the user cannot see more than one input at a time. This feature
replaces that model with a persistent, always-visible layout: a horizontal top-level menu bar, a
collapsible navigation tree for choosing an operation, a left pane holding every input for that
operation at once, and a right pane showing the result.

This is a genuine architecture change, not a tweak to 017's screens: it replaces a chain of
separate, completed `Application.run()` dialog calls with one long-lived layout
(`VSplit`/`HSplit`) holding multiple simultaneously-focusable widgets and a reactively-refreshed
result pane. It therefore supersedes 017's dialog-chain design (`plan.md`, `research.md`,
`contracts/console-tui-contract.md`) rather than amending it, and is scoped as its own feature.

**What this feature reuses from PR #94, unchanged**: the core calculation call wiring
(`calculate()`, `calculate_end_milling()`, `calculate_face_milling()`), the validation functions
and unit-conversion helpers, `DrillingSessionState`/`MillingSessionState`'s field semantics and
default-carryover-across-visits behavior, the i18n message catalog, and the entry-point/no-TTY/
terminal-too-small gating in `terminal_capability.py`.

**What this feature replaces**: `menu.py`'s hand-rolled mnemonic-driven menu, `machining_menu.py`,
`forms.py`'s dialog-based `ask_*` prompt functions, and the screen-orchestration sequencing in
`drilling.py`/`milling.py` that drives that dialog chain one field at a time. The interaction-
model-specific integration tests built against that chain (`test_tui_drilling.py`,
`test_tui_milling.py`, `test_tui_resize_preserves_input.py`, and the harness they share) are
expected to be substantially rewritten, not preserved as-is.

## Clarifications

### Session 2026-09-10

- Q: Should the Configuration screen stay read-only, or gain create/edit capability? → A: View-only — a read-only display of the existing materials/tools registries (drilling, end-mill, face-mill per FR-015), matching 017's default assumption.
- Q: Is the tree's "drilling type" choice today's tool selection relocated, or a genuinely new categorization? → A: Relocation (reading a) — no new domain concept, no backend changes to `processes.machining.drilling` needed. Placement (left pane vs. tree vs. both) and its coupling to tree-collapse behavior (FR-005a) remain separately open.
- Q: Where should tool selection live — left pane only, tree only, or both — and how does that interact with tree-collapse behavior? → A: Both — the tree shows it as a navigation shortcut (satisfying FR-003), the left pane always retains full editable control (satisfying FR-005), and tree-collapse is therefore safe by construction with no collapse-prevention logic needed.

### Session 2026-09-10 (revision — reopened after implementation, per user feedback on PR #96 preferring the discarded pre-plan prototype's UI)

- Q: Should an open Drilling or Milling screen render as a floating/overlaid window on top of the menu bar and tree, rather than replacing the body inline the way the shipped implementation does today? → A: Yes — a bordered, positioned panel floats above the persistent bar+tree layout underneath it (`prompt_toolkit.layout.Float`/`FloatContainer`), superseding FR-004's "opens ... a screen" shape and this session's own now-superseded "Both" resolution above for *how* the screen is reached, though not necessarily for whether tool selection itself stays reachable from the tree (see below).
- Q: Should the Machining tree drop Drilling's tool-selection sub-expansion entirely, so Drilling becomes a direct, flat leaf under Machining exactly like Milling, with tool selection reachable only from the floating screen's left pane? → A: Yes — the tree flattens to Machining → Milling, Drilling (both direct leaves); tool selection lives only in Drilling's left pane. This retires FR-003 and supersedes this session's earlier "Both" resolution (the second bullet above) and its "relocation, not a new categorization" framing (the first bullet above) — the tree no longer has a drilling-type step to relocate anything into.
- Q: Should every radio-style left-pane field (unit system, mode, material type, material, tool) render as `prompt_toolkit.widgets.RadioList` (one option per line, vertically stacked, arrow-highlighted) rather than the shipped implementation's single-line `(•) label  ( ) label` inline text? → A: Yes — match the prototype's own solution exactly, which used prompt-toolkit's native `RadioList` widget rather than a hand-rolled inline-text renderer (the user's explicit direction: implement exactly as the earlier accepted prototype, not a reinterpretation of it).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate by menu bar and tree instead of a dialog chain (Priority: P1)

A user launches the console text GUI and sees a persistent horizontal menu bar (Exit, Machining,
Configuration, About, Help) instead of a full-screen list of choices. Selecting Machining expands
a tree showing Milling and Drilling as flat, direct leaves (revised via `/speckit-clarify`,
reopened after implementation — see Clarifications; Drilling has no further tree-level
sub-expansion of its own).
Selecting a leaf operation opens that operation's floating split-pane window (User Story 2) over
the menu bar and tree, without a separate full-screen transition for either of them.

**Why this priority**: This is the foundational navigation shell every other user story depends on
— without it, there is nothing to select an operation from.

**Independent Test**: Can be fully tested by launching the app, expanding Machining, and confirming
the tree renders and collapses correctly and selecting either flat leaf (Milling or Drilling) opens
the corresponding operation's floating window — independent of what that window's panes contain.

**Acceptance Scenarios**:

1. **Given** the app has just launched, **When** the user looks at the screen, **Then** a
   horizontal menu bar reading Exit, Machining, Configuration, About, Help is visible and none of
   the other menu items require navigating away from it to see.
2. **Given** the menu bar is visible, **When** the user selects Machining, **Then** a tree expands
   in place showing Milling and Drilling, without replacing the whole screen.
3. **Given** the Machining tree is expanded, **When** the user selects Drilling, **Then** it opens
   Drilling's floating operation screen directly (FR-004) — Drilling is a flat leaf, exactly like
   Milling, with no further tree-level expansion (revised via `/speckit-clarify`, reopened after
   implementation; see Clarifications).
4. **Given** a tree is expanded, **When** the user collapses it (e.g. re-selecting Machining or
   pressing a dedicated collapse action), **Then** it returns to its collapsed state without
   losing the user's place in the menu bar.

---

### User Story 2 - Enter every input for an operation in one pane (Priority: P1)

Having selected an operation (e.g. Drilling), the user sees a left pane containing every input for
that calculation at once: unit system (radio, default metric), calculation mode (radio, default
standard), material type (radio over every registered category — Metal and Wood are the bundled
defaults, but a user-supplied materials config can register further categories, e.g. Plastic; see
FR-005), expanding to a further radio choice of the specific material, and plain editable fields
for diameter, hole depth, and available power, and tool selection — editable only here, with no
tree-level shortcut into it (FR-005/FR-005a, revised via `/speckit-clarify`). The user can move
between and edit any of these without a screen transition.

**Why this priority**: This is the core usability improvement this feature exists to deliver —
without it, the redesign offers no benefit over 017's dialog chain.

**Independent Test**: Can be fully tested by opening the Drilling screen, changing each left-pane
input in any order (not just top-to-bottom), and confirming every change is reflected without
leaving the pane.

**Acceptance Scenarios**:

1. **Given** the Drilling screen is open, **When** the user views the left pane, **Then** unit
   system, calculation mode, material type, tool selection, diameter, hole depth, and available
   power are all visible and editable without a screen transition (tool selection is reachable
   only here — the tree has no shortcut into it, per FR-005/FR-005a as revised).
2. **Given** the left pane is open, **When** the user selects "Metal" for material type, **Then**
   a further radio choice of specific metals expands in the same pane (and analogously for
   "Wood").
3. **Given** the user has already entered several inputs, **When** they change an earlier input
   (e.g. unit system), **Then** later inputs are not discarded except where they are genuinely
   unit-dependent (mirroring PR #94's unit-system-carryover fix — see Context), and the user is not
   sent back to a different screen to do so.
4. **Given** the Milling screen is open, **When** the user views its left pane, **Then** the same
   simultaneous-input pattern applies to milling's own inputs (mirroring Drilling's pattern, per
   the feature description).
5. **Given** a numeric field, **When** the user types text that cannot be parsed as a number,
   **Then** the field remains immediately editable, a clear and actionable localized message
   indicates the value is invalid, and the unparseable text is never passed to `calculate()`/its
   milling counterparts (FR-006b).

---

### User Story 3 - See results in a persistent pane and repeat or exit (Priority: P2)

Once every required left-pane input has a valid value, the right pane shows the calculation
result, refreshed automatically. After seeing a result, the user can choose to change inputs and
recompute, or return to the main menu, without the application restarting or losing the tree's
expand/collapse state.

**Why this priority**: This closes the loop User Story 2 opens — inputs without a visible result
are not a complete calculator — but it is reachable only once P1 exists, and its "repeat or return"
convenience is secondary to the input experience itself.

**Independent Test**: Can be fully tested by completing all left-pane inputs for one operation,
confirming the right pane shows a result, then changing one input and confirming the right pane
refreshes, then explicitly choosing to return to the main menu and confirming the app is back at
User Story 1's navigation shell rather than exited or reset.

**Acceptance Scenarios**:

1. **Given** the left pane has an incomplete or invalid set of inputs, **When** the user views the
   right pane, **Then** it does not show a stale or misleading result from a previous, different
   input set.
2. **Given** every left-pane input is complete and valid, **When** the last input is entered,
   **Then** the right pane shows the calculation result without a separate confirmation step.
3. **Given** a result is showing, **When** the user changes any left-pane input, **Then** the
   right pane's result updates to match, clears until the inputs are complete again, or — if every
   input holds a value but the combination is rejected by calculation (e.g. an engagement value
   invalid relative to diameter) — shows the resulting clear, actionable, localized error instead
   of a blank pane (FR-006a).
4. **Given** a result is showing, **When** the user chooses to run another calculation, **Then**
   they can do so from the same screen without restarting the application (mirroring PR #94's own
   Acceptance Scenario 3 parity guarantee).
5. **Given** a result is showing, **When** the user chooses to return to the main menu, **Then**
   they land back at the menu bar/tree from User Story 1, with the tree in a sensible state (not
   necessarily still expanded to the same leaf).

---

### Edge Cases

- What happens when the terminal is too small for the menu bar + two panes, even if it met 017's
  25×80 floor for a single dialog? (See the revised terminal-size Assumption — the floor likely
  needs raising; the completed prototype gave concrete row-count evidence, though the full screen
  with menu bar and tree together still needs a follow-up pass to confirm the exact number.)
- What happens when the terminal is resized mid-session, with left-pane input already entered but
  not yet submitted? (FR-013a: the application MUST adapt without discarding it — a requirement
  that needs re-verifying for this feature's persistent, long-lived `Application`, not assumed
  carried over from 017's short-lived, per-screen `Application` construction.)
- How does the system handle the user switching from Milling to Drilling (or vice versa) via the
  tree while the left pane has partially-entered, unsaved input for the operation being left? (Per
  017's existing per-operation session-state pattern, each operation's own state should be
  preserved independently — switching away and back should not discard it.)
- **Resolved (FR-006a)**: a left-pane input that becomes invalid only in combination with another
  (e.g. an engagement value invalid relative to a diameter that was itself just changed) shows the
  clear, actionable, localized error `calculate()` already returns for it, rather than clearing the
  pane to nothing.
- **Resolved (see Clarifications)**: collapsing the Machining tree while a leaf operation's screen
  is open does not close that screen — only the tree's own visual state changes. Trivially true
  since the floating operation window (FR-004, revised via `/speckit-clarify`) is not part of the
  tree at all: it floats above the bar+tree layout and is unaffected by the tree's own
  expand/collapse state, not merely "safe by construction" via a dual tree/left-pane placement
  that no longer exists (FR-005a).
- The application must remain fully operable by keyboard alone, with no mouse/pointer interaction
  required for any action — carried over unchanged from 017's own Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST display a persistent horizontal top-level menu bar containing
  exactly these items: Exit, Machining, Configuration, About, Help. Machining/Configuration/About/
  Help carry forward 017's FR-009 item set unchanged (About is not otherwise mentioned in this spec
  because its own screen and content are out of scope for this redesign; only its menu-bar placement
  changes from a full-screen menu item to a persistent bar item). Exit is new to this feature: 017
  had no labeled "Exit" menu item, only an unlabeled Escape/Ctrl-Q handler at the root menu (see
  `tui/app.py`'s `run` loop) — a persistent bar with no "root screen" to Escape from needs an
  explicit, discoverable Exit entry instead.
- **FR-002**: Selecting Machining MUST expand a collapsible tree showing Milling and Drilling as
  its children, without requiring a separate full-screen transition.
- **FR-003**: *(Retired via `/speckit-clarify`, reopened after implementation — see Clarifications.)*
  Drilling has no tree-level sub-expansion: it is a direct leaf under Machining, exactly like
  Milling (FR-002). Tool selection lives only in Drilling's left pane (FR-005) — the tree-level
  "drilling-type" navigation shortcut this requirement originally described no longer exists.
- **FR-004**: Selecting a leaf operation (a specific drilling choice, or Milling) MUST open a
  centered, bordered floating window (with a shadow, matching PR #94's existing dialog styling —
  the pre-plan prototype's own confirmed finding, below), overlaid on top of the persistent menu
  bar and Machining tree rather than replacing them inline, containing a left pane (inputs) and a
  right pane (results) for that operation (resolved via `/speckit-clarify`, reopened after
  implementation — see Clarifications).
- **FR-005**: The left pane MUST present all of the following simultaneously, each editable
  without a screen transition: unit system (radio, default metric), calculation mode (radio,
  default standard), material type (radio built from every category `list_material_types()`
  currently returns for the active materials config, not hardcoded to Metal/Wood — those are only
  the bundled defaults; a user-supplied config can register further categories, and PR #94's
  existing `ask_material_type`/`forms.py` already builds this radio dynamically from that list, a
  behavior this feature MUST preserve, not narrow), expanding to a further radio choice of the
  specific material, tool selection (radio — always present here, for both Drilling and Milling,
  with no tree-level shortcut into it for either — see FR-005a),
  and plain fields for diameter, hole depth (Drilling) or the equivalent geometry fields (Milling),
  and available power. Every radio field in this list MUST render as a vertically-stacked,
  arrow-highlighted list — `prompt_toolkit.widgets.RadioList` or an equivalent — not a single-line
  inline `(•) label  ( ) label` layout, matching the pre-plan prototype's own solution exactly
  (resolved via `/speckit-clarify`, reopened after implementation — see Clarifications).
- **FR-005a**: *(Resolution revised via `/speckit-clarify`, reopened after implementation — see
  Clarifications.)* FR-005's "simultaneously visible and editable" guarantee holds trivially now:
  tool selection lives *only* in the left pane, with no tree-level shortcut into it to keep in
  sync or to make "collapse-safe" — there is no longer a tree-collapse interaction for this field
  to reason about at all, since the floating operation window (FR-004) is not part of the tree in
  the first place and stays open independent of the tree's own expand/collapse state regardless.
- **FR-006**: The right pane MUST display the calculation result once every required left-pane
  input holds a valid value, and MUST NOT display a result computed from a different, no-longer-
  current set of inputs.
- **FR-006a**: When every required left-pane input holds *some* value but `calculate()`/
  `calculate_end_milling()`/`calculate_face_milling()` rejects the combination (e.g. an engagement
  value invalid relative to a diameter that was itself just changed), the right pane MUST show the
  resulting clear, actionable, localized error message — not a blank pane or a silently-withheld
  result. This reuses `ErrorInfo`/`forms.format_result()`'s existing error-rendering unchanged (the
  same mechanism PR #94's dialogs already use), per FR-007's "calculate() calls already wired up";
  it does not require new validation logic, only that this feature's right pane actually display
  what that existing mechanism already produces. Mirrors 017's own clear-actionable-message
  guarantee for invalid input (017 Acceptance Scenario 2) for the *out-of-range/unknown-selection*
  portion of that guarantee specifically — `calculate()` and its milling counterparts already
  re-validate every field internally regardless of caller (verified: an out-of-range diameter,
  depth, *or* an unknown material name each independently produce their own `ErrorInfo`, not just
  diameter), so FR-006a's single mechanism covers all of them once the field holds a parseable
  numeric value or a valid selection.
- **FR-006b**: A numeric left-pane field containing text that cannot be parsed as a number at all
  (017 Acceptance Scenario 2's "wrong type" case) MUST NOT be passed to `calculate()`/
  `calculate_end_milling()`/`calculate_face_milling()` — those functions expect an already-parsed
  float and cannot themselves reject unparseable text the way they reject an out-of-range value.
  The field MUST remain immediately editable to correct it, and the application MUST show a clear,
  actionable, localized indication that the value is invalid, distinct from FR-006a's
  calculate()-rejected-combination message. This is the one part of 017's Acceptance Scenario 2
  guarantee FR-006a's reuse-`calculate()`'s-own-errors mechanism cannot cover, since it never
  reaches `calculate()` in the first place.
- **FR-007**: The right pane MUST refresh automatically when a left-pane input changes, without a
  separate manual "calculate" action, mirroring the same `calculate()`/`calculate_end_milling()`/
  `calculate_face_milling()` calls PR #94 already wires up.
- **FR-008**: After a result is shown, the user MUST be able to either change inputs and see an
  updated result, or return to the top-level menu bar/tree, without exiting and relaunching the
  application (parity with PR #94's Acceptance Scenario 3).
- **FR-009**: Milling MUST follow the identical left-pane/right-pane interaction pattern as
  Drilling, differing only in which fields the left pane presents.
- **FR-009a**: Selecting Milling MUST still require the user to choose between End Milling and
  Face Milling (`MillingSubOperation`) before or within the Milling screen — PR #94's existing
  distinction, not something this redesign may drop. Both calculation paths
  (`calculate_end_milling()`/`calculate_face_milling()`) MUST remain reachable; an implementation
  that omits this choice makes one of the two unreachable. Per FR-009's identical-pattern
  requirement, its placement follows FR-005/FR-005a's resolution for Drilling's equivalent choice
  (resolved via `/speckit-clarify`, revised after implementation — see Clarifications): the left
  pane always retains full control, with no Machining-tree-level shortcut for either operation —
  Drilling and Milling are now symmetric in this respect (FR-002, FR-003 retired).
- **FR-010**: The application MUST remain fully operable via keyboard alone; no action may require
  mouse/pointer interaction (unchanged from 017).
- **FR-011**: The application MUST reuse the existing i18n message catalog mechanism
  (`mfgparams.console.i18n`) for every user-visible string introduced by this feature, adding new
  keys under the existing `tui.*` namespace rather than hardcoding text.
- **FR-012**: The application MUST reuse `DrillingSessionState`/`MillingSessionState`'s existing
  field semantics and default-carryover-across-visits behavior (including PR #94's mode-switch and
  unit-system-switch fixes) rather than reintroducing equivalent state from scratch.
- **FR-013**: The application MUST preserve PR #94's entry-point gating *mechanism* unchanged:
  no-TTY detection, terminal-too-small detection, and the missing-`console`-extra message all
  continue to run before any prompt-toolkit object is constructed. This is about the gating
  sequence, not the specific 25×80 threshold `terminal_capability.py` currently checks against —
  that threshold MUST instead be validated against this feature's actual complete layout (menu bar
  + tree + operation screen together) and raised if it doesn't fit, per the revised Assumption
  below. Preserving the number unchanged despite a layout that may no longer fit it would admit
  terminals too small to show every simultaneous input FR-005 requires.
- **FR-013a**: The application MUST adapt to a terminal resize occurring mid-session without
  discarding already-entered, not-yet-submitted left-pane input — carrying forward 017's FR-008
  resize guarantee, which FR-013 above does not otherwise restate. This needs an explicit
  requirement again, not an assumed carryover: 017's dialog-chain screens got this for free from
  prompt-toolkit's own per-`Application` redraw-on-resize behavior (each screen a short-lived,
  independently-constructed `Application`, so there was never a *cross-screen* state-loss risk to
  guard against — see `tui/app.py`'s note on FR-008). This feature's persistent, long-lived
  menu-bar/tree/pane `Application` is a materially different shape that has not itself been
  verified to preserve in-progress input across a resize.
- **FR-014**: The Configuration screen MUST be view-only — a read-only display of the existing
  materials/tools registries, not new create/edit capability (resolved via `/speckit-clarify`,
  see Clarifications; carried forward from 017's default "feature parity, not feature growth"
  assumption, no longer an open question after a third carryover).
- **FR-015**: The Configuration screen MUST cover all three tool registries (drilling, end-mill,
  face-mill), not only drilling's — closing the gap Copilot's review of PR #94 found and deferred.
  This is unconditional following FR-014's view-only resolution: a view-only screen that still
  exposes only drilling's registry leaves the same gap PR #94 shipped.
- **FR-016**: A plain numeric left-pane field (diameter, hole depth, available power, target RPM in
  Fixed RPM mode, and Milling's additional geometry fields) MUST become editable the moment it is
  selected/highlighted — typing a digit immediately edits it. No separate "start editing" action
  (e.g. pressing Enter first) may be required. Confirmed practical in a throwaway prototype built
  against this spec (see Recommended Next Steps): navigating onto a numeric field and typing
  directly, with the value committed automatically on navigating away, reads naturally and needs
  no explicit "confirm" step either.
- **FR-017**: A selected plain numeric field MUST support adjusting its value by a small fixed step
  via a direct keyboard action, in addition to typing a value outright — validated in the same
  prototype using Left/Right to nudge by 1 unit. The exact step size and any per-field bounds are an
  implementation/plan-level decision, not fixed by this FR.
- **FR-018**: The right pane's result text MUST wrap to fit the pane's width rather than being
  truncated or overflowing it — `format_result`'s existing per-line output (label, value, unit) is
  routinely wider than a narrow result pane, confirmed in the same prototype.
- **FR-019**: The application MUST continue to operate within the legacy-hardware resource profile
  Constitution Principle V defines (~64-128 MB RAM, single-threaded CPU, minimal clock speeds) —
  carrying forward 017's FR-004 unchanged. This feature's reactive right-pane redraw (FR-007) is
  the primary new resource-consumption risk relative to 017's one-shot dialogs (which computed and
  displayed a result exactly once per screen, not on every keystroke) and MUST be evaluated against
  this profile specifically, not assumed compatible merely because the underlying
  `calculate()`/registry calls are themselves unchanged.

### Key Entities

- **Top-level menu bar**: The five always-visible entry points (Exit, Machining, Configuration,
  About, Help) — the FR-001 replacement for 017's full-screen top-level menu.
- **Machining tree**: The collapsible navigation structure nested under the Machining menu-bar
  item, with Milling and Drilling as its only (flat, leaf) children — no further sub-expansion
  under either, since Drilling's tool-selection sub-expansion was retired via `/speckit-clarify`
  (reopened after implementation; see Clarifications).
- **Operation floating window**: The bordered panel (FR-004, revised via `/speckit-clarify`) that
  opens over the persistent menu bar/tree when a leaf operation is selected, containing that
  operation's left and right panes.
- **Operation input pane (left pane)**: The set of simultaneously-editable inputs for one
  operation (Drilling or Milling), backed by the existing `DrillingSessionState`/
  `MillingSessionState` entities from PR #94 — this feature changes how those fields are
  presented, not what they are.
- **Operation result pane (right pane)**: The live, auto-refreshing display of the current
  operation's calculation result (or its absence, while inputs are incomplete/invalid).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach a completed Drilling or Milling calculation result while every
  input for that calculation remains visible on screen at the same time, with zero full-screen
  transitions between entering the first and last input (down from 017's 8 sequential dialogs for
  Drilling in standard/power-constrained mode, or 9 in fixed-RPM mode).
- **SC-002**: A user can change any single already-entered input and see an updated result without
  re-entering any other input that did not need to change.
- **SC-003**: A user can run a second calculation (same or different operation) after seeing a
  result without the application exiting or restarting.
- **SC-004**: For identical inputs, the redesigned UI produces calculation results identical to
  PR #94's shipped wizard (no regression in the underlying calculation, only in how inputs are
  collected and results displayed).
- **SC-005**: A first-time, non-technical user can complete one calculation and start a second one
  using only the on-screen menu bar/tree/pane affordances, without external instructions beyond
  what the screen itself shows (carries forward 017's own novice-usability framing).
- **SC-006**: FR-007's automatic right-pane recalculation remains responsive (perceived
  input-to-update delay under approximately 200 ms) when exercised on hardware meeting Constitution
  Principle V's legacy-hardware profile — carrying forward 017's SC-002, scoped to this feature's
  own new reactive-redraw risk surface. Per the Carried-Over Items table below,
  `test_tui_redraw_latency.py` has never actually measured a real reactive redraw until this
  feature's right pane exists to give it one.

## Assumptions

- **Configuration scope, resolved (see Clarifications)**: view-only, a read-only display of the
  existing materials/tools registries, not new create/edit capability — closing out a question
  carried over from 017 that went unconfirmed across `/speckit-plan`, `/speckit-tasks`,
  `/speckit-analyze`, and PR #94's review, and which this spec had deliberately declined to resolve
  by fiat a fourth time (see FR-014).
- **"Drilling further expandable into a choice of drilling type" (feature description), resolved
  in part (see Clarifications): it is today's tool selection, relocated — not a new domain
  concept.** `mfgparams`'s current drilling calculation has no sub-operation split analogous to
  milling's end-mill/face-mill (`MillingSubOperation`) — only a flat drilling-tool registry
  (`list_tools`/`get_tool`), and no new one is being added: reading (a) is confirmed over reading
  (b), so no `processes.machining.drilling` backend changes are needed for this choice to exist.
  **This resolution also covers where Milling's own End-Milling/Face-Milling choice (FR-009a)
  is conceptually rooted** — it is Milling's existing, already-real `MillingSubOperation`, not a
  new concept either — since FR-009 requires Milling to follow Drilling's pattern exactly.
  **Placement, resolved (see Clarifications, revised after implementation)**: the left pane only —
  the Machining tree offers no navigation shortcut into it; FR-003 (which described that shortcut)
  is retired, and Drilling is now a flat tree leaf like Milling (FR-002, FR-005a).
- **Whether collapsing the Machining tree while a leaf operation's screen is open closes that
  screen, resolved (see Clarifications): it does not close.** This was flagged as a third open
  question alongside Configuration scope and drilling-type/sub-operation placement, with no
  existing precedent to lean on — 017/PR #94's `NavigationState` (`tui/app.py`) tracks a single
  `current_screen` with no notion of the tree and a leaf screen being simultaneously "open" at all,
  a mutually-exclusive-state architecture that neither supported nor ruled out this feature's
  persistent layout answering the question either way. The operation-screen-stays-open default is
  now trivially safe by construction, not just conservative: the floating operation window
  (FR-004, revised via `/speckit-clarify`) is not part of the tree at all, so collapsing the tree
  cannot affect it or any FR-005 input regardless of which screen stays open.
- **The 25×80 minimum terminal size (017's FR-011) likely needs raising, not just carrying
  forward, based on the recommended prototype's measured pane height.** Milling's left pane (13
  fields including the always-present available-power field, 14 with Fixed RPM's extra target-RPM
  field) needed a 16-17 row content area — already including its title line — to show every field
  without scrolling. Adding a merged status row and a horizontal divider below it (~18-19 rows),
  plus the floating frame's own border/shadow (~2-3 more) — roughly 20-22 rows for the operation
  screen *alone*, with no menu bar or expanded Machining tree above it yet (both deliberately out of
  scope for that prototype, per the Recommended Next Steps below). Adding FR-001's persistent menu
  bar (1 row) and an expanded Machining tree (FR-002: Machining + Milling + Drilling, 3 rows,
  flat — no further sub-expansion under either leaf) plausibly pushes the real total past 25 rows.
  This is a reasoned
  estimate from the prototype's own numbers, not a verified measurement of the full screen (menu bar
  + tree + operation screen together) — confirming the actual floor needs a follow-up prototype pass
  that adds those two pieces back in, before this Assumption is treated as settled. Drilling's
  narrower left pane (8 fields including available power, 9 with Fixed RPM's extra field, matching
  SC-001's dialog count above) stayed comfortably within 25 rows on its own.
- No new persistence is introduced: as in 017, all state is held for the lifetime of one session
  only.
- This feature does not change the underlying calculation formulas, validation rules, or supported
  materials/tools — only how inputs are collected and results displayed.

## Carried-Over Items From PR #94, and Recommended Next Steps

PR #94's code review (three rounds, six fixed findings) deliberately deferred several items rather
than fixing them in that PR. Recorded here so they are not silently lost, with a recommendation for
when each should be addressed relative to this feature:

| Deferred item | Recommendation |
|---|---|
| Configuration screen's view-vs-edit scope (open since 017's planning) | **Resolved** via `/speckit-clarify`: view-only (see Clarifications, FR-014). |
| Configuration screen only loads the drilling tool registry, not end-mill/face-mill | Fix **as part of this feature**, per FR-015 — same screen being rebuilt, don't patch it twice. |
| `tests/performance/test_tui_redraw_latency.py` doesn't measure real redraw latency (timer starts before input, stops at dialog exit) | Fix **as part of this feature's implementation**, not before: this design introduces the first *real* reactive redraw (the right pane), which is exactly what that test should measure — the old dialog-chain model never had one for it to observe. |
| `test_tui_drilling.py`/`test_tui_milling.py` lost REPL-era coverage of non-standard calculation modes and face milling (only standard mode is exercised, never compared against the rendered result) | Do **not** invest further in the soon-to-be-deleted dialog-chain tests. Write fresh, comprehensive coverage for the new split-pane screens from the start (all modes × both milling sub-operations, asserting against the actual rendered/displayed result), as part of this feature's own test suite. |
| No developer-facing docs page for the `console/tui/` architecture (017's tasks.md T035 never actually satisfied) | Write it **once this feature's architecture is settled**, during its own implementation phase — documenting the soon-to-be-replaced dialog-chain architecture now would be wasted effort. |
| 017's tasks.md T037 (real-terminal, non-technical-user usability walkthrough) was never performed | Fold into **this feature's own acceptance validation** — walk through the *new* UI on a real terminal once built, not the old one. |
| `terminal_capability.py` doesn't detect an incapable real TTY (e.g. `TERM=dumb`) that is otherwise large enough | Independent of this feature and narrow in blast radius (unusual terminal type) — recommend a **small, separate follow-up fix**, not a blocker for this feature. |

**Done: a throwaway prototype was built and tried in a real terminal before `/speckit-plan`,** per
the recommendation this section originally made (kept below for context). Two disposable scripts
were built — one per operation, since Milling's field count turned out to matter (see the revised
25×80 Assumption above) — each a single Drilling or Milling left/right-pane screen, without the
full menu bar/Machining tree, reusing `calculate()`/`calculate_end_milling()`/
`calculate_face_milling()`, the materials/tools registries, and `forms.format_result()` unchanged so
the numbers on screen were real. Both were discarded after validating the shape; nothing from them
was carried into this repository as shipped code. What the exercise confirmed or changed, now folded
into FR-005/FR-016/FR-017/FR-018 and the terminal-size Assumption above:
- The left/right split, rendered as a centered bordered/shadowed box (matching PR #94's existing
  dialog styling) rather than an edge-to-edge full-bleed split, reads naturally. This finding was
  not carried into FR-004 as first written (an embedded, edge-to-edge split pane shipped instead)
  — reopened via `/speckit-clarify` after implementation and now FR-004's own requirement (see
  Clarifications), matching the prototype exactly per explicit user direction.
- Numeric fields being instantly editable on selection (FR-016) and supporting a quick keyboard
  nudge (FR-017) both felt right in practice, not just on paper.
- The right pane needs to wrap text (FR-018) — `format_result`'s lines are routinely wider than a
  proportionally-sized result pane.
- Milling's larger field count is a real constraint on the 25×80 floor, not a hypothetical one — see
  the revised Assumption above for the specific row math and what's still unverified (the floor with
  the menu bar and tree actually present).

*(Original recommendation, for context.)* The primary open question was UX feel and
`prompt-toolkit`'s ergonomics for a persistent, multi-widget split-pane layout with a collapsible
tree — not technical feasibility (the library itself was already confirmed suitable for this
project's resource profile via 017's own technical spike). Mirroring that same
spike-before-committing precedent, the plan was to build a small, disposable script implementing
just one screen's worth of this design and try it in a real terminal before writing
`plan.md`/`tasks.md` — which is what happened, per above.
