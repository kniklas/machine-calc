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

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate by menu bar and tree instead of a dialog chain (Priority: P1)

A user launches the console text GUI and sees a persistent horizontal menu bar (Exit, Machining,
Configuration, Help) instead of a full-screen list of choices. Selecting Machining expands a tree
showing Milling and Drilling; selecting Drilling expands further into a choice of drilling type.
Selecting a leaf operation opens that operation's split-pane screen (User Story 2) without a
separate full-screen transition for the menu bar or tree itself.

**Why this priority**: This is the foundational navigation shell every other user story depends on
— without it, there is nothing to select an operation from.

**Independent Test**: Can be fully tested by launching the app, expanding Machining, expanding
Drilling, and confirming the tree renders and collapses correctly and a leaf selection opens the
corresponding operation screen — independent of what that screen's panes contain.

**Acceptance Scenarios**:

1. **Given** the app has just launched, **When** the user looks at the screen, **Then** a
   horizontal menu bar reading Exit, Machining, Configuration, Help is visible and none of the
   other menu items require navigating away from it to see.
2. **Given** the menu bar is visible, **When** the user selects Machining, **Then** a tree expands
   in place showing Milling and Drilling, without replacing the whole screen.
3. **Given** the Machining tree is expanded, **When** the user selects Drilling, **Then** it
   further expands to show a choice of drilling type, collapsible back to just Milling/Drilling.
4. **Given** a tree is expanded, **When** the user collapses it (e.g. re-selecting Machining or
   pressing a dedicated collapse action), **Then** it returns to its collapsed state without
   losing the user's place in the menu bar.

---

### User Story 2 - Enter every input for an operation in one pane (Priority: P1)

Having selected an operation (e.g. Drilling), the user sees a left pane containing every input for
that calculation at once: unit system (radio, default metric), calculation mode (radio, default
standard), material type (Metal/Wood radio, expanding to a further radio choice of the specific
metal or wood), tool selection (radio), and plain editable fields for diameter, hole depth, and
available power. The user can move between and edit any of these without a screen transition.

**Why this priority**: This is the core usability improvement this feature exists to deliver —
without it, the redesign offers no benefit over 017's dialog chain.

**Independent Test**: Can be fully tested by opening the Drilling screen, changing each left-pane
input in any order (not just top-to-bottom), and confirming every change is reflected without
leaving the pane.

**Acceptance Scenarios**:

1. **Given** the Drilling screen is open, **When** the user views the left pane, **Then** unit
   system, calculation mode, material type, tool selection, diameter, hole depth, and available
   power are all visible and editable without a screen transition.
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
   right pane's result updates to match, or clears until the inputs are complete again.
4. **Given** a result is showing, **When** the user chooses to run another calculation, **Then**
   they can do so from the same screen without restarting the application (mirroring PR #94's own
   Acceptance Scenario 3 parity guarantee).
5. **Given** a result is showing, **When** the user chooses to return to the main menu, **Then**
   they land back at the menu bar/tree from User Story 1, with the tree in a sensible state (not
   necessarily still expanded to the same leaf).

---

### Edge Cases

- What happens when the terminal is too small for the menu bar + two panes, even if it met 017's
  25×80 floor for a single dialog? (See Assumptions — the floor may need revisiting; the
  recommended prototype step should surface whether it does.)
- How does the system handle the user switching from Milling to Drilling (or vice versa) via the
  tree while the left pane has partially-entered, unsaved input for the operation being left? (Per
  017's existing per-operation session-state pattern, each operation's own state should be
  preserved independently — switching away and back should not discard it.)
- How does the system handle a left-pane input that becomes invalid only in combination with
  another (e.g. an engagement value invalid relative to a diameter that was itself just changed) —
  does the right pane clear, show an inline error, or something else?
- What happens if the user collapses the Machining tree while a leaf operation's screen is open —
  does the operation screen close too, or only the tree's own visual state change?
