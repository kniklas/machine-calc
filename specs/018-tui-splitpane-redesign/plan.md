# Implementation Plan: Console TUI Split-Pane Redesign

**Branch**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-tui-splitpane-redesign/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Replace PR #94's sequential full-screen dialog-chain wizard (one field per screen, via
`prompt-toolkit` `shortcuts` dialogs) with a persistent, always-visible layout: a horizontal
top-level menu bar (Exit, Machining, Configuration, About, Help), a collapsible Machining tree
(Milling/Drilling, Drilling further expandable into a tool-selection shortcut), and — once a leaf
operation is selected — a left pane holding every input simultaneously and a right pane showing a
reactively-refreshed result. This is a single long-lived `prompt-toolkit` `Application`/`Layout`
holding multiple simultaneously-focusable widgets, not a chain of separate `Application.run()`
calls, so it supersedes 017's dialog-chain architecture rather than amending it. The core
calculation wiring (`calculate()`/`calculate_end_milling()`/`calculate_face_milling()`), validation,
unit conversion, session-state semantics, and i18n catalog are reused unchanged; `menu.py`,
`machining_menu.py`, `forms.py`'s dialog-shortcut widgets, and `drilling.py`/`milling.py`'s screen
orchestration are replaced.

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
| I. Code Quality | PASS | One widget/concern per module, mirroring 017's existing split (menu bar, tree, and the shared left/right-pane operation-screen component as separate modules — see Project Structure); linting/type-checking apply as usual; `menu.py`/`machining_menu.py`/`forms.py`'s dialog widgets are *replaced*, not accreted onto. |
| II. Testing Standards | PASS (conditional) | `tasks.md` MUST add unit/contract/integration tests for the new menu bar, tree, and split-pane screens (headless, per Testing above — `_tui_test_support.py` adapted for a single long-lived `Application`, per research.md), and MUST rewrite/delete the dialog-chain-specific tests the spec's Carried-Over Items table names (`test_tui_drilling.py`, `test_tui_milling.py`, `test_tui_resize_preserves_input.py`) rather than leave them failing/skipped against code that no longer exists. |
| III. Calculation Robustness | N/A | No new/changed calculation logic (SC-004) — this is a presentation-layer redesign over existing, already-tested core functions. |
| IV. Packaging & Versioning | PASS (conditional) | This is a MINOR bump (`2.0.0` → `2.1.0`), not MAJOR: unlike 017's REPL removal, `mfgparams.console` has no scriptable/programmatic contract to break — it is already TTY-only, interactive-only (017's own "no scripting/automation entry point" guarantee, unchanged here), and CLI args (`--materials-config`) are unchanged. `tasks.md` MUST bump `src/mfgparams/__init__.py`'s `__version__` and add a `CHANGELOG.md` `[Unreleased]` entry. |
| V. Resource-Constrained Compatibility | PASS (conditional) | FR-019/SC-006 require the new reactive right-pane redraw be evaluated against Principle V's profile specifically, not assumed compatible because `calculate()` itself is unchanged. `tasks.md` MUST rewrite `tests/performance/test_tui_redraw_latency.py` to measure the real reactive redraw this feature introduces (per the Carried-Over Items table — the old dialog-chain model never had one for it to observe) and SHOULD extend `test_tui_startup_budget.py` if the new persistent `Application`'s baseline memory footprint differs materially from the old per-screen one. |
| VI. Extensibility by Design | PASS | Drilling and Milling share one left/right-pane component (FR-009's identical-pattern requirement) rather than each hand-rolling its own; a future operation attaches as a new screen module reusing that component plus a new tree leaf, not a change to Drilling's/Milling's own modules. |
| VII. Documentation & Publishing | PASS (conditional) | `tasks.md` MUST update Sphinx end-user docs (new navigation model replaces the old menu/dialog-chain instructions) and MUST add the `console/tui/` architecture docs page the Carried-Over Items table names as still missing from 017 — write it once this feature's architecture (this plan) is settled, not before. |
| VIII. Internationalization | PASS | All new UI strings (menu bar labels, tree labels, pane titles, FR-006b's invalid-number message) sourced via the existing `mfgparams.console.i18n.translate` mechanism under the existing `tui.*` namespace (FR-011); see data-model.md for the new message-key set. |
| IX. Automated Gates | PASS | Standard CI gates apply unchanged; no new runtime dependency is introduced (`prompt-toolkit` already declared), so `dependency-scan`/CodeQL/`bandit` need no new configuration. |
| X. Licensing | N/A | No licensing change. |
| XI. Multi-Agent Consistency | N/A | No agent/skill instruction files touched. |
| XII. Long-Lived Feature Branches | DEFERRED | Reuses far more of the existing architecture than 017 did (i18n, calculate() wiring, session-state semantics, materials/tools registries, entry-point gating are all unchanged) while 017 itself — building the same subsystem from nothing plus deleting the REPL — fit into one PR. Whether this feature nonetheless needs Principle XII's long-lived-integration-branch treatment is deferred to `/speckit-tasks`, once the task breakdown shows the actual diff size, mirroring 017's own precedent for this exact judgment call. |

No unjustified violations — Complexity Tracking table below is empty.

**Post-Phase-1 re-check**: Phase 1 design (data-model.md, contracts/console-tui-splitpane-contract.md,
quickstart.md) introduces no gate beyond what the table above already accounts for. Research.md's
two open items (terminal-size floor verification; `_tui_test_support.py` adaptation for a
single-`Application` model) are Phase 0 research outputs, not gate failures — data-model.md and the
contract both build on their resolutions. No new NEEDS CLARIFICATION surfaced; all three questions
spec.md flagged for `/speckit-clarify` were resolved before this plan (spec.md's Clarifications
section).

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
    ├── app.py                     # REWRITTEN: was a `NavigationState` push/pop while-loop
    │                               # dispatching between short-lived per-screen Applications;
    │                               # becomes the single persistent Application/Layout wiring
    │                               # (menu bar + tree + active operation's left/right panes),
    │                               # constructed once per session (FR-013a's resize guarantee
    │                               # now applies to this one long-lived object).
    ├── terminal_capability.py     # EXTENDED: MIN_COLUMNS/MIN_LINES raised per the verified
    │                               # floor (research.md), gating sequence itself unchanged
    │                               # (FR-013).
    ├── menu.py                    # REPLACED: was a full-screen hand-rolled mnemonic menu;
    │                               # becomes the persistent horizontal menu-bar widget (FR-001).
    │                               # `run_menu`'s mnemonic-assignment logic (`_assign_mnemonics`)
    │                               # is reusable as-is for the bar's own items and the tree's
    │                               # leaves (FR-010) — not full-screen-dialog-specific.
    ├── machining_menu.py          # REPLACED by the collapsible Machining tree widget (FR-002/
    │                               # FR-003), nested under the menu bar's Machining item rather
    │                               # than a separate full-screen submenu.
    ├── forms.py                   # SPLIT: dialog-shortcut widgets (`ask_number`, `ask_choice`,
    │                               # `ask_material_type`, etc. — built on `radiolist_dialog`/
    │                               # `input_dialog`) are replaced by the new left-pane field
    │                               # widgets (FR-016/FR-017). Pure data-shaping helpers with no
    │                               # dialog dependency — `UNIT_LABELS`, `convert_length`,
    │                               # `convert_power`, `format_result`, `material_type_label` —
    │                               # are kept and reused unchanged (confirmed reusable in the
    │                               # prototype; FR-006a/FR-006b depend on `format_result`
    │                               # specifically).
    └── screens/
        ├── drilling.py            # REWRITTEN: `DrillingSessionState` dataclass and its field
        │                          # semantics/default-carryover are kept unchanged (FR-012);
        │                          # `run_drilling_screen`'s sequential-dialog orchestration is
        │                          # replaced by the left/right split-pane pattern (FR-004/
        │                          # FR-005/FR-005a/FR-006/FR-006a/FR-006b/FR-007), reusing this
        │                          # module's own `calculate()` call and unit-conversion helpers
        │                          # unchanged.
        ├── milling.py             # REWRITTEN: same shape as drilling.py, for both
        │                          # `calculate_end_milling()`/`calculate_face_milling()` and
        │                          # `MillingSessionState`; the sub-operation choice (FR-009a)
        │                          # becomes a left-pane field with a tree shortcut, mirroring
        │                          # Drilling's tool-selection placement (FR-009's identical-
        │                          # pattern requirement).
        ├── configuration.py       # EXTENDED: still view-only (FR-014, resolved), now covers all
        │                          # three tool registries — drilling, end-mill, face-mill — not
        │                          # only drilling's (FR-015, closing PR #94's deferred gap).
        ├── about.py                # UNCHANGED content; reachable from the persistent menu bar
        │                          # instead of the old full-screen top menu (FR-001).
        └── help.py                 # UNCHANGED content; same placement change as about.py.

tests/
├── unit/console/tui/              # EXTENDED — unit tests for the new menu-bar/tree widgets and
│                                  # the shared left/right-pane component.
├── contract/
│   └── test_console_tui_contract.py            # UPDATED (research.md's consolidated decisions
│                                  # table) — rewritten in place against
│                                  # contracts/console-tui-splitpane-contract.md;
│                                  # 017's contract described the now-replaced dialog-chain
│                                  # structure, but no second, differently-named contract test file
│                                  # is added for the same subsystem.
├── integration/
│   ├── _tui_test_support.py       # ADAPTED (research.md) — driving one persistent Application
│   │                              # instead of a dialog chain.
│   ├── test_tui_drilling.py       # REWRITTEN — left/right-pane flow, all three modes, asserted
│   │                              # against the actual rendered/displayed result (Carried-Over
│   │                              # Items table: don't just port the old dialog-chain assertions).
│   ├── test_tui_milling.py        # REWRITTEN — same, both sub-operations × all three modes.
│   ├── test_tui_resize_preserves_input.py  # REWRITTEN — FR-013a, against the new persistent
│   │                              # Application, not the old per-screen one 017's version tested.
│   ├── test_tui_validation.py     # EXTENDED — FR-006a (cross-field rejection) and FR-006b
│   │                              # (unparseable text) cases.
│   ├── test_tui_terminal_too_small.py  # UPDATED — new MIN_COLUMNS/MIN_LINES floor.
│   └── test_tui_no_tty_fallback.py, test_tui_app_run.py, test_tui_static_screens.py,
│       test_tui_i18n.py           # LIKELY UNCHANGED in intent, updated only where they construct
│                                  # the now-replaced `NavigationState`/screen-stack directly
│                                  # (research.md confirms exact touch points).
├── static/
│   └── test_console_catalogue_ownership.py    # UNCHANGED — already generalized (017) to scan
│                                  # every non-`locales` file under `console/`.
└── performance/
    ├── test_tui_redraw_latency.py  # REWRITTEN (Constitution Check row V) — measures the real
    │                              # reactive right-pane redraw this feature introduces (SC-006).
    └── test_tui_startup_budget.py  # RE-VERIFIED, extended only if research.md finds the new
                                   # persistent Application's baseline RSS differs materially.
```

**Structure Decision**: Single project (Option 1), continuing to extend the existing
`mfgparams.console.tui` subpackage in place — no new top-level package or subpackage boundary.
`DrillingSessionState`/`MillingSessionState` stay defined in their existing screen modules
(`screens/drilling.py`/`screens/milling.py`) per FR-012, since moving them would be a change to
"what those fields are" the spec explicitly says this feature does not make (Key Entities).

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally empty.*
