---
description: "Task list for feature implementation"
---

# Tasks: Console TUI Split-Pane Redesign

**Input**: Design documents from `/specs/018-tui-splitpane-redesign/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md),
[contracts/console-tui-splitpane-contract.md](contracts/console-tui-splitpane-contract.md),
[quickstart.md](quickstart.md)

**Tests**: Included and REQUIRED throughout — Constitution Principle II is NON-NEGOTIABLE, and
this repo's own history (every prior `specs/*/tasks.md`, including 017's immediate predecessor)
follows the same convention.

**Organization**: Tasks are grouped by user story (spec.md's US1/US2/US3) to enable independent
implementation and testing of each story. Every path below is exact, taken from plan.md's Project
Structure.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project — `src/mfgparams/`, `tests/` at repository root (plan.md's Project Structure).

---

## Phase 1: Setup

**Purpose**: The two prerequisites every later phase's tests depend on, before any behavior
changes. Unlike 017, no new dependency or package skeleton is needed here — `console/tui/` already
exists.

- [X] T001 [P] Raise `MIN_LINES` from `25` to `30` in
      `src/mfgparams/console/tui/terminal_capability.py`; keep `MIN_COLUMNS` at `80` unchanged
      (research.md #1 — the complete layout no longer reliably fits the old floor)
- [X] T002 [P] Adapt `tests/integration/_tui_test_support.py`'s headless-driving helper for a
      single persistent `Application` (research.md #2): keep the existing thread +
      `contextvars.copy_context()` propagation technique, but change the call shape to drive one
      `app.py` entry point for the whole session and add a way to capture the currently-rendered
      left/right pane text (a capturing `Output` wrapping/subclassing `DummyOutput`, or reading a
      control's own text via the `Layout`) so assertions can check *rendered* content, not an
      intermediate dialog return value — every later integration test in this file depends on this

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data model and catalog entries every user story's screens depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Define `MenuBar`, `MachiningTree`, `FieldId` (per-operation enum/literal),
      `OperationScreen`, and `SessionUI` (replacing `NavigationState`) in
      `src/mfgparams/console/tui/app.py`, per data-model.md — pure dataclasses/enums at this point,
      no rendering logic yet; `MenuBar` reuses 017's existing `MenuEntry` shape from `menu.py`
      rather than inventing a new entry type
- [X] T004 [P] Add the new `tui.*` keys this feature needs to
      `src/mfgparams/console/locales/en.py`: a `tui.menu.exit` label (Exit is new to the bar,
      FR-001) and a tree drilling-type/tool-selection leaf label. Reuse existing keys rather than
      duplicating: the right pane's title is already `tui.result.title` ("Result"); FR-006b's
      invalid-number message reuses the existing `tui.prompt.number.invalid`
      ("Please enter a numeric value.") rather than a new key — confirm this reuse still reads
      correctly in the new inline-field context, not just the old dialog context, before assuming
      it needs no wording change
- [X] T005 [P] Unit test: `SessionUI`'s `tree`/`open_operation` independence — collapsing/expanding
      `tree` never changes `open_operation`, and vice versa (FR-005a's invariant as a data-model
      constraint) — in `tests/unit/console/tui/test_session_ui.py`
- [X] T006 [P] Unit test: `MachiningTree`'s expand/collapse state transitions, including the
      `drilling_expanded` MUST-be-`False`-when-`expanded`-is-`False` validation rule, in
      `tests/unit/console/tui/test_machining_tree.py`
- [X] T007 [P] Update the existing terminal-size unit test for the new 30-row floor (mock terminal
      sizes above/below 30×80, not 25×80) in `tests/unit/console/tui/test_terminal_capability.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Navigate by menu bar and tree instead of a dialog chain (Priority: P1) 🎯 MVP (part 1 of 2)

**Goal**: The persistent menu bar and collapsible Machining tree replace `menu.py`'s full-screen
menu and `machining_menu.py`'s full-screen submenu (FR-001, FR-002, FR-003, FR-010).

**Independent Test**: Per spec.md — launch the app, expand Machining, expand Drilling, confirm the
tree renders/collapses correctly (Acceptance Scenarios 1-4) and a leaf selection opens the
corresponding operation screen — independent of what that screen's panes contain (quickstart.md
Scenario 1).

### Tests for User Story 1 ⚠️ (write first, confirm they fail before implementing)

- [X] T008 [P] [US1] Contract test: rewrite `tests/contract/test_console_tui_contract.py` in place
      against `contracts/console-tui-splitpane-contract.md` §2 — exact menu-bar entry set (5
      items), exact tree structure (Machining → Milling/Drilling, Drilling →
      tool-selection shortcut), and pairwise-unique mnemonics within the bar and within the tree
      (research.md's decision to rewrite in place, not add a second contract test file)
- [X] T009 [P] [US1] Integration test: headless navigation shell — launch, expand Machining
      (Acceptance Scenario 2), expand Drilling's shortcut (Acceptance Scenario 3), collapse back
      (Acceptance Scenario 4), select a leaf and confirm the corresponding operation screen opens
      — in `tests/integration/test_tui_navigation.py` (new file; 017's `test_tui_app_run.py` tested
      `NavigationState` push/pop directly, which no longer exists in that shape)

### Implementation for User Story 1

- [X] T010 [US1] Rewrite `src/mfgparams/console/tui/menu.py` as the persistent horizontal
      menu-bar widget rendering `MenuBar`'s 5 entries (T003, T004), reusing `_assign_mnemonics`
      unchanged (research.md — not full-screen-dialog-specific)
- [X] T011 [US1] Replace `src/mfgparams/console/tui/machining_menu.py` with the collapsible
      `MachiningTree` widget (Milling/Drilling children, Drilling's tool-selection-shortcut leaf),
      rendering `SessionUI.tree`'s state (T003) (depends on T010)
- [X] T012 [US1] Rewrite `src/mfgparams/console/tui/app.py`'s `Application`/`Layout`/key-binding
      wiring around `SessionUI` (T003): one persistent `Application` constructed once per session
      (not a while-loop dispatching between short-lived per-screen `Application`s), with the Exit
      bar entry as the app's own exit action (FR-001's "no root screen to Escape from" — an
      explicit action now, not a bare Escape/Ctrl-Q handler) (depends on T003, T010, T011)
- [X] T013 [US1] Wire `about.py`/`help.py` (content unchanged) into the new menu bar's About/Help
      entries (FR-001's "only its menu-bar placement changes") (depends on T012)

**Checkpoint**: Navigation shell fully functional and independently testable — quickstart.md
Scenario 1.

---

## Phase 4: User Story 2 - Enter every input for an operation in one pane (Priority: P1) 🎯 MVP (part 2 of 2)

**Goal**: The left/right split-pane screen replaces the sequential dialog chain for both Drilling
and Milling, with every FR-005 field simultaneously visible/editable, instant-edit numeric fields
(FR-016), keyboard nudge (FR-017), and tool-selection placement resolved per FR-005a.

**Independent Test**: Per spec.md — open the Drilling screen, change each left-pane input in any
order, confirm every change is reflected without leaving the pane (quickstart.md Scenarios 2, 5,
6).

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Integration test: rewrite `tests/integration/test_tui_drilling.py` — every
      FR-005 field visible/editable without a screen transition (Acceptance Scenario 1),
      unit-system carryover (Acceptance Scenario 3, PR #94's fix), all three modes, asserting
      against the actual rendered/displayed result (spec's Carried-Over Items table — not just
      porting the old dialog-chain assertions)
- [X] T015 [P] [US2] Integration test: rewrite `tests/integration/test_tui_milling.py` — same
      pattern (Acceptance Scenario 4), both End-Milling/Face-Milling sub-operations × all three
      modes, sub-operation choice (FR-009a) reachable
- [X] T016 [P] [US2] Integration test: numeric-field instant-edit (typing a digit immediately
      edits, no separate start-editing action) and Left/Right nudge, in
      `tests/integration/test_tui_field_editing.py` (new file, FR-016/FR-017)
- [X] T017 [P] [US2] Integration test: extend `tests/integration/test_tui_validation.py` for
      FR-006b — text that can't parse as a number stays editable with a clear message, never
      reaches `calculate()` (Acceptance Scenario 5 of User Story 2)
- [X] T018 [P] [US2] Integration test: extend `tests/integration/test_tui_navigation.py` (T009) —
      collapsing the Machining tree while Drilling's screen is open does not hide tool selection
      (FR-005a; quickstart.md Scenario 5 — the specific regression this feature's
      `/speckit-clarify` session exists to guard against)
- [X] T019 [P] [US2] Integration test: data-driven material-type category set — with a
      `--materials-config` fixture registering a category beyond Metal/Wood, confirm the left
      pane's material-type radio includes it (spec User Story 2, quickstart.md Scenario 6),
      extending the existing materials-config test fixture pattern

### Implementation for User Story 2

- [X] T020 [US2] Prune `src/mfgparams/console/tui/forms.py`: remove the dialog-shortcut widgets
      this feature replaces (`ask_choice`, `ask_number`, `ask_required_number`,
      `ask_optional_number`, `ask_unit_system`, `ask_mode`, `ask_material_type`, `ask_material`,
      `ask_tool`, `ask_drilling_tool`, `show_result`, and the now-unneeded `Cancelled`/`CANCELLED`
      sentinel — fields commit-on-navigate now, not via an explicit per-dialog Back/Cancel button).
      Keep unchanged: `UNIT_LABELS`, `convert_length`, `convert_power`, `render_error`,
      `display_label`, `material_type_label`, `unique_labels`, `format_result` (research.md's
      consolidated table; confirmed reusable in the pre-plan prototype)
- [X] T021 [US2] Implement the shared left/right split-pane component both Drilling and Milling
      reuse (FR-009's identical-pattern requirement) — instant-edit numeric fields (FR-016),
      Left/Right nudge with a floor at zero (FR-017), radio-field cycling, right-pane text wrap
      (FR-018) — in a new `src/mfgparams/console/tui/screens/split_pane.py` (depends on T003, T020)
- [X] T022 [US2] Rewrite `src/mfgparams/console/tui/screens/drilling.py`: keep
      `DrillingSessionState`'s fields/semantics/default-carryover unchanged (FR-012); replace
      `run_drilling_screen`'s sequential-dialog orchestration with T021's shared component; tool
      selection always present in the left pane (FR-005), with the Machining tree's shortcut (T011)
      navigating into the same field, never a separate/duplicate value (FR-005a) (depends on T021)
- [X] T023 [US2] Rewrite `src/mfgparams/console/tui/screens/milling.py`: same shape for
      `MillingSessionState`, calling `calculate_end_milling()`/`calculate_face_milling()`
      unchanged; the End-Milling/Face-Milling choice (FR-009a) is a left-pane field following
      Drilling's placement resolution (depends on T021)
- [X] T024 [US2] Extend `src/mfgparams/console/tui/screens/configuration.py`: still view-only
      (FR-014, resolved via `/speckit-clarify`), now covers all three tool registries — add
      end-mill and face-mill sections alongside the existing drilling-only
      `tui.configuration.section.tools` (FR-015, closing the gap PR #94's review found and
      deferred; new `tui.configuration.section.end_mill_tools`/`.face_mill_tools` keys in
      `locales/en.py`) (depends on T003)

**Checkpoint**: User Stories 1 AND 2 together deliver a fully usable single-operation flow — this
is the feature's MVP (mirroring 017's own "no smaller shippable increment" reasoning: a menu/tree
with nothing to select, or an input pane with no way to reach it, is not independently useful).

---

## Phase 5: User Story 3 - See results in a persistent pane and repeat or exit (Priority: P2)

**Goal**: The right pane's three states (placeholder/result/error — FR-006/FR-006a) and automatic
refresh (FR-007) are correct, and the user can repeat a calculation or return to the menu without
restarting (FR-008).

**Independent Test**: Per spec.md — complete all left-pane inputs, confirm the right pane shows a
result, change one input and confirm it refreshes, then return to the main menu and confirm the
app is back at the navigation shell, not restarted.

### Tests for User Story 3 ⚠️

- [X] T025 [P] [US3] Integration test: the right pane's three states — placeholder while incomplete
      (Acceptance Scenario 1), a result once complete/valid with no separate confirmation
      (Acceptance Scenario 2), and the resulting error when `calculate()` rejects a
      complete-but-invalid combination (Acceptance Scenario 3, FR-006a) — plus automatic refresh on
      any input change (FR-007), in `tests/integration/test_tui_results.py` (new file, exercising
      both Drilling and Milling against the shared T021 component)
- [X] T026 [P] [US3] Integration test: for identical inputs, the TUI's displayed result is
      byte-identical to calling `calculate()`/`calculate_end_milling()`/`calculate_face_milling()`
      directly (SC-004), in `tests/integration/test_tui_calculation_parity.py` (new file)

### Implementation for User Story 3

- [X] T027 [US3] Complete T021's right-pane state machine: exactly the three states contract §3
      names, never a fourth, with `last_result` invalidated/recomputed whenever the cached input
      tuple no longer matches current session-state values (data-model.md's `OperationScreen`
      validation rule) (depends on T021, T022, T023)
- [X] T028 [US3] Implement "return to the main menu" and "repeat calculation" actions on the
      operation screen (FR-008), wiring `SessionUI.open_operation = None` on return without
      touching `SessionUI.tree`'s own state (Acceptance Scenario 5 — "not necessarily still
      expanded to the same leaf") (depends on T012, T022, T023)

**Checkpoint**: All three user stories independently functional — the complete split-pane redesign
is usable end to end (quickstart.md Scenarios 1-6).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Rewrite `tests/integration/test_tui_resize_preserves_input.py` against the new
      persistent `Application` (FR-013a) — 017's version tested per-screen resize behavior that no
      longer exists in that shape
- [X] T030 [P] Rewrite `tests/performance/test_tui_redraw_latency.py` to measure the real reactive
      redraw this feature introduces (SC-006, Constitution Check row V) — the old version's timer
      started before input and stopped at dialog exit, never observing an actual redraw (Carried-
      Over Items table)
- [X] T031 [P] Re-verify `tests/performance/test_tui_startup_budget.py` against the new persistent
      `Application`'s baseline memory footprint; extend only if research.md's assumption (no
      material difference from the old per-screen baseline) turns out wrong
- [X] T032 [P] Update `tests/integration/test_tui_terminal_too_small.py` for the new 30×80 floor
      (T001)
- [X] T033 [P] Confirm (and update only where they construct the now-replaced `NavigationState`/
      screen-stack directly) `tests/integration/test_tui_no_tty_fallback.py`,
      `tests/integration/test_tui_app_run.py`, `tests/integration/test_tui_static_screens.py`, and
      `tests/integration/test_tui_i18n.py` still pass against the rewritten `app.py` — research.md
      flags this as needing confirmation, not assumed
- [X] T034 [P] Add the `console/tui/` architecture docs page 017's own tasks.md left outstanding
      (Constitution Principle VII, Carried-Over Items table) — write it now that this feature's
      architecture (this plan) is settled
- [X] T035 [P] Update Sphinx end-user docs: replace the old menu/dialog-chain navigation
      instructions with the new persistent menu-bar/tree/split-pane model (Constitution Principle
      VII)
- [X] T036 Bump `src/mfgparams/__init__.py`'s `__version__` from `"2.0.0"` to `"2.1.0"` (MINOR, not
      MAJOR — contract §7; Constitution Principle IV)
- [X] T037 Add a `CHANGELOG.md` `[Unreleased]` entry under `### Changed` describing the navigation
      model change and the raised terminal-size floor (contract §7)
- [ ] T038 Run every scenario in `quickstart.md` manually, end-to-end, on a real terminal — SC-005's
      first-time/non-technical-user walkthrough and 017's own tasks.md T037, both folded into this
      feature's acceptance validation per spec's Carried-Over Items table (do not repeat 017's
      "not done as such" gap if an interactive terminal is available this time)
- [X] T039 Run `/speckit-analyze` to confirm spec.md/plan.md/tasks.md are still mutually consistent
      before implementation sign-off

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's `app.py`/menu-bar/tree wiring existing
  (T021-T024 need somewhere to open into) — not independently buildable before US1's shell exists,
  but independently *testable* once it does, same relationship 017's US2 had to its US1.
- **User Story 3 (Phase 5)**: Depends on Foundational + US2's `drilling.py`/`milling.py`/
  `split_pane.py` existing (T027/T028 complete behavior T021-T023 already scaffold).
- **Polish (Phase 6)**: Depends on US1+US2 (MVP); T038/T039 benefit from US3 also being done.

### Within Each User Story

Tests (T008-T009, T014-T019, T025-T026) MUST be written and confirmed failing before their
corresponding implementation tasks, per Constitution Principle II.

### Parallel Opportunities

- T001, T002 (Setup, marked [P]) run in parallel — different files.
- T003, T004, T005, T006, T007 (Foundational, marked [P]) run in parallel — different files;
  T005-T007 depend on T003's dataclasses existing conceptually but can be written against
  data-model.md directly and only need T003 merged before they can pass.
- T008, T009 (US1 tests) run in parallel.
- T014-T019 (US2 tests, marked [P]) run in parallel — six different files.
- T025, T026 (US3 tests) run in parallel.
- T029-T035 (Polish, marked [P]) run in parallel.
- T010, T011 are NOT marked [P] against each other (T011 depends on T010's bar existing) despite
  touching different files; T022, T023 similarly depend on T021 but are independent of each other
  and MAY be parallelized in practice once T021 lands — left sequential here only because that
  dependency is already unambiguous from the listing.

---

## Parallel Example: User Story 2 tests

```bash
# Launch all six US2 test tasks together (different files, no shared state):
Task: "Integration test: Drilling left-pane fields in tests/integration/test_tui_drilling.py"
Task: "Integration test: Milling left-pane fields in tests/integration/test_tui_milling.py"
Task: "Integration test: instant-edit + nudge in tests/integration/test_tui_field_editing.py"
Task: "Integration test: FR-006b unparseable text in tests/integration/test_tui_validation.py"
Task: "Integration test: tree-collapse safety in tests/integration/test_tui_navigation.py"
Task: "Integration test: data-driven material categories in tests/integration/test_tui_drilling.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything).
3. Complete Phase 3: User Story 1 — navigation shell.
4. Complete Phase 4: User Story 2 — input panes. Unlike 017 (where US1 alone was the MVP, since it
   included the REPL deletion), here US1 alone (a tree with nothing behind its leaves) is not a
   useful increment — the MVP is Phases 1-4 as one unit.
5. **STOP and VALIDATE**: run quickstart.md Scenarios 1, 2, 5, 6 manually; confirm T008-T009 and
   T014-T019 pass.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → validate independently → navigation shell only, not yet demoable end-to-end.
3. User Story 2 → validate independently → MVP complete (a full calculation is now reachable).
4. User Story 3 → validate independently → right-pane correctness and repeat/exit confirmed.
5. Polish → docs, performance budgets, resize/no-TTY/terminal-floor tests, version bump, final
   `/speckit-analyze` pass.

### Note on Constitution Principle XII (Long-Lived Feature Branches)

plan.md deferred the question of whether this feature needs a long-lived integration branch to this
phase, mirroring 017's own precedent for the identical judgment call. Task count: 39, comparable to
017's 38 — and this feature reuses substantially more of the existing architecture (i18n, session
state, `calculate()` wiring, materials/tools registries, entry-point gating are all unchanged;
017 built the entire `tui/` subpackage from nothing plus deleted the REPL). **Recommendation:
single PR against `018-tui-splitpane-redesign`, merged directly to `main`** — the same conclusion
017 reached at comparable size, and this feature has fewer genuinely novel subsystems (one shared
split-pane component reused twice, vs. 017's five independent screen types built from scratch).
Revisit only if implementation reveals the diff is unreviewable in one pass — e.g. if `split_pane.py`
(T021) grows large enough that reviewing it together with both `drilling.py`/`milling.py` rewrites
in one PR becomes impractical.
