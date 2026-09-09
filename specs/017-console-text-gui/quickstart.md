# Quickstart: Console Text GUI (TUI)

**Feature**: `017-console-text-gui` | **Date**: 2026-09-08

Validation scenarios proving the feature works end-to-end, once implemented per plan.md/tasks.md.
Links to contracts/data-model rather than restating them.

## Prerequisites

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[console,test]"
```

Installs `mfgparams` with the now-populated `console` extra (prompt-toolkit) and the test toolchain.

## Scenario 1 — Launch and complete a Drilling calculation (User Story 1, contracts §1/§5)

```bash
mfgparams
```

Expected: the text GUI's top-level menu appears (contracts §2) within a normal terminal. Navigate
`Machining` → `Drilling` (arrow keys + Enter, or the mnemonic keys per contracts §3), enter valid
parameters, and confirm a result is displayed without leaving the text GUI (spec User Story 1,
Acceptance Scenario 1). Compare the displayed value against calling
`mfgparams.processes.machining.drilling.calculate(...)` directly with the same arguments in a
Python shell — they must match (spec User Story 1's Independent Test).

## Scenario 2 — Invalid input shows an in-place, localized error (User Story 1, Scenario 2)

Same as Scenario 1, but enter an out-of-range or non-numeric value for a required field. Expected:
a validation message appears in place, sourced from the catalog (contracts §4), and the field can
be corrected without restarting the text GUI.

## Scenario 3 — Non-English locale (User Story 2)

```bash
MFGPARAMS_LOCALE=<supported-non-english-locale> mfgparams
```

Expected: every visible label/prompt/help string and a deliberately-triggered validation error
render in that locale (or fall back to English per the existing rule) — no string sourced from
anywhere but the catalog (FR-003).

## Scenario 4 — No TTY / unsupported terminal (User Story 3, contracts §1)

```bash
echo "" | mfgparams
```

Expected: the process exits promptly with a clear, actionable, localized message (never a Python
traceback, never prompt-toolkit's own unlocalized "Input is not a terminal" warning, never a
silent hang) — per research.md #2, this must be caught *before* any prompt-toolkit object is
constructed.

## Scenario 5 — Terminal too small (FR-008/FR-011)

```bash
COLUMNS=40 LINES=10 mfgparams   # or resize the terminal below 25x80 before launch
```

Expected: a clear message rather than a garbled/truncated display, per contracts §1.

## Scenario 6 — Menu structure and shortcuts (FR-009/FR-010, SC-006)

Launch `mfgparams` with no prior instructions. Confirm: the exact menu set in contracts §2 is
visible with on-screen shortcut hints, and a first-time user can reach a Milling calculation and
locate Help within the keystroke budget `tasks.md` fixes for SC-006's usability walkthrough.

## Automated equivalents

Each scenario above has (or, per plan.md's Project Structure, will have) an automated,
headless counterpart under `tests/integration/test_tui_*.py`, `tests/contract/
test_console_tui_contract.py`, and `tests/static/test_console_catalogue_ownership.py`, driven the
same way the technical spike drove its own headless probes: `prompt_toolkit.output.DummyOutput` +
`prompt_toolkit.input.create_pipe_input`, not a real terminal. Run the full suite with:

```bash
pytest tests/unit/console tests/integration/test_tui_*.py tests/contract tests/static -v
```

Performance validation (Constitution Check row V) runs separately, opt-in, per this repo's existing
convention:

```bash
MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance -v
```
