# Implementation Plan: Console Text GUI (TUI)

**Branch**: `017-console-text-gui` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-console-text-gui/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Replace `mfgparams.console`'s line-based REPL with a full-screen, keyboard-navigable, menu-driven
text GUI (Machining → Milling/Drilling; Configuration; About; Help), built on **prompt-toolkit**
(confirmed by the technical spike, [spike-tui-framework.md](spike-tui-framework.md)) and reusing
the console's existing i18n and calculation-invocation infrastructure. The REPL is deleted, not
kept — a breaking CLI change requiring a MAJOR version bump (1.0.0 → 2.0.0) and a changelog entry
(FR-013). There is no REPL fallback for terminals the text GUI cannot run in: the console instead
detects that case proactively (before constructing the framework, since prompt-toolkit itself
degrades silently rather than failing — see research.md #2) and exits with a clear, localized
message.

## Technical Context

**Language/Version**: Python ≥3.9 (`pyproject.toml`'s `requires-python`; the spike ran under
3.9.0, the project floor, and confirmed prompt-toolkit installs and runs there).

**Primary Dependencies**: `prompt-toolkit` (new, added to the `console` extra — currently empty
since 014). Reuses `mfgparams.console.i18n`/`mfgparams.console.locales.*` (message catalog),
`mfgparams.registry`/`mfgparams.registry_config` (materials/tools), and the core calculation
functions already used by `console/cli.py` (`mfgparams.processes.machining.drilling`/`.milling`).

**Storage**: N/A — no new persistence (spec Assumptions); materials/tools configuration continues
to be read from the existing `--materials-config` TOML file, unchanged.

**Testing**: `pytest`, matching this repo's existing suite layout (`tests/unit`, `tests/integration`,
`tests/contract`, `tests/static`, `tests/performance`). Headless TUI testing follows the spike's own
method: `prompt_toolkit.output.DummyOutput` + `prompt_toolkit.input.create_pipe_input` to drive
screens without a real terminal.

**Target Platform**: Cross-platform terminal (Linux/macOS/Windows), including older/long-term-stable
OS releases and constrained/legacy hardware (Constitution Principle V).

**Project Type**: Single project (existing `src/`-layout library + CLI) — Option 1 in the structure
below; no new top-level project.

**Performance Goals**: Perceived input-to-redraw latency <200ms (SC-002) on Principle V's
legacy-hardware profile; the spike's measured cold-start (~0.3-0.4s) and minimal-screen peak RSS
(~25.7 MB) leave large headroom under that profile's ~64-128 MB target.

