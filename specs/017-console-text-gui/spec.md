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

**Entry-point precedence (revised from PR #94 review discussion, superseding the note below)**: the
text GUI becomes the **sole** interactive entry point — the REPL is **removed entirely**, not kept
alongside it. This reverses issue #63's explicit "keep REPL" instruction; that reversal is
deliberate, per direct instruction during PR #94's review, and is recorded here rather than left
implicit. Two consequences follow directly and are treated as first-class requirements below, not
afterthoughts:
- **This is a breaking change to `mfgparams`'s public CLI.** Per Constitution Principle IV
  ("Breaking changes to the public API MUST bump the MAJOR version and MUST be documented in a
  changelog before release"), shipping this feature MUST bump the package's MAJOR version and MUST
  be called out in the changelog as removing the REPL entry point.
- **There is no longer a fallback entry point for environments the text GUI cannot run in.** The
  REPL previously served as that fallback (see the now-superseded User Story 3 below); with it
  removed, an unsupported terminal has no interactive alternative left. FR-006/SC-005 are revised
  accordingly: the console MUST fail with a clear, actionable, non-crashing message rather than
  falling back to anything.
- *(Superseded, kept for history)* ~~the text GUI is the default interactive entry point... the REPL
  is retained... as an explicit, scriptable entry point for automation, CI, and power users~~ — this
  intermediate design (text GUI as default, REPL kept for scripting) was recorded during PR #94
  review and is superseded by full REPL removal above.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a calculation from a full-screen text interface (Priority: P1)

As a console user — including one with little computer experience — I want a full-screen,
menu-driven text interface reachable with the keyboard alone (arrow/tab navigation and mnemonic
shortcuts), organized as a small top-level menu (Machining → Milling, Drilling; Configuration;
About; Help), for choosing a manufacturing process/operation, entering its parameters, and reviewing
the result, so that the tool is approachable and readable at a glance rather than requiring
memorized commands — this is now the *only* way to use `mfgparams.console` interactively, so it must
stand on its own rather than merely improve on a line-based alternative.

**Why this priority**: This is the entire substance of the feature; every other story depends on
this one existing. It is also now the *sole* interactive entry point into `mfgparams.console` —
there is no REPL to fall back on if this story is incomplete.

**Independent Test**: Launch the text GUI, complete one full calculation (pick an operation, enter
valid parameters, view the result) using only the keyboard, and confirm the displayed result matches
the value the same inputs produce when the same parameters are passed directly to the underlying
core calculation function (not via the REPL, which no longer exists after this feature ships).

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
4. **Given** the existing REPL entry point, **When** this feature ships, **Then** the REPL is removed
   from `mfgparams.console` entirely and the text GUI is the only interactive entry point; invoking
   the console interactively (e.g. the bare `mfgparams` command) MUST launch the text GUI, not the
   REPL, and any REPL-only code path MUST be deleted rather than left dead in the tree.
5. **Given** the text GUI's top-level menu, **When** the user views it, **Then** it presents exactly
   the structure Machining (→ Milling, Drilling), Configuration, About, and Help, each reachable by
   a visible keyboard shortcut without needing to consult external documentation.

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

### User Story 3 - Fail clearly, not crash, on unsupported terminals (Priority: P3)

As a user running the console on a constrained, scripted, or non-interactive environment (e.g., a
CI job, a dumb terminal, or piped input/output), I want the tool to detect that the text GUI cannot
run and exit with a clear, actionable message instead of crashing, so a terminal that can't support
the text GUI fails predictably rather than with a traceback. **There is no REPL to fall back to** —
this feature removes it entirely (see the "Entry-point precedence" note in Context) — so an
unsupported terminal means the console cannot be used interactively at all until run somewhere
capable; this story is about failing safely, not about recovering an interactive session.

**Why this priority**: Lower priority than the core feature and its i18n parity, but a hard
requirement given Principle V's target of older/constrained environments where not every terminal
emulator supports full-screen rendering, and given that REPL removal means this is now the console's
*only* safety net for such environments — there is no second entry point to catch what this one
misses.

**Independent Test**: Invoke the console's entry point with stdin/stdout piped (no TTY) and confirm
it exits with a clear, actionable, non-zero-or-documented-exit-code message, never an unhandled
exception or traceback, and never a silent hang.

**Acceptance Scenarios**:

1. **Given** no TTY is attached (piped/redirected stdin or stdout), **When** the console is invoked,
   **Then** the process exits promptly with a clear, actionable, localized message explaining that
   an interactive terminal is required — never with an unhandled exception or traceback, and never
   a silent hang.
2. **Given** a terminal that lacks a capability the text GUI requires, **When** the console is
   launched, **Then** the same clear-failure behavior occurs.

---

### Edge Cases

- What happens when the terminal window is resized while the text GUI is running mid-calculation?
  The layout must adapt (or clip gracefully) without losing already-entered input.
- What happens when the terminal window is smaller than the text GUI's minimum usable size (target
  25 rows × 80 columns)? The user must get a clear message rather than a garbled or
  silently-truncated display.
- How does the system handle a locale switch requested *while* the text GUI is already running?
- What happens if the process is killed or the connection drops mid-input? No partial/corrupt state
  should be persisted, since calculations are not yet saved to disk in this feature's scope.
- How does the text GUI behave over a genuinely slow (e.g., legacy serial/SSH) connection where
  full-screen redraws could be visibly slow? At minimum, it must not become unresponsive or drop
  keystrokes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `mfgparams.console` submodule MUST offer a full-screen, keyboard-navigable text
  interface as its **sole** interactive entry point; the existing line-based REPL MUST be removed
  entirely (code deleted, not merely hidden behind a flag). Invoking the console interactively
  (e.g. the bare `mfgparams` command) MUST launch the text GUI.
- **FR-002**: The text GUI MUST let a user select a manufacturing process/operation the REPL exposed
  prior to its removal, enter that operation's required parameters, and view its calculated result
  and any validation/error messages — reaching feature parity with what the REPL exposed
  immediately before removal.
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
  unrecognized/incapable terminal type, or non-interactive/piped invocation), the console MUST exit
  with a clear, actionable, localized message explaining that an interactive terminal is required —
  it MUST NOT crash with an unhandled exception, hang silently, or attempt to fall back to a REPL
  (there is none after this feature ships).
