# Contract: Console Text GUI Entry Point, Menu Structure & Message Ownership

**Feature**: `017-console-text-gui` | **Date**: 2026-09-08

Mirrors this repo's existing contract style (e.g. `specs/014-process-namespaces-extras/contracts/
console-entry-contract.md`, `specs/015-console-i18n-relocation`'s catalogue-ownership contract):
a durable, test-enforced statement of the interface this feature exposes, not narrative
documentation.

## 1. Entry points

| Invocation | Behavior after this feature |
|---|---|
| `mfgparams` (console script) | Launches the text GUI. No REPL exists to launch instead (FR-001). |
| `python -m mfgparams` | Same — delegates to `mfgparams.__main__.main`, unchanged wiring. |
| `python -m mfgparams.console` | Same — delegates to `mfgparams.__main__.main`, unchanged wiring. |
| `mfgparams[console]` not installed | Unchanged FR-011 behavior: a clear, localized, catalog-sourced message naming the exact install command (`mfgparams/__main__.py`'s existing guard, generic over whatever the `console` extra declares — no code change required there). |
| No TTY / terminal too small (<25×80) | Exits with a clear, localized, catalog-sourced message (FR-006/FR-008/FR-011) and a non-zero, documented exit status — **before** any prompt-toolkit `Application` is constructed (research.md #2). Never a REPL fallback. |

## 2. Menu structure (FR-009) — closed set, exact wording sourced from the catalog

```
Top-level menu
├── Machining          (mnemonic: configurable per locale, English default "m")
│   ├── Milling
│   └── Drilling
├── Configuration       (read-only view/select — research.md #4)
├── About
└── Help                (placeholder content, still reachable and non-crashing)
```

**Invariant**: this set is exact — "Machining", "Configuration", "About", "Help" at the top level;
"Milling", "Drilling" under Machining. Adding a future operation (e.g. Turning, per Constitution
Principle VI) adds a new entry under Machining; it does not restructure the other three top-level
entries. Enforced by `tests/contract/test_console_tui_contract.py`.

**Invariant**: every menu's mnemonics are pairwise distinct within that menu (data-model.md's
`MenuEntry` validation rule). Enforced by the same contract test.

## 3. Keyboard contract (FR-010)

- Every screen MUST be reachable by sequential navigation (arrow keys and/or Tab) alone, with no
  mnemonic required.
- Every menu entry additionally has a direct mnemonic/accelerator key, visibly hinted on-screen
  (rendered as part of the label, e.g. underlined or bracketed per prompt-toolkit's own convention
  — a presentation detail for `tasks.md`, not fixed here).
- A "go back" action (e.g. `Escape` or `Backspace`) is available on every non-`MENU` screen,
  popping `NavigationState.screen_stack` (data-model.md).
- No mouse/pointer interaction is required for any action (spec Assumptions: "Keyboard-only
  interaction").

## 4. Message-catalog ownership (FR-003, extends 015's catalogue-ownership contract)

- Every new message key introduced by this feature is namespaced `tui.*` (parallel to the REPL's
  existing `cli.*` namespace, which is retired alongside the REPL code that used it — dead keys
  MUST be removed from `locales/en.py`, not left orphaned).
- `tests/static/test_console_catalogue_ownership.py` is generalized (research.md #5) to scan every
  `.py` file under `mfgparams/console/` (all subpackages, including the new `tui/`), excluding
  `mfgparams/console/locales/` itself, for `translate()`/`has_message()` call sites — not just
  `console/cli.py`.
- The FR-006 no-TTY/too-small-terminal message and the FR-011 (existing, unrelated) missing-extra
  message remain **owned by core's catalog** (`mfgparams.i18n`/`mfgparams.locales`), not the
  console's — same reasoning `console.missing_dependency*`'s existing placement already
  establishes: a message whose whole purpose is to say the console/text-GUI is unavailable cannot
  depend on the console's own catalog machinery having initialized successfully.

## 5. Feature-parity contract (FR-002)

Every process/operation the REPL exposed immediately before its removal MUST have an equivalent
text-GUI screen reachable from the menu structure in §2, calling the same core function with the
same parameter set. At the time this plan was written, that means: Drilling (one form) and Milling
(end milling and face milling, as the REPL's existing `_prompt_milling_sub_operation` sub-operation
choice — data-model.md's `OperationForm` for Milling covers both under one screen with a
sub-operation selector, mirroring the REPL's own structure rather than inventing a new one).

## 6. Versioning contract (FR-013)

- `src/mfgparams/__init__.py`'s `__version__` MUST read `"2.0.0"` in the commit that removes the
  REPL (single source of truth, Constitution Principle IV — no other file hardcodes the version).
- `CHANGELOG.md`'s `[Unreleased]` section MUST gain an entry under a `### Removed` (or `### Changed`
  if grouped with other breaking changes already there) heading stating that the REPL entry point
  is removed and the text GUI is now the sole interactive entry point, consistent with the
  formatting of the existing process-first-rename entry already in that section.
