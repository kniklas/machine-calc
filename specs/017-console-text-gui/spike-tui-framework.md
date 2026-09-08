# Technical Spike: TUI Framework Comparison

**Feature**: `017-console-text-gui` | **Date**: 2026-09-08

Runs the technical spike `spec.md`'s "Technology Candidates & Recommended Next Steps" section
called for before `/speckit-plan`: compare prompt-toolkit against a full-screen alternative
(Textual) and a minimal-dependency alternative (urwid) against Constitution Principle V's
~64-128 MB/single-threaded-CPU legacy-hardware profile.

## Methodology

Each candidate was installed in its own isolated virtualenv (`venv-prompt-toolkit`,
`venv-textual`, `venv-urwid`) under Python 3.9.0 — this project's `requires-python` floor
(`pyproject.toml`) and a reasonable proxy for an older/long-term-stable OS's default interpreter.
All three installed and ran without incident under 3.9.0.

Memory was measured as the **absolute peak RSS of a freshly-started child process**
(`resource.getrusage(...).ru_maxrss`), matching the method already used by this repo's
`tests/performance/harness.py` for the same reason documented there: a before/after delta within
one long-lived process is unreliable because `ru_maxrss` is monotonically non-decreasing, so a
small measurement can invisibly ride on an already-high baseline. Each figure below is the median
of 3 runs. A bare `import os` process (no framework) was measured as the interpreter-only
baseline (~8.45 MB) for context.

Two probes were run per candidate:
1. **Cold import** — `import <package>` only.
2. **Minimal menu screen** — construct and headlessly render one frame of a screen shaped like
   this spec's actual FR-009 menu (Machining, Configuration, About, Help), using each framework's
   own headless-testing mechanism: prompt-toolkit's `DummyOutput` + `create_pipe_input`,
   Textual's built-in `App.run_test()` pilot, and (since urwid has no built-in headless harness) a
   direct `widget.render((80, 25))` call — the closest equivalent without vendoring a fake
   `Screen`.

A third check fed each candidate a mixed Polish-diacritic + arrow + CJK string
(`"Frezowanie → Wiercenie / 钻孔作业"`) through its normal text/label path to sanity-check
Unicode/wide-character handling relevant to Principle VIII.

**Limitations** (documented, not silently assumed away): measured on a macOS development machine,
not the actual ~64-128 MB legacy-hardware target — absolute numbers are directional, not a
guarantee for that hardware. Single-core CPU pinning (`os.sched_setaffinity`) is unavailable on
macOS, the same limitation `tests/performance/harness.py`'s own research.md records for its
suite, so no candidate was measured under actual single-core contention. Real full-screen
redraw/input latency over an interactive TTY was not measured — only construction + one headless
render pass, which is a proxy for startup cost, not sustained interaction latency.

## Results

| Metric | prompt-toolkit 3.0.52 | Textual 8.2.8 | urwid 4.1.2 |
|---|---|---|---|
| Direct + transitive runtime deps | 1 (`wcwidth`) | 8 (`rich`, `pygments`, `markdown-it-py`, `mdit-py-plugins`, `linkify-it-py`, `mdurl`, `uc-micro-py`, `platformdirs`, `typing-extensions`) | 2 (`wcwidth`, `typing-extensions`) |
| On-disk install size (excl. pip/setuptools) | ~6.2 MB | ~18.7 MB | ~5.9 MB |
| Cold-import peak RSS (median of 3) | ~23.4 MB | ~25.3 MB | ~20.8 MB |
| Minimal-menu-screen peak RSS (median of 3) | ~25.7 MB | ~27.4 MB | ~20.8 MB |
| Full process wall time, cold start (median of 3) | ~0.38 s | ~0.43 s | ~0.19 s |
| Runs under Python 3.9.0 (project floor) | Yes | Yes | Yes |
| Unicode/wide-char smoke test (Polish + CJK label) | Pass | Pass | Pass |

(Interpreter-only baseline for reference: ~8.45 MB peak RSS.)

## Analysis

- **None of the three candidates is disqualified by memory.** Even Textual's ~27.4 MB
  minimal-screen figure leaves large headroom under Principle V's ~64-128 MB target once actual
  application code (materials/tools registries, calculation modules, i18n catalogs) is added —
  this spike did not find a hard blocker on the memory axis for any candidate.
- **Textual is the clear outlier on dependency weight and disk footprint** (~18.7 MB, roughly 3x
  the other two), driven almost entirely by a Markdown-rendering/syntax-highlighting stack
  (`rich` + `markdown-it-py` + `pygments`, the last alone ~8.5 MB on disk) that this feature has no
  use for — a menu-driven parameter-entry screen needs none of it. Per Principle V ("any
  dependency with a non-trivial memory footprint MUST be justified") and Principle I
  (maintainability/no unnecessary complexity), pulling in an unrelated markdown/syntax-highlighting
  stack for this feature is hard to justify. Textual was also consistently the slowest to cold-start
  (~0.43 s vs. ~0.19-0.38 s) and heaviest on every RSS measurement.
- **urwid is the leanest and fastest candidate** on every measured axis (RSS, disk, cold-start
  time) — consistent with it being the "minimal-dependency alternative" the spec named it as. It is
  a lower-level, older-style widget toolkit, though: it has no built-in headless-testing harness
  (this spike had to fall back to a raw `render()` call), and reaching the discoverable,
  keyboard-shortcut-hinted, novice-friendly menu/dialog UX this spec's FR-009-FR-012 call for would
  require more custom widget-composition work than a toolkit with built-in dialog/menu widgets.
- **prompt-toolkit sits close to urwid on footprint** (~6.2 MB vs. ~5.9 MB disk, ~25.7 MB vs.
  ~20.8 MB minimal-screen RSS — both comfortably lean) while offering a more complete,
  actively-developed layout/key-binding/widgets API (built-in dialogs, radio-lists, buttons) better
  suited to building the specific menu-driven, keyboard-shortcut-hinted, first-time-user-friendly
  interface FR-009-FR-012 specify, with correspondingly less custom code to build and maintain.

## Recommendation

**prompt-toolkit is confirmed as the framework choice for `/speckit-plan`.** The spike does not
disqualify it — its footprint is close to urwid's (the leanest candidate) and far below Textual's,
while its higher-level widget/layout API most directly reduces the custom code needed to satisfy
FR-009 (menu structure), FR-010 (keyboard shortcuts), and FR-012 (novice usability) without pulling
in Textual's unrelated markdown/syntax-highlighting dependency weight. Textual is not recommended
for this feature's scope, given its disk/dependency footprint is unjustified by anything this
feature needs. urwid remains a credible lighter-weight fallback if `/speckit-plan` or later
implementation surfaces a concrete reason prompt-toolkit doesn't work out (e.g. an unexpected
legacy-terminal incompatibility), but is not the primary recommendation given the added
implementation effort its lower-level API would require to meet the usability bar.

## Spike artifacts

Probe scripts and raw output are not committed to this repository (ephemeral, session-scratch
only); the tables above are the durable record. Anyone wanting to reproduce: create isolated
virtualenvs for `prompt_toolkit`, `textual`, and `urwid` under Python 3.9, then measure
`resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` in a fresh child process immediately after
import (and again after constructing/rendering a representative screen), per the methodology
above.