- **FR-007**: The text GUI MUST be delivered inside the existing `mfgparams.console` submodule
  (not a new top-level package) and MUST reuse the submodule's existing i18n infrastructure and any
  REPL-independent calculation-invocation logic rather than duplicating equivalent logic;
  REPL-specific presentation code MUST be deleted, not left dead in the tree.
- **FR-008**: The text GUI MUST degrade gracefully (clear message, not a garbled or silently
  truncated display) when the terminal window is smaller than the interface's minimum usable size,
  and MUST adapt to a terminal resize occurring mid-session without discarding already-entered,
  not-yet-submitted input.
- **FR-009**: The text GUI's top-level navigation MUST be organized as a menu with exactly these
  entries: **Machining** (containing, at minimum, **Milling** and **Drilling**, extensible as core
  gains further processes), **Configuration** (setting up materials, tools, and related reference
  data), **About** (the program), and **Help** (a placeholder in this feature's scope, reachable and
  non-crashing even with no content beyond a stub).
- **FR-010**: Every action reachable from the text GUI MUST be reachable via the keyboard alone,
  using both sequential navigation (arrow keys/Tab) and a direct mnemonic/accelerator shortcut per
  menu item, with the active shortcuts visibly hinted on screen (not requiring the user to memorize
  or look up a command).
- **FR-011**: The text GUI's default/target layout MUST fit within a 25-row × 80-column terminal
  without requiring scrolling or resizing for any top-level menu or single-operation screen; FR-008's
  graceful-degradation behavior applies below that size, not at or above it.
- **FR-012**: The text GUI's navigation and wording MUST be usable by a first-time, non-technical
  user without external documentation — every screen MUST make the next available action (or how to
  go back) visible without requiring the user to already know a command.
- **FR-013**: Removing the REPL is a breaking change to `mfgparams`'s public CLI. Per Constitution
  Principle IV, this feature MUST bump the package's MAJOR version and MUST document the REPL's
  removal in the changelog before release.

### Key Entities

