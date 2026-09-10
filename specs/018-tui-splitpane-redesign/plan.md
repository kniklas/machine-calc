# Implementation Plan: Console TUI Split-Pane Redesign

**Branch**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-tui-splitpane-redesign/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Replace PR #94's sequential full-screen dialog-chain wizard (one field per screen, via
`prompt-toolkit` `shortcuts` dialogs) with a persistent, always-visible layout: a horizontal
top-level menu bar (Exit, Machining, Configuration, About, Help) and a collapsible Machining tree
(Milling, Drilling — both flat leaves) stay visible underneath; selecting a leaf operation opens
its **floating window** (a centered, bordered `prompt_toolkit.layout.Float`, matching the pre-plan
prototype's own confirmed styling) holding a left pane with every input simultaneously visible and
a right pane showing a reactively-refreshed result. This is a single long-lived `prompt-toolkit`
`Application`/`Layout` (a `FloatContainer` wrapping the bar+tree, with the operation window as its
one `Float`) holding multiple simultaneously-focusable widgets, not a chain of separate
`Application.run()` calls, so it supersedes 017's dialog-chain architecture rather than amending
it.

**Revision note (this plan re-run)**: `/speckit-clarify` was reopened after this feature's first
implementation pass shipped, per user feedback on PR #96 preferring the pre-plan prototype's UI.
Three requirements changed as a result — FR-004 (embedded split pane → floating window), FR-003
(retired: Drilling's tree-level tool-selection shortcut is gone, Drilling is now a flat leaf like
Milling), and FR-005 (radio fields render as `prompt_toolkit.widgets.RadioList`, accordion-style,
not the shipped inline-text renderer) — and this plan is updated accordingly (research.md #3-4,
data-model.md's `MachiningTree`, this file's Project Structure). The core calculation wiring
(`calculate()`/`calculate_end_milling()`/`calculate_face_milling()`), validation, unit conversion,
session-state semantics, and i18n catalog remain reused unchanged throughout.

## Technical Context

**Language/Version**: Python ≥3.9 (`pyproject.toml`'s `requires-python`, unchanged).

**Primary Dependencies**: `prompt-toolkit` (already declared under the `console` extra since 017 —
no new dependency). Reuses `mfgparams.console.i18n`/`mfgparams.console.locales.en` (message
catalog), `mfgparams.registry`/`mfgparams.registry_config` (materials/tools, including
`list_material_types()`'s data-driven category set — FR-005), and the core calculation functions
already wired up by the current `screens/drilling.py`/`screens/milling.py`
(`mfgparams.processes.machining.drilling`/`.milling`).

**Storage**: N/A — no new persistence (spec Assumptions); materials/tools configuration continues
to be read from the existing `--materials-config` TOML file, unchanged.

**Testing**: `pytest`, matching this repo's existing suite layout. Headless TUI testing reuses
`tests/integration/_tui_test_support.py`'s existing technique (`prompt_toolkit.output.DummyOutput` +
`prompt_toolkit.input.create_pipe_input`, driven from a background thread with explicit
`contextvars` propagation) — but that helper's docstring describes driving "a chain of
prompt-toolkit dialogs internally"; this feature's single long-lived `Application` is a materially
different shape (one `.run()` call, not a sequence), so the helper needs revisiting during Phase 0
research, not assumed to work as-is (see research.md).

**Target Platform**: Cross-platform terminal (Linux/macOS/Windows), including older/long-term-stable
OS releases and constrained/legacy hardware (Constitution Principle V) — unchanged from 017.

**Project Type**: Single project (existing `src/`-layout library + CLI) — Option 1 in the structure
below; no new top-level project. Extends the existing `mfgparams.console.tui` subpackage.

**Performance Goals**: Perceived input-to-update latency <200ms (SC-006) on Principle V's
legacy-hardware profile, specifically for the right pane's automatic recalculation on every
left-pane input change (FR-007) — a materially new, continuously-recomputing workload relative to
017's one-shot-per-dialog compute that `test_tui_redraw_latency.py` has never actually measured
(spec's Carried-Over Items table).

**Constraints**: Principle V's ~64-128 MB RAM / single-threaded-CPU / minimal-clock-speed profile
(FR-019); the 25×80 terminal-size floor likely needs raising for the complete layout (menu bar +
tree + operation screen together) per spec's revised Assumption — the exact number is not yet
verified and is a Phase 0 research item, not assumed; FR-013's gating-mechanism-unchanged
requirement (no-TTY/terminal-too-small detection still runs before any prompt-toolkit object is
constructed).

**Scale/Scope**: Single-user, local, interactive tool — unchanged in scope from 017/PR #94. Same
two operations (Drilling; Milling with its existing End-Milling/Face-Milling sub-operation, FR-009a)
and three calculation modes (standard, power-constrained, fixed-RPM); this feature changes
presentation and interaction model only, not what can be calculated (spec Assumptions, SC-004).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Code Quality | PASS | One widget/concern per module, mirroring 017's existing split (menu bar, tree, and the shared left/right-pane operation-screen component as separate modules — see Project Structure); linting/type-checking apply as usual; `menu.py`/`machining_menu.py`/`forms.py`'s dialog widgets are *replaced*, not accreted onto. The `FloatContainer`/`Float` wiring (research.md #3) lives in `app.py` alongside the rest of its `Layout` construction, not a new module — it is composition of existing pieces (the bar+tree `HSplit`, the operation screen's own `HSplit`/`VSplit`), not new widget logic. |
| II. Testing Standards | PASS (conditional) | `tasks.md` MUST re-rewrite the split-pane/navigation tests this feature's *first* implementation pass already wrote once (`test_tui_navigation.py`, `test_tui_drilling.py`, `test_tui_milling.py`, `test_tui_field_editing.py`, `test_console_tui_contract.py`, and `screens/split_pane.py`'s own coverage) against the revised FR-003/FR-004/FR-005 shape — a second rewrite of already-once-rewritten tests, not fresh no-existing-code work, since this plan re-run follows a shipped-then-reopened revision, not a first pass. |
| III. Calculation Robustness | N/A | No new/changed calculation logic (SC-004) — this is a presentation-layer redesign over existing, already-tested core functions. |
| IV. Packaging & Versioning | PASS (conditional) | This is a MINOR bump (`2.0.0` → `2.1.0`), not MAJOR: unlike 017's REPL removal, `mfgparams.console` has no scriptable/programmatic contract to break — it is already TTY-only, interactive-only (017's own "no scripting/automation entry point" guarantee, unchanged here), and CLI args (`--materials-config`) are unchanged. `tasks.md` MUST bump `src/mfgparams/__init__.py`'s `__version__` and add a `CHANGELOG.md` `[Unreleased]` entry. |
| V. Resource-Constrained Compatibility | PASS (conditional) | FR-019/SC-006 require the new reactive right-pane redraw be evaluated against Principle V's profile specifically, not assumed compatible because `calculate()` itself is unchanged. `tasks.md` MUST rewrite `tests/performance/test_tui_redraw_latency.py` to measure the real reactive redraw this feature introduces (per the Carried-Over Items table — the old dialog-chain model never had one for it to observe) and SHOULD extend `test_tui_startup_budget.py` if the new persistent `Application`'s baseline memory footprint differs materially from the old per-screen one. |
| VI. Extensibility by Design | PASS | Drilling and Milling share one left/right-pane component (FR-009's identical-pattern requirement) rather than each hand-rolling its own; a future operation attaches as a new screen module reusing that component plus a new tree leaf, not a change to Drilling's/Milling's own modules. |
| VII. Documentation & Publishing | PASS (conditional) | README.md/`docs/source/{drilling,milling}.rst` and the `console/tui/` architecture note (README) already describe this feature's *first* pass (embedded split pane, inline radio text) — `tasks.md` MUST update them again for the floating-window/`RadioList` shape, not leave the now-superseded description in place. |
| VIII. Internationalization | PASS | All new UI strings (menu bar labels, tree labels, pane titles, FR-006b's invalid-number message) sourced via the existing `mfgparams.console.i18n.translate` mechanism under the existing `tui.*` namespace (FR-011); see data-model.md for the new message-key set. |
| IX. Automated Gates | PASS | Standard CI gates apply unchanged; no new runtime dependency is introduced (`prompt-toolkit` already declared), so `dependency-scan`/CodeQL/`bandit` need no new configuration. |
| X. Licensing | N/A | No licensing change. |
| XI. Multi-Agent Consistency | N/A | No agent/skill instruction files touched. |
| XII. Long-Lived Feature Branches | DEFERRED | Reuses far more of the existing architecture than 017 did (i18n, calculate() wiring, session-state semantics, materials/tools registries, entry-point gating are all unchanged) while 017 itself — building the same subsystem from nothing plus deleting the REPL — fit into one PR. Whether this feature nonetheless needs Principle XII's long-lived-integration-branch treatment is deferred to `/speckit-tasks`, once the task breakdown shows the actual diff size, mirroring 017's own precedent for this exact judgment call. |

No unjustified violations — Complexity Tracking table below is empty.

**Post-Phase-1 re-check**: Phase 1 design (data-model.md, contracts/console-tui-splitpane-contract.md,
quickstart.md) introduces no gate beyond what the table above already accounts for. Research.md's
four items (terminal-size floor verification; `_tui_test_support.py` adaptation for a
single-`Application` model; `FloatContainer`/`Float` construction; `RadioList` accordion rendering
and its keyboard-contract consequence) are Phase 0 research outputs, not gate failures —
data-model.md and the contract both build on their resolutions. No new NEEDS CLARIFICATION
surfaced; every question raised across both `/speckit-clarify` sessions (the original three, and
this revision's three reopening FR-003/FR-004/FR-005) was resolved before this plan re-run
(spec.md's Clarifications section, both dated sessions).

## Project Structure

### Documentation (this feature)

```text
specs/018-tui-splitpane-redesign/
├── plan.md                                # This file (/speckit.plan command output)
├── research.md                            # Phase 0 output (/speckit.plan command)
├── data-model.md                          # Phase 1 output (/speckit.plan command)
├── quickstart.md                          # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── console-tui-splitpane-contract.md  # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md                    # Spec quality checklist (already exists, /speckit-clarify)
└── tasks.md                               # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
src/mfgparams/console/
├── cli.py                        # UNCHANGED: terminal_capability.check() gating sequence stays
│                                  # first (FR-013); only the `run()` it calls into changes shape.
├── i18n.py                       # UNCHANGED (FR-011 reuses this unmodified)
├── locales/
│   └── en.py                     # EXTENDED: new `tui.*` keys for the menu bar, tree, pane
│                                  # titles, and FR-006b's invalid-number message; no REPL-era
│                                  # `cli.*` keys to remove (017 already did that cleanup).
└── tui/
    ├── app.py                     # REWRITTEN AGAIN (revision): the already-shipped `app.py`
    │                               # built one persistent Application/Layout with a
    │                               # `DynamicContainer` swapping the body between the tree and
    │                               # an embedded operation pane. This revision changes the root
    │                               # container to a `FloatContainer` wrapping the bar+tree
    │                               # `HSplit`, adding/removing a single `Float` (the operation
    │                               # screen, in a bordered `Frame`) as `SessionUI.open_operation`
    │                               # is set/cleared (research.md #3) — the bar+tree `HSplit`
    │                               # itself, and FR-013a's one-persistent-Application resize
    │                               # guarantee, are unchanged by this revision.
    ├── terminal_capability.py     # UNCHANGED by this revision — MIN_LINES/MIN_COLUMNS already
    │                               # raised in the first pass; research.md #4's row-math
    │                               # cross-check confirms no further change is needed.
    ├── menu.py                    # UNCHANGED by this revision — the persistent horizontal
    │                               # menu-bar widget (FR-001) already shipped in the first pass;
    │                               # `_assign_mnemonics` reuse is unaffected by the tree
    │                               # flattening or the floating window.
    ├── machining_menu.py          # REWRITTEN (revision): loses `drilling_expanded`/the
    │                               # tool-selection-shortcut row entirely (FR-003 retired) —
    │                               # `tree_rows()` always returns exactly the two flat leaves,
    │                               # Milling and Drilling, with no further expansion state to
    │                               # track or render.
    ├── forms.py                   # UNCHANGED by this revision — already pruned to pure
    │                               # data-shaping helpers in the first pass (research.md's
    │                               # original consolidated table); this revision doesn't reopen
    │                               # that split.
    └── screens/
        ├── split_pane.py          # REWRITTEN (revision): the shared left/right-pane engine
        │                          # (`RadioRow`/`NumberRow`, navigation, the right pane's
        │                          # three-state machine) already shipped in the first pass.
        │                          # This revision replaces `RadioRow`'s rendering with
        │                          # `prompt_toolkit.widgets.RadioList` for the currently-focused
        │                          # radio field (accordion — one-line summary for every other
        │                          # radio field), and its Left/Right-cycles-the-value key
        │                          # handling with `RadioList`'s own Up/Down/Enter/Space bindings
        │                          # (research.md #4) — `NumberRow`'s instant-edit/nudge behavior
        │                          # (FR-016/FR-017) is unchanged. Also now owns constructing the
        │                          # `Float`/`Frame` wrapper `app.py` adds to its
        │                          # `FloatContainer` (research.md #3), since that's the
        │                          # operation screen's own presentation, not `app.py`'s
        │                          # navigation-shell concern.
        ├── drilling.py            # UNCHANGED by this revision — `DrillingSessionState` and
        │                          # `rows_for()`'s field list/order (FR-005/FR-012) already
        │                          # shipped in the first pass; only `split_pane.py`'s rendering
        │                          # of the rows this module returns changes.
        ├── milling.py             # UNCHANGED by this revision — same reasoning as drilling.py;
        │                          # the sub-operation choice (FR-009a) stays a left-pane-only
        │                          # field with no tree shortcut, as it always was (FR-009's
        │                          # identical-pattern requirement, now symmetric with Drilling's
        │                          # own no-tree-shortcut resolution too).
        ├── configuration.py       # UNCHANGED by this revision — still view-only (FR-014),
        │                          # covering all three tool registries (FR-015); not part of the
        │                          # floating-window/tree-flattening/RadioList scope.
        ├── about.py                # UNCHANGED (content and placement both settled in the first
        │                          # pass).
        └── help.py                 # UNCHANGED, same reasoning as about.py.

tests/
├── unit/console/tui/              # EXTENDED — unit tests for the new menu-bar/tree widgets and
│                                  # the shared left/right-pane component.
├── contract/
│   └── test_console_tui_contract.py            # REWRITTEN AGAIN (revision) — the tree-structure
│                                  # invariant changes to two flat leaves (no more
│                                  # `drilling_expanded`/tool-selection-shortcut row or its
│                                  # mnemonic).
├── integration/
│   ├── _tui_test_support.py       # UNCHANGED by this revision — the headless-driving technique
│   │                              # (research.md #2) is orthogonal to the tree/window/radio
│   │                              # shape.
│   ├── test_tui_navigation.py     # REWRITTEN AGAIN (revision) — every test exercising the old
│   │                              # "toggle Drilling's shortcut, then select Tool" sequence is
│   │                              # now simply "select Drilling" (a flat leaf); FR-005a's
│   │                              # tree-collapse-never-closes-the-screen tests are simplified,
│   │                              # not removed, since the floating window still needs that
│   │                              # guarantee (now trivially, research.md #3).
│   ├── test_tui_field_editing.py  # REWRITTEN AGAIN (revision) — its Left/Right-cycles-a-radio
│   │                              # assertions are now wrong (research.md #4); replaced with
│   │                              # Up/Down-navigates-the-open-`RadioList`/Enter-or-Space-commits
│   │                              # assertions. Numeric instant-edit/nudge assertions (FR-016/
│   │                              # FR-017) are unchanged.
│   ├── test_tui_app_run.py, test_tui_resize_preserves_input.py  # REWRITTEN AGAIN (revision) —
│   │                              # both drive real key sequences through the tree to reach
│   │                              # Drilling; the sequence simplifies (no more shortcut-toggle
│   │                              # step) but the scenarios themselves (a full calculation
│   │                              # end-to-end; a resize mid-entry) are unchanged.
│   └── test_tui_drilling.py, test_tui_milling.py, test_tui_validation.py, test_tui_results.py,
│       test_tui_calculation_parity.py, test_tui_materials_config.py, test_tui_static_screens.py,
│       test_tui_terminal_too_small.py, test_tui_no_tty_fallback.py, test_tui_i18n.py  #
│                                  # LIKELY UNCHANGED by this revision — `drilling.py`/`milling.py`
│                                  # themselves aren't touched (Project Structure above), and
│                                  # these test `rows_for()`/`calculate_result()`/the right pane's
│                                  # state machine directly, not through radio-specific key
│                                  # bindings; confirm during implementation, don't assume.
├── unit/console/tui/
│   └── test_machining_tree.py     # REWRITTEN AGAIN (revision) — `MachiningTree` loses
│                                  # `toggle_drilling()`/`drilling_expanded` entirely; this
│                                  # file's coverage of that method/field and its validation rule
│                                  # is removed, not just updated, since the thing it tested no
│                                  # longer exists.
├── static/
│   └── test_console_catalogue_ownership.py    # UNCHANGED — already generalized (017) to scan
│                                  # every non-`locales` file under `console/`.
└── performance/
    ├── test_tui_redraw_latency.py  # UNCHANGED by this revision — measures
    │                              # `split_pane.render_right_pane` directly against a completed
    │                              # screen, orthogonal to how radio fields render or whether the
    │                              # screen is embedded or floating.
    └── test_tui_startup_budget.py  # UNCHANGED by this revision.
```

**Structure Decision**: Single project (Option 1), continuing to extend the existing
`mfgparams.console.tui` subpackage in place — no new top-level package or subpackage boundary.
`DrillingSessionState`/`MillingSessionState` stay defined in their existing screen modules
(`screens/drilling.py`/`screens/milling.py`) per FR-012, since moving them would be a change to
"what those fields are" the spec explicitly says this feature does not make (Key Entities).

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally empty.*