- The application must remain fully operable by keyboard alone, with no mouse/pointer interaction
  required for any action — carried over unchanged from 017's own Assumptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST display a persistent horizontal top-level menu bar containing
  exactly these items: Exit, Machining, Configuration, Help.
- **FR-002**: Selecting Machining MUST expand a collapsible tree showing Milling and Drilling as
  its children, without requiring a separate full-screen transition.
- **FR-003**: Selecting Drilling MUST further expand/collapse to present a choice, within the
  same tree, before or as part of opening the Drilling operation screen (see Assumptions for what
  this choice represents pending confirmation).
- **FR-004**: Selecting a leaf operation (a specific drilling choice, or Milling) MUST open a
  screen with a left pane (inputs) and a right pane (results) for that operation.
- **FR-005**: The left pane MUST present all of the following simultaneously, each editable
  without a screen transition: unit system (radio, default metric), calculation mode (radio,
  default standard), material type (Metal/Wood radio, expanding to a further radio choice of the
  specific material), tool selection (radio), and plain fields for diameter, hole depth (Drilling)
  or the equivalent geometry fields (Milling), and available power.
- **FR-006**: The right pane MUST display the calculation result once every required left-pane
  input holds a valid value, and MUST NOT display a result computed from a different, no-longer-
  current set of inputs.
- **FR-007**: The right pane MUST refresh automatically when a left-pane input changes, without a
  separate manual "calculate" action, mirroring the same `calculate()`/`calculate_end_milling()`/
  `calculate_face_milling()` calls PR #94 already wires up.