**Constraints**: Principle V's ~64-128 MB RAM / single-threaded-CPU / minimal-clock-speed profile;
FR-011's 25×80 minimum terminal size; FR-013's MAJOR-version/changelog obligation; no REPL fallback
(FR-006) — an unsupported terminal must fail closed with a clear message, not degrade silently
(research.md #2 documents why this can't be left to prompt-toolkit's own behavior).

**Scale/Scope**: Single-user, local, interactive tool. One top-level menu with 4 entries
(Machining → Milling, Drilling; Configuration; About; Help); 2 operation forms at ship time
(Milling, Drilling — matching current REPL parity per FR-002); no multi-user/concurrency concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Code Quality | PASS | One screen/concern per module (see Project Structure); linting/type-checking apply as usual; no god-functions — `cli.py`'s existing REPL prompt functions are being *replaced*, not accreted onto. |
| II. Testing Standards | PASS (conditional) | `tasks.md` MUST add unit/contract/integration tests for every new screen (headless, per Testing above) *before or alongside* implementation, and MUST delete REPL-specific tests together with the REPL code they tested (SC-004) — not leave them failing/skipped. |
| III. Calculation Robustness | N/A | No new/changed calculation logic; this is a presentation-layer replacement over existing, already-tested core functions. |
| IV. Packaging & Versioning | PASS (conditional) | `tasks.md` MUST bump `src/mfgparams/__init__.py`'s `__version__` from `1.0.0` to `2.0.0` (MAJOR — breaking CLI change) and add a `CHANGELOG.md` `[Unreleased]` entry documenting REPL removal, per FR-013. |
| V. Resource-Constrained Compatibility | PASS | Addressed by the completed spike (spike-tui-framework.md); prompt-toolkit not disqualified. Implementation SHOULD add a `tests/performance`-style budget check for the shipped app (not just framework import) before merge, per Additional Constraints' "performance MUST be measured, not assumed." |
| VI. Extensibility by Design | PASS | Machining submenu and per-operation screens are separate modules (`screens/milling.py`, `screens/drilling.py`); a future operation attaches as a new screen + menu entry, not a change to existing ones. |
| VII. Documentation & Publishing | PASS (conditional) | `tasks.md` MUST update Sphinx end-user docs (new TUI usage replaces REPL usage instructions) and developer docs (new `console/tui/` architecture), consistent with Principle VII. |
| VIII. Internationalization | PASS | All new UI strings sourced from `mfgparams.console.locales.en` via `mfgparams.console.i18n.translate`, per FR-003; see data-model.md for the new message-key set and contracts/console-tui-contract.md for catalogue-ownership implications. |
| IX. Automated Gates | PASS | Standard CI gates apply unchanged; `prompt-toolkit`'s addition is covered automatically by `dependency-scan`/CodeQL/`bandit` once declared in `pyproject.toml`. |
| X. Licensing | N/A | No licensing change. |
| XI. Multi-Agent Consistency | N/A | No agent/skill instruction files touched. |
| XII. Long-Lived Feature Branches | DEFERRED | This feature (REPL deletion + full TUI build + version bump) is larger than most single-PR specs in this repo. Whether it needs Principle XII's long-lived-integration-branch treatment (multiple sub-PRs against `017-console-text-gui`) is deferred to `/speckit-tasks`, once the task breakdown shows how large the diff actually is — not a plan-time blocker. |

No unjustified violations — Complexity Tracking table below is empty.

**Post-Phase-1 re-check**: Phase 1 design (data-model.md, contracts/console-tui-contract.md,
quickstart.md) introduces no gate beyond what the table above already accounts for. Two rows
gained concrete obligations during design rather than new risk: II now names the exact test files
to add/delete (Project Structure below); IV/§6 of the contract now names the exact version string
(`2.0.0`) and changelog location. No new NEEDS CLARIFICATION surfaced; research.md #4's
Configuration-scope decision is flagged as an open item for the user, not a gate failure.

## Project Structure

### Documentation (this feature)

```text
specs/017-console-text-gui/
├── plan.md                      # This file (/speckit.plan command output)
├── research.md                  # Phase 0 output (/speckit.plan command)
├── data-model.md                # Phase 1 output (/speckit.plan command)
├── quickstart.md                # Phase 1 output (/speckit.plan command)
├── spike-tui-framework.md       # Pre-plan technical spike (already run)
├── contracts/
│   └── console-tui-contract.md  # Phase 1 output (/speckit.plan command)
└── tasks.md                     # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/mfgparams/
├── __init__.py                  # __version__ bump: "1.0.0" -> "2.0.0" (FR-013)
├── __main__.py                  # UNCHANGED: existing missing-dependency guard already
│                                 # generically covers whatever `console` ends up requiring
│                                 # (_console_extra_roots() reads installed metadata) — no
│                                 # edit needed there for FR-005/FR-011 parity.
├── console/
│   ├── __init__.py               # UNCHANGED (layering docstring/contract still applies)
│   ├── __main__.py               # UNCHANGED (delegates to mfgparams.__main__.main)
│   ├── cli.py                    # GUTTED: REPL prompt/session functions deleted (FR-001,
│   │                              # FR-007); becomes a thin `main()` that launches the TUI
│   │                              # app from `tui/app.py`. Existing calculation-invocation
│   │                              # helpers that are REPL-independent (material/tool lookup,
│   │                              # result formatting data, NOT the `input()`-based prompt
│   │                              # functions) move into `tui/` or a shared module — see
│   │                              # research.md #3 for the exact split.
│   ├── i18n.py                   # UNCHANGED (FR-003 reuses this unmodified)
│   ├── locales/
│   │   └── en.py                 # EXTENDED: new `tui.*` message keys (menu labels, screen
│   │                              # titles, no-TTY/too-small-terminal messages); REPL-only
│   │                              # `cli.*` keys removed alongside the code that used them.
│   └── tui/                      # NEW subpackage — the text GUI itself
│       ├── __init__.py
│       ├── app.py                 # Application wiring: prompt-toolkit Application, root
│       │                          # Layout, global key bindings, locale-at-startup binding
│       │                          # (Principle VIII, spec Assumptions "single active locale
│       │                          # per session").
│       ├── terminal_capability.py # FR-006/FR-008/FR-011: proactive TTY + 25x80-size check
│       │                          # run *before* constructing the Application (research.md #2).
│       ├── menu.py                # Top-level menu screen (FR-009/FR-010): Machining,
│       │                          # Configuration, About, Help.
│       ├── machining_menu.py      # Machining submenu: Milling, Drilling.
│       └── screens/
│           ├── __init__.py
│           ├── milling.py         # Milling parameter-entry screen (mirrors existing
│           │                      # `_run_milling_session`/`_prompt_milling_inputs` flow).
│           ├── drilling.py        # Drilling parameter-entry screen (mirrors existing
│           │                      # `_run_drilling_session` flow).
│           ├── configuration.py   # Configuration screen — v1 scope is read-only
│           │                      # view/selection of the active materials/tools registry
│           │                      # (parity with REPL's `--materials-config`, not new
│           │                      # create/edit capability — see research.md #4).
│           ├── about.py           # About screen (name, version, license pointer).
│           └── help.py            # Help screen (FR-009 placeholder — reachable, non-crashing).
└── (rest of src/mfgparams/ unchanged: models.py, registry.py, registry_config.py,
    processes/, i18n.py, locales/, data/)

tests/
├── unit/
│   └── console/                  # NEW — headless per-screen unit tests
│       └── tui/
├── contract/
│   └── test_console_tui_contract.py   # NEW — validates contracts/console-tui-contract.md
│                                       # (menu structure, shortcuts, message-key ownership)
├── integration/
│   ├── test_tui_milling.py            # NEW — end-to-end headless milling flow
│   ├── test_tui_drilling.py           # NEW — end-to-end headless drilling flow
│   ├── test_tui_no_tty_fallback.py    # NEW — replaces the REPL-fallback assertions in
│   │                                  # test_cli_edge_cases.py's no-TTY cases
│   └── test_cli_*.py                  # DELETED where they test REPL-only behavior that no
│                                       # longer exists (SC-004); kept where they test
│                                       # REPL-independent behavior that moved (rare — most
│                                       # existing integration tests drive the REPL directly
│                                       # via stdin and cannot survive REPL removal as-is).
├── static/
│   ├── test_core_does_not_import_console.py  # UNCHANGED — still enforces core/console
│   │                                          # layering; unaffected by REPL->TUI swap.
│   └── test_console_catalogue_ownership.py    # UPDATED — currently scans `console/cli.py`
│                                               # by name; generalized to scan every non-
│                                               # `locales` file under `console/` (research.md #1).
└── performance/
    └── test_tui_startup_budget.py     # NEW (SHOULD, per Constitution Check row V) — measures
                                        # the shipped app's own cold-start RSS/time against a
                                        # Principle V budget, using the existing
                                        # tests/performance/harness.py machinery.
```

**Structure Decision**: Single project (Option 1), extending the existing `mfgparams.console`
package with a new `tui/` subpackage rather than a new top-level package — required by FR-007.
`cli.py` is kept as the module name for the console's entry point (`console/__main__.py` and
`mfgparams/__main__.py` both already import `mfgparams.console.cli`, per the existing
missing-dependency guard's provenance detection in `__main__.py`, which is path-based against
`mfgparams/console/` as a whole and therefore unaffected by files moving *within* that directory)
but its content changes completely: REPL session/prompt functions are deleted, and it becomes a
thin dispatcher into `tui/app.py`.

## Complexity Tracking

*No Constitution Check violations requiring justification — table intentionally empty.*
