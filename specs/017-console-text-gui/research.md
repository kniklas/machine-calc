# Research: Console Text GUI (TUI)

**Feature**: `017-console-text-gui` | **Date**: 2026-09-08

The spec has no `[NEEDS CLARIFICATION]` markers, but four implementation-shaping questions were
not (and could not be) answered by the spec alone. This research resolves each with a decision and
rationale, per the standard research.md format.

## 1. TUI framework

**Decision**: prompt-toolkit, as confirmed by the pre-plan technical spike
([spike-tui-framework.md](spike-tui-framework.md)).

**Rationale**: See the spike document for full methodology/numbers. Summary: none of
prompt-toolkit/Textual/urwid was disqualified on memory against Principle V's ~64-128 MB profile;
Textual's dependency weight (~18.7 MB disk, an unrelated markdown/syntax-highlighting stack) isn't
justified by this feature; urwid is leanest/fastest but lower-level; prompt-toolkit's footprint
sits close to urwid's while its higher-level widget/layout/dialog API most directly reduces the
custom code needed for FR-009 (menu), FR-010 (shortcuts), and FR-012 (novice usability).

**Alternatives considered**: Textual (rejected — dependency weight), urwid (documented fallback,
not primary — lower-level API raises implementation risk against FR-012's usability bar).

## 2. Detecting an unsupported terminal (FR-006, FR-008, FR-011)

**Decision**: Check `sys.stdin.isatty()` and `sys.stdout.isatty()` **before** constructing any
prompt-toolkit object, and check terminal size via `shutil.get_terminal_size()` against the 25×80
minimum (FR-011) at the same point. On either check failing, print the FR-006 message (sourced from
the message catalog, per FR-003) to stderr and exit — never construct the `Application`.

**Rationale**: Empirically probed during the spike follow-up: `prompt_toolkit.input.defaults
.create_input()` / `output.defaults.create_output()` do **not** raise when stdin/stdout are piped —
they print a bare, unlocalized `"Warning: Input is not a terminal (fd=0)"` to stderr and silently
fall back to a `PlainTextOutput`, continuing to "run" in a degraded mode. That is exactly the
behavior FR-006 forbids ("MUST NOT... hang silently" and must produce *this project's own*
clear, localized, actionable message, not a library warning). The check therefore cannot be
delegated to the framework's own error handling; it must run first, in application code, as a
precondition.

**Alternatives considered**: Letting `Application.run()` fail naturally and catching the exception
— rejected, since it doesn't reliably raise (see above) and the resulting `PlainTextOutput` session
would violate FR-011's "no scrolling/resizing" and FR-012's usability requirements without ever
tripping an exception handler.

## 3. Splitting `cli.py`'s existing REPL logic

**Decision**: `console/cli.py`'s REPL-only functions (`_prompt_*` families that call `input()`
directly, `_run_drilling_session`, `_run_end_milling_session`, `_run_face_milling_session`,
`_run_milling_session`, `run()`, the REPL's own `_parse_args`) are deleted outright — they have no
survivors, since every one of them is REPL-specific interaction code (FR-001/FR-007). Functions
that only *resolve* data (not prompt for it) — e.g. `_resolve_materials_config`,
`_display_result`'s underlying value-formatting (not its `print()` calls), `_material_type_label`,
`_unique_labels` — are ports, not rewrites: their logic moves into `tui/` (or a small shared helper
module if reused by more than one screen) with prompt-toolkit widgets replacing the `input()`
call sites, not new calculation logic.

**Rationale**: FR-007 requires reusing "REPL-independent calculation-invocation logic" and deleting
"REPL-specific presentation code" — the dividing line is exactly "does this function call `input()`
or `print()` for interactive I/O" vs. "does this function only shape data for display." Keeping the
distinction explicit here (rather than deciding function-by-function during implementation) is what
lets `tasks.md` size the work accurately and lets code review verify FR-007 compliance directly
against this list.

**Alternatives considered**: Keeping `cli.py` monolithic with both old and new code side by side
during a transition period — rejected; FR-001 explicitly requires the REPL "deleted, not merely
hidden," and this repo's history (CHANGELOG's `[Unreleased]` entry for the process-first rename)
already establishes the project's convention of no compatibility shims for pre-1.0/pre-PyPI code.

## 4. Configuration screen scope

**Decision**: The Configuration screen is **read-only** in this feature's v1 scope: it lets a user
view/select the currently-active materials and tools registry (the same data the REPL already
exposed via `--materials-config` and its selection prompts), not author or edit new materials/tools
definitions.

**Rationale**: A PR #94 review comment described the menu item as "Configuration - setup materials,
tools, etc," which read informally could imply new create/edit capability. But the spec's own
Assumptions section is explicit and unambiguous: "**Feature parity, not feature growth, is the v1
scope**... not to introduce new calculations" and FR-002 requires "reaching feature parity with
what the REPL exposed immediately before removal" — the REPL never had an edit/authoring flow for
materials or tools; it only *selected* from an existing TOML-file-backed registry
(`registry_config.py`'s `load_and_merge`, `--materials-config PATH`). Authoring a full create/edit
UI plus a write-back mechanism for that TOML file would be new scope well beyond "un-park the
existing REPL's capability into a full-screen shell," is not covered by any FR/SC in the spec, and
would be a materially larger, separately-plannable feature. Treating "Configuration" as a
view/select screen keeps this plan inside the spec's own stated scope.

**Alternatives considered**: Building create/edit capability now — rejected as scope growth beyond
FR-002/Assumptions with no corresponding FR/SC to test against; flagged here explicitly (rather
than silently narrowed) so the user can request a follow-up feature spec for it if that was the
actual intent.

**Open item for the user**: this is a plan-time interpretation of ambiguous informal feedback, not
a spec-level decision — worth confirming before `/speckit-tasks` locks in the Configuration screen's
scope as read-only.

## 5. Catalogue-ownership static check generalization

**Decision**: `tests/static/test_console_catalogue_ownership.py` currently scans `console/cli.py`
by name for `translate()`/`has_message()` call sites (per its own docstring, check 1/2). It is
generalized to scan every `.py` file directly under `mfgparams/console/` and its subpackages,
excluding `mfgparams/console/locales/` (the catalogues themselves) — i.e. the same "core vs.
console" boundary logic `test_core_does_not_import_console.py` already uses, applied within the
console package to find every module that might call `translate()`.

**Rationale**: The TUI's screens live in a new `console/tui/` subpackage (multiple files), not in
`console/cli.py`. Leaving the ownership check hardcoded to `cli.py` alone would silently stop
enforcing FR-003 (every user-facing string sourced from the catalog) for the module set doing
almost all of this feature's UI work — a regression in coverage, not a neutral no-op.

**Alternatives considered**: Keeping all TUI presentation code physically inside `cli.py` to avoid
touching the static check — rejected; a single-file TUI (menu + 4 screens + framework wiring)
would violate Principle I's single-responsibility guidance and Principle VI's per-screen
extensibility goal for no benefit besides avoiding a test-file edit.
