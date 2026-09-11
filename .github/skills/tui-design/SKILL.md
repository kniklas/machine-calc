---
name: tui-design
description: Design-before-build checklist for console/TUI screens in mfgparams (prompt-toolkit code under src/mfgparams/console/tui/**) — reuse the shared style classes instead of inventing new colors per screen, and for any net-new UI region with no exact prototype to copy, write down a palette/layout/interaction contract and get it confirmed before implementing. Use when adding or changing a TUI screen, dialog, dropdown, menu, or any other visual/interactive console surface.
---

# TUI Design (mfgparams)

Use whenever a PR adds or changes a screen, dialog, dropdown, floating
window, or other visual/interactive surface under
`src/mfgparams/console/tui/**`.

## Why this exists

specs/018-tui-splitpane-redesign (PR #96) needed two full implementation
passes rejected outright, then 8 further user-reported correction rounds
after a third rewrite was already marked "done" — see the retrospective at
[PR #96, comment](https://github.com/kniklas/mfgparams/pull/96#issuecomment-5637032822).
Root cause #1 there (a claimed-lost prototype never checked against the
filesystem) and the missing manual-QA gate (root cause #6) are covered by
Constitution **Principle XIII** (added by
[PR #98](https://github.com/kniklas/mfgparams/pull/98); check
`.specify/memory/constitution.md` directly if that PR hasn't merged yet —
don't assume the principle number below is already ratified). Root cause
#3 is not:

> The chrome around the prototype was never specified, only reacted to...
> designed live, turn-by-turn, in response to a stream of small
> corrections, rather than agreed up front as a single design.

The menu bar, dropdowns, background, shadow, and Exit dialog in that
feature had no prototype to copy — so they were invented one correction at
a time (color scheme → different bar color → dropdown submenus → divider/
highlight/shading → color unification → a focus bug from one of the
earlier fixes), at a total cost far higher than one consolidated design
pass. This skill is that missing pass. It doesn't replace Principle XIII's
manual-verification task (PR #98) — the design contract below is what the
manual walkthrough checks the built feature *against*; Principle XIII
checks that someone actually looked.

## 1. Read the actual reference — don't re-derive it from memory or prose

Before designing anything, confirm whether an exact reference already
exists (a prototype script, an earlier screen doing the same kind of
thing, a mockup) and read its literal source. This is Principle XIII's
second bullet, restated as the first step here because skipping it is what
caused two of the three implementation rewrites in #96: a claim that the
prototype was "discarded" was carried forward across two passes without
ever running `find`/`ls` against the path it actually named. If a
reference exists, cite/link its real content in the spec — a re-derived
paraphrase is not an equivalent substitute for having read it.

## 2. Reuse the existing shared style — don't invent a new one per screen

Every floating window, the persistent bar, and the desktop background in
this codebase currently share **one** `Style.from_dict({...})` call in
`src/mfgparams/console/tui/app.py` (search for `Style.from_dict` if this
has moved). That consolidation itself was a direct-user-feedback fix in
#96 ("milling and drilling floating windows ... should follow the same
colour scheme as sub-menu drop downs") — don't reintroduce the fragmentation
it corrected by adding a second `Style` object in a new module. Current
classes and their semantic role (verify against the actual dict — this
list is a pointer, not a copy that can drift):

| Class | Role |
|---|---|
| `mnemonic` | An accelerator character within a label |
| `selected` | The currently-focused/highlighted item in a list |
| `hint` | Secondary/de-emphasized text |
| `error` | Validation/error text |
| `pane-title` | A section heading within a pane |
| `background` | The desktop behind the bar and any floating window |
| `bar` | The persistent menu bar row |
| `dialog` | The outer `Box` margin around the **centered operation window only** — the bar-entry dropdowns and the Exit dialog deliberately skip `Box` for a snugger fit and don't use this class |
| `dialog.body` / `frame.border` / `frame.label` | `Frame`'s body/border/title, shared by every floating window (dropdowns, Exit dialog, and the operation window alike) |
| `shadow` | The drop-shadow under a floating window |

For a new UI element, map it to the existing class that already owns its
visual role: a new dropdown/panel-style float → `dialog.body`/
`frame.border`/`shadow` only (no `Box`, so no `dialog`, matching the
dropdowns/Exit dialog above); a new centered/boxed window like the
operation screen → add `dialog` too. Don't apply `dialog` to a dropdown —
that would reintroduce the `Box` margin the existing dropdowns
deliberately skip. Only add a new class when no existing one fits the
role — and when you do, add it to this same dict and say why in the PR
description, rather than starting a second one.

## 3. Write a design contract before implementing a net-new region

If step 1 found no exact reference to copy for some part of the surface
(true of the bar/dropdown/dialog chrome in #96), write down — in
`research.md` or `plan.md`, before `/speckit-implement` — a short contract
covering the parts prose tends to lose:

- **Palette** — any new class from step 2, its `prompt_toolkit` style
  string, and why no existing class covers the role.
- **Layout** — where the region sits relative to the persistent bar/panes
  (position, size/proportions, minimum terminal size it assumes).
- **Interaction** — what `Tab`/`Escape`/arrow keys/`Enter` do inside it;
  what regains focus when it opens and when it closes (#96's "press Down
  twice" bug and the Escape-refocus rework both trace back to this being
  undecided until a user hit it); if the region is reachable from more
  than one path (e.g. a collapsible tree shortcut *and* a direct pane),
  say so explicitly and confirm both paths are meant to coexist — #96 had
  a live requirements reversal here (FR-003/FR-005a) that a one-line
  ambiguity note up front would have caught before implementation, not
  after. If the region adds a new menu/tree entry or dropdown item, this
  table also assigns its mnemonic (reusing `menu.py`'s `_assign_mnemonics`
  logic) and confirms it's visibly hinted and pairwise-distinct within its
  own level — every menu in this codebase MUST satisfy this
  (`specs/017-console-text-gui/contracts/console-tui-contract.md` §2/§3,
  `specs/018-tui-splitpane-redesign/contracts/console-tui-splitpane-contract.md`
  §2), enforced by `tests/contract/test_console_tui_contract.py`; a design
  that only specifies sequential-key navigation and skips this is
  incomplete.

Keep it to a table per concern, not prose — the goal is something a
30-second read confirms or corrects, not a design document.

## 4. Get the contract confirmed before writing the implementation

Show the palette/layout/interaction contract (a quick ASCII sketch of the
layout is enough) to the user and get explicit confirmation before
implementing a net-new region. A cheap confirmation pass here is what the
#96 retrospective is arguing is far less costly than the rewrite rounds
that happened without one. Implementing first and collecting corrections
afterward is the exact pattern this skill exists to avoid.