- **FR-008**: After a result is shown, the user MUST be able to either change inputs and see an
  updated result, or return to the top-level menu bar/tree, without exiting and relaunching the
  application (parity with PR #94's Acceptance Scenario 3).
- **FR-009**: Milling MUST follow the identical left-pane/right-pane interaction pattern as
  Drilling, differing only in which fields the left pane presents.
- **FR-010**: The application MUST remain fully operable via keyboard alone; no action may require
  mouse/pointer interaction (unchanged from 017).
- **FR-011**: The application MUST reuse the existing i18n message catalog mechanism
  (`mfgparams.console.i18n`) for every user-visible string introduced by this feature, adding new
  keys under the existing `tui.*` namespace rather than hardcoding text.
- **FR-012**: The application MUST reuse `DrillingSessionState`/`MillingSessionState`'s existing
  field semantics and default-carryover-across-visits behavior (including PR #94's mode-switch and
  unit-system-switch fixes) rather than reintroducing equivalent state from scratch.
- **FR-013**: The application MUST preserve PR #94's entry-point gating unchanged: no-TTY
  detection, terminal-too-small detection, and the missing-`console`-extra message all continue to
  run before any prompt-toolkit object is constructed.
- **FR-014**: The Configuration menu item's actual capability (view-only vs. create/edit) MUST be
  resolved as part of this feature rather than carried forward as an open question a third time
  (see Assumptions) — a menu bar entry is being rebuilt regardless, and the two supporting screens
  should not be shipped, then re-opened, twice.
- **FR-015**: If the Configuration screen remains view-only, it MUST cover all three tool
  registries (drilling, end-mill, face-mill), not only drilling's — closing the gap Copilot's
  review of PR #94 found and deferred.

### Key Entities

- **Top-level menu bar**: The four always-visible entry points (Exit, Machining, Configuration,
  Help) — the FR-001 replacement for 017's full-screen top-level menu.
- **Machining tree**: The collapsible Milling/Drilling (and drilling-type) navigation structure
  nested under the Machining menu-bar item.
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
  transitions between entering the first and last input (down from 017's 9+ sequential dialogs for
  Drilling).
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

## Assumptions

- **Configuration scope remains genuinely open** (carried over from 017, still unconfirmed by the
  repo owner across `/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, and PR #94's review):
  whether "Configuration" means a read-only view of the existing materials/tools registries, or new
  create/edit ("setup materials, tools") capability. This spec does not resolve it by fiat a fourth
  time; FR-014 instead makes resolving it explicitly in-scope for this feature's `/speckit-clarify`
  or planning stage, since Configuration's own menu-bar entry and screen are being rebuilt here
  regardless of the answer.
- **"Drilling further expandable into a choice of drilling type" (feature description) may
  overlap with the existing "tool selection" left-pane field, not introduce a new domain concept.**
  `mfgparams`'s current drilling calculation has no sub-operation split analogous to milling's
  end-mill/face-mill (`MillingSubOperation`) — only a flat drilling-tool registry
  (`list_tools`/`get_tool`). Two readings are both plausible from the feature description alone:
  (a) the tree's "drilling type" choice *is* today's tool selection, simply relocated into the tree
  instead of the left pane, or (b) it introduces a genuinely new categorization above tool
  selection (e.g. grouping tools by drilling technique) that does not exist in the domain model
  today and would need new backend support. This spec assumes (a) — no new domain concept, purely
  a UI relocation of the existing tool choice — as the reasonable default consistent with "feature
  parity, not feature growth" (017's own operating assumption), but flags (b) explicitly for
  `/speckit-clarify` to confirm or override before `/speckit-plan`, since it changes whether any
  core/`processes.machining.drilling` code needs to change at all.
- The existing 25×80 minimum terminal size (017's FR-006/FR-008) is assumed as the initial target
  for the new layout; the recommended prototype (see below) should confirm whether a menu bar plus
  two simultaneous panes needs a larger floor, and this spec's requirements should be revisited if
  so.
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
| Configuration screen's view-vs-edit scope (open since 017's planning) | Resolve **during this feature's `/speckit-clarify`/planning**, per FR-014/Assumptions above — it is being rebuilt here regardless. |
| Configuration screen only loads the drilling tool registry, not end-mill/face-mill | Fix **as part of this feature**, per FR-015 — same screen being rebuilt, don't patch it twice. |
| `tests/performance/test_tui_redraw_latency.py` doesn't measure real redraw latency (timer starts before input, stops at dialog exit) | Fix **as part of this feature's implementation**, not before: this design introduces the first *real* reactive redraw (the right pane), which is exactly what that test should measure — the old dialog-chain model never had one for it to observe. |
| `test_tui_drilling.py`/`test_tui_milling.py` lost REPL-era coverage of non-standard calculation modes and face milling (only standard mode is exercised, never compared against the rendered result) | Do **not** invest further in the soon-to-be-deleted dialog-chain tests. Write fresh, comprehensive coverage for the new split-pane screens from the start (all modes × both milling sub-operations, asserting against the actual rendered/displayed result), as part of this feature's own test suite. |
| No developer-facing docs page for the `console/tui/` architecture (017's tasks.md T035 never actually satisfied) | Write it **once this feature's architecture is settled**, during its own implementation phase — documenting the soon-to-be-replaced dialog-chain architecture now would be wasted effort. |
| 017's tasks.md T037 (real-terminal, non-technical-user usability walkthrough) was never performed | Fold into **this feature's own acceptance validation** — walk through the *new* UI on a real terminal once built, not the old one. |
| `terminal_capability.py` doesn't detect an incapable real TTY (e.g. `TERM=dumb`) that is otherwise large enough | Independent of this feature and narrow in blast radius (unusual terminal type) — recommend a **small, separate follow-up fix**, not a blocker for this feature. |

**Recommended next step before `/speckit-plan`: build a throwaway prototype first.** The primary
open question here is UX feel and `prompt-toolkit`'s ergonomics for a persistent, multi-widget
split-pane layout with a collapsible tree — not technical feasibility (the library itself is
already confirmed suitable for this project's resource profile via 017's own technical spike).
Mirroring that same spike-before-committing precedent: build a small, disposable script implementing
just one screen's worth of this design (e.g. Drilling's left/right pane, without the full menu
bar/tree) and try it in a real terminal before writing `plan.md`/`tasks.md`. Discard the prototype
once its shape is validated or revised — it exists to answer "does this feel right and does
`prompt-toolkit` make it reasonably easy to build," not to become shipped code.
