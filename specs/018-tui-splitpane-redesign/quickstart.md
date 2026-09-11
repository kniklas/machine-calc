# Quickstart: Console TUI Split-Pane Redesign

**Feature**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10

Validation scenarios proving the feature works end-to-end, once implemented per plan.md/tasks.md.
Links to contracts/data-model rather than restating them.

## Prerequisites

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[console,test]"
```

Same as 017 — no new dependency (`prompt-toolkit` already declared under the `console` extra).

## Scenario 1 — Launch and see the persistent shell (User Story 1)

```bash
mfgparams
```

Expected: the menu bar (contract §2) is visible on launch — Exit, Machining, Configuration, About,
Help, in that order, with on-screen mnemonic hints (contract §4). Select Machining; a tree expands
in place showing Milling and Drilling as flat leaves, without a full-screen transition (spec User
Story 1, Acceptance Scenarios 1-2). Select Drilling; its floating operation window opens directly
over the bar/tree (Acceptance Scenario 3 — no further tree-level expansion; FR-003 retired).
Collapse the tree (from the bar, independent of whether a floating window is open); it returns to
collapsed state without losing your place in the menu bar (Acceptance Scenario 4).

## Scenario 2 — Complete a Drilling calculation in one pane (User Story 2)

From Scenario 1's tree, select Drilling's leaf. Expected: a floating window opens over the bar/tree
(FR-004) whose left pane shows every FR-005 field simultaneously — unit system, mode, material type
(see Scenario 5 for the data-driven category set), tool selection, diameter, hole depth, available
power — all editable without a screen transition (Acceptance Scenario 1). Change unit system after
entering a diameter; confirm the diameter value survives, converted, not discarded (Acceptance
Scenario 3, mirroring PR #94's unit-carryover fix). Type a numeric field directly, with no prior
"start editing" keystroke (FR-016); nudge it with Left/Right (FR-017); confirm the typed value only
lands in `session_state` once you navigate away from the field (Up/Down), not on every keystroke.
Navigate onto a radio field (e.g. material type); confirm it is always a single `Label: value` line
(never an expanded option list) and that Left/Right/Space cycles its value with wraparound,
committing it immediately (FR-005, research.md #4).
Compare the eventual right-pane result against calling
`mfgparams.processes.machining.drilling.calculate(...)` directly with the same arguments in a
Python shell — they must match (SC-004).

## Scenario 3 — Live, reactive right pane (User Story 3)

Continuing Scenario 2: confirm the right pane stays empty/placeholder until every required field
holds a value (Acceptance Scenario 1 of User Story 3), then shows a result the instant the last
field completes, with no separate "calculate" action (Acceptance Scenario 2). Change one
already-entered input; confirm the result updates automatically (Acceptance Scenario 3, FR-007).
Run a second calculation without exiting (Acceptance Scenario 4); return to the main menu and
confirm you land back at the menu bar/tree, not a relaunched process (Acceptance Scenario 5).

## Scenario 4 — Error feedback without a blank pane (FR-006a, FR-006b, contract §3)

- Enter a complete set of inputs where one value is out of `calculate()`'s valid range (e.g. an
  engagement value invalid relative to diameter). Expected: the right pane shows the same clear,
  actionable, localized error `calculate()` already returns for it — not a blank pane (FR-006a).
- Type non-numeric text into a numeric field, then navigate away from it (Up/Down). Expected: the
  field keeps editable text while you're still typing, with no message shown yet; once you navigate
  away, the field reverts to its last valid value and a clear, localized message appears in the
  status bar beneath both panes (not the right pane) — the text is never passed to `calculate()`
  (FR-006b).

## Scenario 5 — Tree-collapse never hides a required field (FR-005a, resolved via `/speckit-clarify`)

With Drilling's floating window open (Scenario 2) and the Machining tree still expanded from
getting there, focus the bar and collapse the tree (without closing the floating window). Expected:
the floating window stays open exactly as before — it is not part of the tree's own container
(research.md #3), so collapsing the tree cannot affect it. This is the specific regression FR-005a
guards against; treat any case where a required field becomes unreachable or the window closes here
as a contract violation, not a cosmetic issue.

## Scenario 6 — Data-driven material categories (FR-005)

If a `--materials-config` TOML file registers a category beyond the bundled Metal/Wood (e.g.
Plastic), confirm the left pane's material-type radio includes it without any code change —
`list_material_types()` already returns whatever the active config declares (spec User Story 2).

## Scenario 7 — Non-English locale (unchanged from 017)

```bash
MFGPARAMS_LOCALE=<supported-non-english-locale> mfgparams
```

Expected: every visible label/prompt/error string (including FR-006b's new invalid-number message)
renders in that locale, or falls back to English per the existing rule (FR-011).

## Scenario 8 — No TTY / unsupported terminal (unchanged mechanism, FR-013)

```bash
echo "" | mfgparams
```

Expected: the process exits promptly with a clear, actionable, localized message — never a Python
traceback, never prompt-toolkit's own unlocalized warning, never a silent hang — caught before any
prompt-toolkit object is constructed.

## Scenario 9 — Terminal too small, raised floor (research.md #1, contract §1)

```bash
COLUMNS=40 LINES=25 mfgparams   # below the new 30-row floor, though above 017's old 25
```

Expected: a clear message rather than a garbled/truncated or partially-rendered layout — confirms
the floor was actually raised, not left at 017's value.

## Scenario 10 — Mid-session resize preserves input (FR-013a)

Start entering a Drilling calculation (partially fill the left pane), then resize the terminal
window without completing the calculation. Expected: already-entered, not-yet-submitted values are
still present after the resize — this is the guarantee FR-013a restores for the new persistent
`Application`, verified against `test_tui_resize_preserves_input.py`'s rewritten assertions
(research.md #2's headless-testing adaptation), not assumed from 017's now-superseded per-screen
behavior.

## Automated equivalents

Each scenario above has (or, per plan.md's Project Structure, will have) an automated, headless
counterpart under `tests/integration/test_tui_*.py`, `tests/contract/test_console_tui_contract.py`,
and `tests/static/test_console_catalogue_ownership.py`, driven via `_tui_test_support.py`'s adapted
helper (research.md #2) — `DummyOutput` + pipe input against the one persistent `Application`, not
a real terminal. Run the full suite with:

```bash
pytest tests/unit/console tests/integration/test_tui_*.py tests/contract tests/static -v
```

Performance validation (Constitution Check row V — SC-006's reactive-redraw latency, FR-019's
resource profile) runs separately, opt-in, per this repo's existing convention:

```bash
MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance -v
```