Not applicable — this feature adds a presentation-layer entry point over calculations and
validation results that already exist; it introduces no new persisted data or domain entities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A console user can complete an entire calculation — selecting a process/operation,
  entering parameters, and viewing the result — inside the text GUI using only the keyboard; there
  is no REPL to fall back on, so this is the only way that flow can be completed.
- **SC-002**: The text GUI remains responsive (perceived input-to-screen-update delay under
  approximately 200 ms) when exercised on hardware meeting the Principle V legacy-hardware profile.
- **SC-003**: 100% of the strings the text GUI displays are resolvable through the console's
  existing message-catalog mechanism; zero strings are hardcoded in the UI layer, verified by
  review/audit at merge time.
- **SC-004**: 100% of the console's existing tests that exercise REPL-independent behavior
  (calculation logic, i18n, validation) continue to pass unmodified after the REPL is removed and
  the text GUI takes over; REPL-specific tests are removed along with the REPL code they tested,
  not left failing or skipped.
- **SC-005**: When invoked with no TTY attached (piped/redirected input or output), the console
  exits with a clear, actionable message in 100% of tested cases, with no unhandled exception and no
  silent hang.
- **SC-006**: A first-time user given no instructions beyond "run the console" can locate and start
  a Milling calculation from the top-level menu, and can locate Help, within a small, fixed number
  of keystrokes/menu selections determined during usability review — verified by an informal
  walkthrough with a non-technical reviewer before this feature ships.
- **SC-007**: The text GUI's default screens (top-level menu and each single-operation screen)
  render fully within a 25×80 terminal with no scrolling required, verified by manual/automated
  check at the target size during implementation.

## Assumptions

- **Framework selection: prompt-toolkit, confirmed by spike.** The technical spike recommended
  below has been run (see [spike-tui-framework.md](spike-tui-framework.md)); prompt-toolkit was not
  disqualified and is the confirmed choice for `/speckit-plan` to carry forward, with urwid as the
  documented fallback if a disqualifying finding surfaces later.
- **Feature parity, not feature growth, is the v1 scope.** The text GUI is assumed to cover every
  process/operation the REPL already exposes at ship time, not to introduce new calculations —
  consistent with Principle VI's per-operation interface, which any UI layer built against it can
  drive uniformly without operation-specific glue.
- **The REPL is removed, not kept.** This deliberately reverses issue #63's "keep REPL" instruction
  (per direct instruction during PR #94 review); the text GUI becomes the sole interactive entry
  point. There is no scripting/automation entry point into `mfgparams.console` after this feature
  ships — a future need for one would be a new, separate feature, not part of this spec's scope.
  This is a breaking CLI change; see FR-013 and Principle IV.
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
- **Spike completed 2026-09-08 — prompt-toolkit is confirmed.** See
  [spike-tui-framework.md](spike-tui-framework.md) for full methodology and results. Summary:
  prompt-toolkit (~6.2 MB disk, ~25.7 MB minimal-screen peak RSS, 1 transitive dependency),
  Textual (~18.7 MB disk — driven by an unrelated markdown/syntax-highlighting stack, ~27.4 MB
  peak RSS, 8 transitive dependencies), and urwid (~5.9 MB disk, ~20.8 MB peak RSS, 2 transitive
  dependencies) were all installed and probed under Python 3.9.0 (this project's floor). None was
  disqualified on memory — all comfortably fit Principle V's ~64-128 MB target with headroom.
  Textual's dependency weight is unjustified by this feature's needs and is not recommended; urwid
  is leanest/fastest but lower-level, requiring more custom widget work to meet FR-009/FR-010/
  FR-012's menu/shortcut/novice-usability bar; prompt-toolkit's footprint is close to urwid's while
  its higher-level widget/layout API most directly supports those requirements. `/speckit-plan`
  MUST treat prompt-toolkit as the selected framework unless it surfaces a concrete disqualifying
  finding of its own (per the original "if the spike disqualifies prompt-toolkit" fallback below).
- **If `/speckit-plan` or implementation surfaces a disqualifying finding not caught by this
  spike** (e.g. an actual legacy-hardware/terminal incompatibility), it should record that finding
  and fall back to urwid (the next-leanest, already-probed alternative) rather than defaulting
  silently or re-running the full comparison from scratch.
