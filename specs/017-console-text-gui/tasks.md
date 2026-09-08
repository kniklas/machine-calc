---
description: "Task list for feature implementation"
---

# Tasks: Console Text GUI (TUI)

**Input**: Design documents from `/specs/017-console-text-gui/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/console-tui-contract.md](contracts/console-tui-contract.md),
[quickstart.md](quickstart.md)

**Tests**: Included and REQUIRED throughout — Constitution Principle II is NON-NEGOTIABLE
("Automated tests are mandatory for all calculation logic... MUST be written before or alongside
implementation, never deferred"), and this repo's own history (every prior `specs/*/tasks.md`)
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

**Purpose**: Dependency + package skeleton, before any behavior exists.

- [ ] T001 Add `prompt-toolkit` to the `console` extra in `pyproject.toml` (currently `console = []`
      — see the extra's own comment explaining why it shipped empty since 014)
- [ ] T002 [P] Create the `src/mfgparams/console/tui/` package skeleton: `__init__.py` and
      `screens/__init__.py`, per plan.md's Project Structure — empty modules, no logic yet

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure every user story's screens depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 [P] Define `ScreenId` (enum) and `NavigationState` (dataclass: `current_screen`,
      `screen_stack`, `locale`, `materials_config_path`) in `src/mfgparams/console/tui/app.py`,
      per data-model.md's NavigationState entity
- [ ] T004 [P] Implement `src/mfgparams/console/tui/terminal_capability.py`: a function checking
      `sys.stdin.isatty()`/`sys.stdout.isatty()` and `shutil.get_terminal_size()` against the 25×80
      minimum (FR-006/FR-008/FR-011), returning a typed result — **no prompt-toolkit import in this
      module**, since research.md #2 established the check must run *before* any prompt-toolkit
      object exists
- [ ] T005 [P] Add a `console.tui_unavailable` message key (no-TTY / terminal-too-small,
      parameterized on which condition failed) to the **core** catalog
      `src/mfgparams/locales/en.py`, mirroring `console.missing_dependency`'s existing placement
      there (contracts/console-tui-contract.md §4 — a message saying the console is unavailable
      can't depend on the console's own catalog having initialized)
- [ ] T006 Add the base `tui.*` message keys to `src/mfgparams/console/locales/en.py`: top-level
      menu labels (`tui.menu.machining`, `tui.menu.configuration`, `tui.menu.about`,
      `tui.menu.help`), Machining submenu labels (`tui.machining.milling`,
      `tui.machining.drilling`), and a generic `tui.action.back` label — per contracts §2/§3
- [ ] T007 Generalize `tests/static/test_console_catalogue_ownership.py` (currently scans only
      `console/cli.py`) to scan every `.py` file under `mfgparams/console/` and its subpackages,
      excluding `mfgparams/console/locales/`, for `translate()`/`has_message()` call sites — using
      the same "core vs. console" path-boundary approach `test_core_does_not_import_console.py`
      already uses (research.md #5)
- [ ] T008 [P] Unit test for `ScreenId`/`NavigationState` push/pop/"back" semantics in
      `tests/unit/console/tui/test_navigation_state.py`
- [ ] T009 [P] Unit test for `terminal_capability`'s isatty/size detection (mock `isatty()`
      True/False and terminal sizes above/below 25×80) in
      `tests/unit/console/tui/test_terminal_capability.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Run a calculation from a full-screen text interface (Priority: P1) 🎯 MVP

**Goal**: The text GUI is the sole interactive entry point, with the exact FR-009 menu structure,
full parameter-entry parity with what the REPL exposed (Milling, Drilling), and the REPL is deleted
— not hidden — from the codebase (FR-001, FR-002, FR-007, FR-009, FR-010, FR-011, FR-012, FR-013).

**Independent Test**: Per spec.md — launch the text GUI, complete one full calculation using only
the keyboard, and confirm the result matches calling the underlying core function directly with the
same arguments (the REPL no longer exists to compare against). Also: confirm the exact menu
structure (contracts §2) renders with visible shortcuts, and confirm the REPL is fully gone
(`mfgparams.console.cli` has no `input()`-driven session functions left).

### Tests for User Story 1 ⚠️ (write first, confirm they fail before implementing)

- [ ] T010 [P] [US1] Contract test: exact menu structure + pairwise-unique mnemonics per menu, in
      `tests/contract/test_console_tui_contract.py` (contracts §2/§3, data-model.md's `MenuEntry`
      validation rule)
- [ ] T011 [P] [US1] Integration test: headless end-to-end Milling flow (menu → Machining →
      Milling → sub-operation → parameters → result), using `prompt_toolkit.output.DummyOutput` +
      `prompt_toolkit.input.create_pipe_input` per the spike's own method, in
      `tests/integration/test_tui_milling.py` — asserts the displayed result matches
      `mfgparams.calculate_end_milling`/`calculate_face_milling` called directly with the same
      arguments
- [ ] T012 [P] [US1] Integration test: headless end-to-end Drilling flow, in
      `tests/integration/test_tui_drilling.py` — asserts the displayed result matches
      `mfgparams.calculate` called directly (User Story 1's Independent Test)
- [ ] T013 [P] [US1] Integration test: an invalid parameter (out of range/wrong type/missing)
      produces an in-place, catalog-sourced validation message and the field is correctable without
      restarting, in `tests/integration/test_tui_validation.py` (Acceptance Scenario 2)
- [ ] T014 [P] [US1] Integration test: the REPL is fully gone — `python -m mfgparams` launches the
      text GUI (asserted via the headless probe), and `mfgparams.console.cli` contains no
      `input()`-driven session/prompt functions (an `ast`-based static assertion, mirroring
      `test_cli_contract.py`'s existing style), in `tests/integration/test_console_repl_removed.py`
      (Acceptance Scenario 4, FR-001, FR-007)

### Implementation for User Story 1

- [ ] T015 [US1] Implement `src/mfgparams/console/tui/menu.py`: top-level menu screen rendering the
      4 entries from T006's keys with visible mnemonic hints (depends on T003, T006)
- [ ] T016 [US1] Implement `src/mfgparams/console/tui/machining_menu.py`: Machining submenu
      (Milling, Drilling) (depends on T015)
- [ ] T017 [US1] Implement `src/mfgparams/console/tui/screens/milling.py`: ports the REPL's
      `_prompt_milling_sub_operation`/`_prompt_milling_inputs`/`_prompt_mill_tool_choice`/
      `_prompt_end_mill_tool_choice`/`_prompt_face_mill_tool_choice`/`_prompt_milling_geometry`
      logic (data shaping, not `input()` calls) into `data-model.md`'s `OperationForm`/`FieldSpec`
      shape, calling `mfgparams.calculate_end_milling`/`calculate_face_milling` unchanged
      (research.md #3) (depends on T004, T016)
- [ ] T018 [US1] Implement `src/mfgparams/console/tui/screens/drilling.py`: ports the REPL's
      `_run_drilling_session`'s data-shaping logic (material/tool/diameter/depth/power/mode/target
      RPM) into the same `OperationForm` shape, calling `mfgparams.calculate` unchanged
      (research.md #3) (depends on T004, T016)
- [ ] T019 [US1] Implement `src/mfgparams/console/tui/screens/configuration.py`: read-only
      materials/tools registry view+select (research.md #4, data-model.md's `ConfigurationView`) —
      **not** a create/edit UI (depends on T015)
- [ ] T020 [US1] Implement `src/mfgparams/console/tui/screens/about.py`: program name, version
      (`mfgparams.__version__`), license pointer (depends on T015)
- [ ] T021 [US1] Implement `src/mfgparams/console/tui/screens/help.py`: placeholder content,
      reachable and non-crashing (FR-009) (depends on T015)
- [ ] T022 [US1] Implement `src/mfgparams/console/tui/app.py`'s `Application`/`Layout`/key-binding
      wiring: constructs `NavigationState` (T003), resolves the session locale once via
      `mfgparams.console.i18n.get_locale()`, and assembles menu.py + machining_menu.py +
      screens/* into one navigable app (depends on T015, T016, T017, T018, T019, T020, T021)
- [ ] T023 [US1] Rewrite `src/mfgparams/console/cli.py`: delete every REPL-only function
      (`_prompt_*` functions that call `input()` directly, `_run_drilling_session`,
      `_run_end_milling_session`, `_run_face_milling_session`, `_run_milling_session`, the REPL's
      `run()` loop, the REPL's `_parse_args`); keep `main()` as a thin dispatcher that runs
      `terminal_capability`'s check (T004) and then launches `tui/app.py` (T022); update
      `tests/contract/test_cli_contract.py`'s target/assertion to match wherever `calculate()` is
      now actually invoked from (`screens/drilling.py`/`milling.py`), since it currently asserts
      against `cli.py` directly (depends on T004, T022)
- [ ] T024 [US1] Bump `src/mfgparams/__init__.py`'s `__version__` from `"1.0.0"` to `"2.0.0"`
      (Constitution Principle IV, FR-013 — single source of truth, no other file hardcodes it)
- [ ] T025 [US1] Add a `CHANGELOG.md` `[Unreleased]` entry (grouped with or after the existing
      process-first-rename entry) documenting that the REPL entry point is removed and the text GUI
      is now the sole interactive entry point (FR-013, contracts §6)
- [ ] T026 [US1] Delete the REPL-only integration tests that exercise the now-removed `run()` loop
      via simulated stdin: `tests/integration/test_cli_edge_cases.py`,
      `test_cli_end_milling.py`, `test_cli_face_milling.py`, `test_cli_fixed_rpm.py`,
      `test_cli_flow.py`, `test_cli_loop.py`, `test_cli_material_types.py`,
      `test_cli_materials_config.py`, `test_cli_milling_fixed_rpm.py`,
      `test_cli_milling_mode_prompt_ux.py`, `test_cli_milling_power_constrained.py`,
      `test_cli_mode_prompt_ux.py`, `test_cli_operation_reselection.py`,
      `test_cli_operation_selection.py`, `test_cli_power_constrained.py`,
      `test_cli_prompt_budget.py`, `test_cli_validation.py` — verify during implementation that
      each is genuinely REPL-loop-specific (not testing REPL-independent logic that survived the
      T017/T018 port) before deleting; anything found to test surviving logic gets folded into
      T011-T013 instead of dropped (SC-004). **Leave `tests/contract/test_library_cli_extensions.py`
      unchanged** — it tests core library function signatures, not the REPL.
- [ ] T027 [US1] Re-verify `tests/integration/test_console_missing_dependency.py` still passes
      unmodified: its guard (`mfgparams/__main__.py`) is generic over whatever the `console` extra
      declares, so T001's new `prompt-toolkit` dependency should require no test change — confirm
      rather than assume

**Checkpoint**: User Story 1 fully functional and independently testable (quickstart.md Scenarios
1, 2, 6). This is the feature's MVP — it cannot ship partially (REPL deletion is part of US1
itself), so "MVP" here means Phases 1-3 complete as one unit.

---

## Phase 4: User Story 2 - Use the text GUI in the configured language (Priority: P2)

**Goal**: Every string the text GUI displays is sourced from the catalog, with correct
locale-switch and fallback behavior (FR-003, SC-003).

**Independent Test**: Per spec.md — switch to a supported non-English locale, launch the text GUI,
confirm every visible string (including a deliberately-triggered validation error) renders in that
locale or falls back to English.

### Tests for User Story 2 ⚠️

- [ ] T028 [P] [US2] Integration test: with a fixture/test locale registered (mirroring this
      repo's existing i18n test fixture pattern — `mfgparams.console.i18n`'s catalog cache supports
      registering one deterministically), confirm the top-level menu and a deliberately-triggered
      validation error both render in that locale, in `tests/integration/test_tui_i18n.py`
      (quickstart.md Scenario 3)
- [ ] T029 [P] [US2] Unit test: a `tui.*` key missing from a non-English catalog falls back to the
      English catalog entry rather than showing blank/broken text, in
      `tests/unit/console/tui/test_i18n_fallback.py`

### Implementation for User Story 2

- [ ] T030 [US2] Audit every string emitted anywhere under `src/mfgparams/console/tui/` (menu.py,
      machining_menu.py, screens/*.py, app.py) resolves via `mfgparams.console.i18n.translate` —
      zero hardcoded strings in the UI layer (SC-003); fix any violation T007's generalized
      contract test surfaces

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Fail clearly, not crash, on unsupported terminals (Priority: P3)

**Goal**: No TTY, or a terminal below 25×80, produces a clear catalog-sourced exit message —
never a traceback, never a silent hang, never prompt-toolkit's own unlocalized warning (FR-006,
FR-008, FR-011).

**Independent Test**: Per spec.md — invoke the console with stdin/stdout piped (no TTY) and confirm
a prompt, actionable, non-crashing exit.

### Tests for User Story 3 ⚠️

- [ ] T031 [P] [US3] Integration test: piped/no-TTY invocation exits promptly with the T005 message,
      never a traceback, never prompt-toolkit's own "Input is not a terminal" warning, never a
      hang, in `tests/integration/test_tui_no_tty_fallback.py` (quickstart.md Scenario 4)
- [ ] T032 [P] [US3] Integration test: a terminal reporting a size below 25×80 exits with the same
      clear message, in `tests/integration/test_tui_terminal_too_small.py` (quickstart.md
      Scenario 5)

### Implementation for User Story 3

- [ ] T033 [US3] Wire `terminal_capability`'s check (T004) into `console/cli.py`'s `main()`
      (T023) so it runs — and can exit via T005's message — strictly before `tui/app.py` (T022)
      constructs any prompt-toolkit object (research.md #2); this task is mostly verification if
      T023 already called it correctly, but owns the negative-path wiring specifically

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T034 [P] Update Sphinx end-user docs: replace REPL usage instructions with text-GUI usage
      (menu navigation, shortcuts) (Constitution Principle VII)
- [ ] T035 [P] Update Sphinx developer docs: document the new `console/tui/` architecture and its
      relationship to `console/cli.py` (Constitution Principle VII)
- [ ] T036 [P] Add `tests/performance/test_tui_startup_budget.py`, reusing
      `tests/performance/harness.py`'s isolated-child-process RSS measurement, budgeted against
      Constitution Principle V's ~64-128 MB target for the *shipped* app (not just the framework
      import the spike measured) — opt-in via `MFGPARAMS_RUN_PERFORMANCE_TESTS=1` per the existing
      convention
- [ ] T037 Run every scenario in `quickstart.md` manually, end-to-end, on a real terminal
- [ ] T038 Run `/speckit-analyze` to confirm spec.md/plan.md/tasks.md are still consistent before
      implementation sign-off

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational + US1's screens existing (T030 audits code
  T015-T022 produce) — not independently buildable before US1's UI exists, but independently
  *testable* once it does.
- **User Story 3 (Phase 5)**: Depends on Foundational + T023's `cli.py main()` existing (T033 wires
  into it) — same relationship as US2.
- **Polish (Phase 6)**: Depends on US1 (MVP); T034/T035/T037 benefit from US2/US3 also being done.

### Within Each User Story

Tests (T010-T014, T028-T029, T031-T032) MUST be written and confirmed failing before their
corresponding implementation tasks, per Constitution Principle II.

### Parallel Opportunities

- T002 (package skeleton) has no dependents blocking it once T001 lands.
- T003, T004, T005, T008, T009 (Foundational, marked [P]) run in parallel — different files.
- T010-T014 (US1 tests, marked [P]) run in parallel — different files, no shared state.
- T017, T018, T019, T020, T021 are NOT marked [P] against each other despite being different
  files: all five depend on T016 (or T015) but are otherwise independent of each other and MAY be
  parallelized in practice — left unmarked here only because T022 depends on all five completing,
  which the sequential listing already communicates unambiguously.
- T028, T029 (US2 tests) and T031, T032 (US3 tests) each run in parallel within their story.
- T034, T035, T036 (Polish, marked [P]) run in parallel.

---

## Parallel Example: User Story 1 tests

```bash
# Launch all five US1 test tasks together (different files, no shared state):
Task: "Contract test: menu structure + mnemonics in tests/contract/test_console_tui_contract.py"
Task: "Integration test: headless Milling flow in tests/integration/test_tui_milling.py"
Task: "Integration test: headless Drilling flow in tests/integration/test_tui_drilling.py"
Task: "Integration test: in-place validation message in tests/integration/test_tui_validation.py"
Task: "Integration test: REPL fully removed in tests/integration/test_console_repl_removed.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (blocks everything).
3. Complete Phase 3: User Story 1 — this phase already includes REPL deletion, the version bump,
   and the changelog entry, since spec.md ties all three to US1 directly. There is no smaller
   shippable increment than "all of Phase 3."
4. **STOP and VALIDATE**: run quickstart.md Scenarios 1, 2, 6 manually; confirm T010-T014 pass.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → validate independently → this is the MVP (the REPL-to-TUI swap, complete).
3. User Story 2 → validate independently → i18n parity confirmed on top of US1's screens.
4. User Story 3 → validate independently → unsupported-terminal handling confirmed.
5. Polish → docs, performance budget, final `/speckit-analyze` pass.

### Note on Constitution Principle XII (Long-Lived Feature Branches)

plan.md deferred the question of whether this feature needs a long-lived integration branch to this
phase. Looking at the task count (38 tasks, one deletion-heavy phase touching ~20 test files, one
new subpackage): this is sized similarly to this repo's past single-PR features (e.g.
005-configurable-materials-tools, 009-milling-calculations), not to #63's genuinely multi-slice
restructuring that justified numbered slices 014-017. **Recommendation: single PR against
`017-console-text-gui`, merged directly to `main`** — revisit only if implementation reveals the
diff is unreviewable in one pass.

### Note on the Configuration screen's scope (research.md #4)

T019 implements Configuration as **read-only** (view/select the existing registry), per research.md
#4's reasoning from the spec's own "feature parity, not feature growth" assumption. This was
explicitly flagged to the user as a judgment call in the PR comment for the `/speckit-plan` step and
has not yet been confirmed. If the user wants create/edit capability instead, T019, data-model.md's
`ConfigurationView`, and contracts §2/§5 all need revising before implementation — and the task
count above would grow materially (new validation, a TOML write-back mechanism, and tests for both).
