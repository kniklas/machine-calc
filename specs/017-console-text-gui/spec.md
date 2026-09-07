# Feature Specification: Console Text GUI (TUI)

**Feature Branch**: `017-console-text-gui`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Implement a simple text GUI (TUI) for text terminals as part of the
mfgparams.console submodule, alongside the existing REPL. This unparks the 'text-base UI' item
from issue #63. Requirements must satisfy Constitution Principle V (resource-constrained
compatibility), Principle VIII (internationalization), and Principle I (code quality). Candidate
framework to evaluate first: prompt-toolkit — recommended for its lower resource footprint versus
full-screen TUI frameworks, cross-platform portability, built-in Unicode/multi-language rendering,
and maintainability — but the spec should not commit to it outright; a short technical spike
comparing it against alternatives is a recommended next step before /speckit-plan."

## Context

[Issue #63](https://github.com/kniklas/mfgparams/issues/63) ("change repository and package
structure") asked for `mfgparams.console` to eventually hold "REPL and text-base UI"; it explicitly
said to **keep REPL** and **park text-base UI for later**. [Slice 1 of that issue
(014)](../014-process-namespaces-extras/spec.md) delivered the `console` optional-dependency extra
but left it declared empty ("[the console] needs nothing beyond the standard library today... The
`[console]` extra buys nothing until [a TUI framework] arrives" — PR #63 review discussion). This
feature is the first slice that actually populates that extra: it un-parks the text-UI item.

This spec deliberately does **not** select a final UI framework. It documents the requirement, the
constitutional constraints any candidate must satisfy, and a leading candidate (prompt-toolkit) for
evaluation — recommending a short technical spike against the legacy-hardware profile before
`/speckit-plan` commits to one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a calculation from a full-screen text interface (Priority: P1)

As a console user, I want a full-screen, keyboard-navigable text interface — not just the
line-by-line REPL — for choosing a manufacturing process/operation, entering its parameters, and
reviewing the result, so that entering parameters and reading results is less error-prone than
typing and re-typing REPL commands, especially over a slow or remote terminal connection.

**Why this priority**: This is the entire substance of the feature; every other story depends on
this one existing.

**Independent Test**: Launch the text GUI, complete one full calculation (pick an operation, enter
valid parameters, view the result) using only the keyboard, and confirm the displayed result
matches the value the same inputs produce through the existing REPL.

**Acceptance Scenarios**:

1. **Given** the console's text-GUI entry point is launched in a supported terminal, **When** a
   user selects a process/operation and enters valid parameters, **Then** the calculated result is
   displayed on screen without the user needing to leave the text GUI.
2. **Given** the user is in the text GUI, **When** they enter an invalid parameter (out of range,
   wrong type, missing required field), **Then** a clear, actionable validation message is shown
   in-place, in the user's configured language, and the user can correct the input without
   restarting.
3. **Given** the user has completed one calculation, **When** they choose to start another,
   **Then** they can do so without exiting and relaunching the text GUI.
4. **Given** the existing REPL entry point, **When** this feature ships, **Then** the REPL continues
   to work exactly as before — the text GUI is an additional entry point, not a replacement.

---

### User Story 2 - Use the text GUI in the configured language (Priority: P2)

As a console user who runs the tool in a non-English locale, I want every label, prompt, help
string, and error/validation message in the text GUI to appear in my configured language (falling
back to English where a translation is missing), so the text GUI is exactly as usable as the
existing REPL for non-English speakers.

**Why this priority**: Principle VIII (Internationalization) is a non-negotiable constitutional
requirement for all user-facing console output; a text GUI that hardcodes English strings would be
a regression against work already completed for the REPL (015-console-i18n-relocation).

**Independent Test**: Switch the console's active locale to a supported non-English language,
launch the text GUI, and confirm every visible string (including a deliberately-triggered
validation error) renders in that language or falls back to English per the existing rule.

**Acceptance Scenarios**:

1. **Given** a supported non-English locale is active, **When** the text GUI is launched, **Then**
   all static labels/help text appear in that locale.
2. **Given** a supported non-English locale is active, **When** a validation error is triggered,
   **Then** the error message appears in that locale using the existing message-catalog mechanism,
   not a hardcoded English string.
3. **Given** a message key has no translation for the active locale, **When** that message is
   shown, **Then** the English fallback is displayed rather than a blank or broken string.

---

### User Story 3 - Fall back gracefully on unsupported terminals (Priority: P3)

As a user running the console on a constrained, scripted, or non-interactive environment (e.g., a
CI job, a dumb terminal, or piped input/output), I want the tool to detect that the text GUI cannot
run and fall back to the existing REPL (or a clear message) instead of crashing, so automation and
low-capability terminals are never broken by this feature.

**Why this priority**: Lower priority than the core feature and its i18n parity, but a hard
requirement given Principle V's target of older/constrained environments where not every terminal
emulator supports full-screen rendering.

**Independent Test**: Invoke the console's text-GUI entry point with stdin/stdout piped (no TTY)
and confirm it falls back to the REPL or prints a clear, actionable message, with a non-crashing
exit.

**Acceptance Scenarios**:

1. **Given** no TTY is attached (piped/redirected stdin or stdout), **When** the text-GUI entry
   point is invoked, **Then** the process falls back to the REPL or exits with a clear message,
   never with an unhandled exception or traceback.
2. **Given** a terminal that lacks a capability the text GUI requires, **When** the text GUI is
   launched, **Then** the same graceful fallback occurs.

---

### Edge Cases

- What happens when the terminal window is resized while the text GUI is running mid-calculation?
  The layout must adapt (or clip gracefully) without losing already-entered input.
- What happens when the terminal window is smaller than the text GUI's minimum usable size? The
  user must get a clear message rather than a garbled or silently-truncated display.
- How does the system handle a locale switch requested *while* the text GUI is already running?
- What happens if the process is killed or the connection drops mid-input? No partial/corrupt state
  should be persisted, since calculations are not yet saved to disk in this feature's scope.
- How does the text GUI behave over a genuinely slow (e.g., legacy serial/SSH) connection where
  full-screen redraws could be visibly slow? At minimum, it must not become unresponsive or drop
  keystrokes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `mfgparams.console` submodule MUST offer a full-screen, keyboard-navigable text
  interface as an additional entry point alongside the existing line-based REPL, without removing,
  replacing, or changing the behavior of the REPL.
- **FR-002**: The text GUI MUST let a user select a manufacturing process/operation already exposed
  by the REPL, enter that operation's required parameters, and view its calculated result and any
  validation/error messages — reaching feature parity with what the REPL already exposes at the
  time this feature ships.
- **FR-003**: Every user-facing string the text GUI displays (labels, prompts, help text,
  validation/error messages) MUST be sourced from the console's existing message-catalog/locale
  mechanism (`src/mfgparams/console/i18n.py`, `src/mfgparams/console/locales/`) per Constitution
  Principle VIII; the text GUI MUST NOT introduce a second, parallel translation mechanism or any
  hardcoded English string in its UI layer.
- **FR-004**: The text GUI MUST operate within the legacy-hardware profile defined in Constitution
  Principle V (approximately 64-128 MB RAM, single-threaded CPU, minimal clock speeds) and MUST
  remain compatible with the older/long-term-stable OS releases that profile targets.
- **FR-005**: Any new runtime dependency the text GUI requires MUST be declared under the existing
  `console` optional-dependency extra (`pyproject.toml`), so that installing only the core library
  (`pip install mfgparams`) continues to pull in none of it.
- **FR-006**: When the runtime terminal environment cannot support the text GUI (no TTY, an
  unrecognized/incapable terminal type, or non-interactive/piped invocation), the console MUST fall
  back to the existing REPL or report a clear, actionable message — it MUST NOT crash with an
  unhandled exception.
- **FR-007**: The text GUI MUST be delivered inside the existing `mfgparams.console` submodule
  (not a new top-level package) and MUST reuse the submodule's existing REPL/i18n infrastructure
  rather than duplicating equivalent logic.
- **FR-008**: The text GUI MUST degrade gracefully (clear message, not a garbled or silently
  truncated display) when the terminal window is smaller than the interface's minimum usable size,
  and MUST adapt to a terminal resize occurring mid-session without discarding already-entered,
  not-yet-submitted input.

### Key Entities

Not applicable — this feature adds a presentation-layer entry point over calculations and
validation results that already exist; it introduces no new persisted data or domain entities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A console user can complete an entire calculation — selecting a process/operation,
  entering parameters, and viewing the result — inside the text GUI using only the keyboard,
  without needing the line-based REPL.
- **SC-002**: The text GUI remains responsive (perceived input-to-screen-update delay under
  approximately 200 ms) when exercised on hardware meeting the Principle V legacy-hardware profile.
- **SC-003**: 100% of the strings the text GUI displays are resolvable through the console's
  existing message-catalog mechanism; zero strings are hardcoded in the UI layer, verified by
  review/audit at merge time.
- **SC-004**: 100% of the console's existing REPL tests continue to pass unmodified after the text
  GUI is added — the feature is additive, not a regression.
- **SC-005**: When invoked with no TTY attached (piped/redirected input or output), the console
  falls back to the REPL or a clear message in 100% of tested cases, with no unhandled exception.

## Assumptions

- **Framework selection is deferred, not decided by this spec.** prompt-toolkit is documented below
  as the leading candidate, but no framework is committed to here; `/speckit-plan` MUST record the
  outcome of the technology-evaluation next step (below) before implementation begins.
- **Feature parity, not feature growth, is the v1 scope.** The text GUI is assumed to cover every
  process/operation the REPL already exposes at ship time, not to introduce new calculations —
  consistent with Principle VI's per-operation interface, which any UI layer built against it can
  drive uniformly without operation-specific glue.
- **The REPL is permanent, not a stepping stone.** Per issue #63's explicit "keep REPL" instruction,
  this feature adds a second entry point; it does not deprecate or plan to remove the REPL.
- **Keyboard-only interaction.** Mouse/pointer support is out of scope, consistent with targeting
  minimal/legacy terminals and keeping the dependency footprint small.
- **No new persistence.** The text GUI reads/displays calculation results already computed by
  existing core logic; it does not introduce saving/loading of sessions or results to disk.
- **Single active locale per session**, matching the REPL's existing behavior — switching languages
  requires restarting the text GUI, unless a candidate framework makes live-switching trivial
  enough to reconsider during planning.

## Technology Candidates & Recommended Next Steps

- **Leading candidate: prompt-toolkit.** Suggested because, relative to full-screen TUI frameworks
  generally, it is reported to offer a lower resource footprint (relevant to Principle V's ~64-128
  MB/single-threaded-CPU target), cross-platform portability across Windows/Linux/macOS terminals
  (relevant to Principle V's OS-compatibility requirement), built-in Unicode rendering that eases
  multi-language display (relevant to Principle VIII), and a comparatively simple API surface
  (relevant to Principle I's maintainability requirement).
- **This has not been verified against this project's actual constraints.** No TUI library has been
  benchmarked in this repository, and the `console` extra has shipped empty since 014
  specifically because nothing has been evaluated yet.
- **Recommended next step before `/speckit-plan`**: run a short, time-boxed technical spike that
  installs prompt-toolkit (and, for comparison, at least one full-screen alternative such as
  Textual, and at least one minimal-dependency alternative such as urwid or blessed) and measures,
  on hardware representative of the Principle V profile:
  1. Idle and active RSS memory footprint.
  2. Cold-start time and input-to-redraw latency.
  3. Behavior on the older/long-term-stable OS release(s) this project targets (e.g., an old Debian
     stable install) — including whether the library's own dependency chain (e.g., `wcwidth`,
     terminal-capability detection libraries) is itself compatible with that target.
  4. Practical ease of wiring the existing message-catalog mechanism into the framework's widgets
     (Principle VIII) without a parallel i18n layer.
- **If the spike disqualifies prompt-toolkit** (e.g., it cannot meet the memory/CPU profile on the
  target OS), `/speckit-plan` should record the disqualifying measurement and select from the
  alternatives evaluated in the same spike, rather than defaulting silently.
- **If no in-repo spike is performed**, `/speckit-plan` MUST at minimum document the chosen
  framework's published resource-footprint claims and how they were checked against Principle V
  before committing to it in the plan, per Principle V's "flagged during planning... with an
  explicit trade-off note" requirement.
