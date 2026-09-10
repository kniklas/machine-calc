# Phase 1 Data Model: Console TUI Split-Pane Redesign

**Feature**: `018-tui-splitpane-redesign` | **Date**: 2026-09-10

Entities extracted from spec.md's Key Entities section plus the session-state objects FR-012
requires be reused unchanged. This feature introduces new *UI-state* entities (how the screen is
structured and navigated) but no new *domain* entities — no calculation, material, or tool concept
changes (spec Assumptions, SC-004).

## Reused unchanged (FR-012) — not redefined here

- **`DrillingSessionState`** (`screens/drilling.py`): `unit_system`, `material_type`, `material`,
  `tool`, `diameter`, `depth`, `available_power`, `mode`, `target_rpm`, `previous_mode`. Field
  semantics and default-carryover-across-visits behavior (including PR #94's mode-switch and
  unit-system-switch fixes) are unchanged; only how the fields are *presented* changes.
- **`MillingSessionState`** (`screens/milling.py`): `unit_system`, `material_type`, `material`,
  `tool`, `diameter`, `axial_depth_of_cut`, `radial_engagement`, `feed_per_tooth`,
  `number_of_teeth`, `length_of_cut`, `available_power`, `mode`, `target_rpm`, `previous_mode`.
  Same unchanged-semantics guarantee. `tool`'s registry (end-mill vs. face-mill) and
  `radial_engagement`'s label ("Radial depth of cut" vs. "Width of cut") depend on the sub-operation
  choice (FR-009a), exactly as PR #94 already implements.
- **`CalculationResult`**/**`ErrorInfo`** (`mfgparams.models`): unchanged; FR-006a/FR-006b depend on
  `ErrorInfo`'s existing shape and `forms.format_result()`'s existing rendering of it.

## New: UI-state entities

### `MenuBar`

The FR-001 persistent horizontal bar. Effectively static — its entry set never changes at runtime,
unlike 017's `MenuEntry`/`run_menu` which built a *fresh* entry list per screen instance.

| Field | Type | Notes |
|---|---|---|
| `entries` | `tuple[MenuBarEntry, ...]` | Fixed, in order: Exit, Machining, Configuration, About, Help (FR-001). |

`MenuBarEntry` reuses 017's existing `MenuEntry(value, label)` shape (`menu.py`) — no new type
needed; `menu.py`'s `_assign_mnemonics` (research.md) assigns each entry's accelerator character at
render time from the current entry list, same as today.

**Validation rule**: exactly the five FR-001 entries, in that order — a closed set, not
data-driven (unlike material types).

### `MachiningTree`

The collapsible Milling/Drilling navigation structure nested under the Machining bar entry
(FR-002), replacing `machining_menu.py`'s full-screen submenu. **Revised via `/speckit-clarify`
(reopened after implementation)**: Drilling's tool-selection sub-expansion is retired (FR-003) —
both children are now flat leaves, so this entity loses its `drilling_expanded` field entirely.

| Field | Type | Notes |
|---|---|---|
| `expanded` | `bool` | Whether Machining's own children (Milling, Drilling) are shown. Default `False`. |

**State transitions**:
- Selecting Machining while `expanded=False` → `expanded=True`.
- Selecting Machining again (or a dedicated collapse action) while `expanded=True` →
  `expanded=False` (Acceptance Scenario 4).
- Selecting Milling or Drilling opens the corresponding operation's floating window (FR-004)
  **without** changing `MachiningTree`'s own expand state (FR-005a: collapsing/expanding the tree
  never affects which operation screen is open, and vice versa — the two are independent, and now
  trivially so, since the floating window is not part of the tree's own container at all,
  research.md #3).

**Validation rule**: none beyond the type itself — with only one field, there is no longer a
sub-state that could become orphaned relative to another.

### `OperationScreen`

The FR-004 left/right split-pane screen for whichever operation (Drilling, or Milling — FR-009's
identical pattern) is currently open, rendered inside the floating window described in research.md
#3. One shared shape; Drilling and Milling supply different field sets (FR-005) and a different
`SessionState` instance (`DrillingSessionState`/`MillingSessionState`, reused unchanged above).
`selected_field` doubles as the accordion state for radio rendering (research.md #4): the row
matching `selected_field` renders as a full `RadioList` if it's a radio field, every other radio
row renders as a one-line summary — no separate "which radio is expanded" field is needed, since
that's always exactly whichever field is currently selected.

| Field | Type | Notes |
|---|---|---|
| `operation` | `Literal["drilling", "milling"]` | Which operation this instance presents. |
| `session_state` | `DrillingSessionState \| MillingSessionState` | The reused, unchanged state object (FR-012) — one instance per operation, owned by `app.py`, exactly as today. |
| `selected_field` | `FieldId` | Which left-pane field currently has focus (FR-016/FR-017's "the moment it is selected/highlighted"). |
| `field_buffer` | `str` | Raw, possibly-not-yet-valid text for a numeric field currently being typed (FR-016) — distinct from `session_state`'s own committed value; only meaningful while `selected_field` names a numeric field. Never passed to `calculate()` while unparseable (FR-006b). |
| `last_result` | `CalculationResult \| None` | The right pane's currently-displayed result (or `None` while inputs are incomplete — FR-006), cached against the exact input tuple that produced it so an input change that doesn't affect the result (or hasn't yet completed) doesn't trigger a spurious recompute. |

**`FieldId`**: an enum/literal naming every field FR-005 lists for the operation (e.g. for
Drilling: `unit_system`, `mode`, `material_type`, `material`, `tool`, `diameter`, `depth`,
`target_rpm` (only when `mode` is fixed-RPM), `available_power`). Milling's set additionally
includes `sub_operation`, `axial_depth_of_cut`, `radial_engagement`, `feed_per_tooth`,
`number_of_teeth`, `length_of_cut` in place of Drilling's `diameter`/`depth`. Mirrors the
prototype's own field-ordering approach (spec's Recommended Next Steps).

**State transitions** (FR-016/FR-017, validated in the prototype):
- Navigating to a new field commits `field_buffer` into `session_state` if the previous
  `selected_field` was numeric and `field_buffer` parses (FR-016); an unparseable buffer is
  discarded with a status message, not written to `session_state` (FR-006b), and navigation still
  proceeds.
- Left/Right on a numeric field adjusts `field_buffer` by a small step (FR-017). On a radio field,
  Up/Down navigates the expanded `RadioList`'s options and Enter/Space commits the highlighted one
  into `session_state`'s corresponding value (research.md #4 — `RadioList`'s own native bindings,
  not Left/Right cycling).
- Any committed change recomputes `last_result` (FR-007) against the current, complete input tuple;
  an incomplete or `calculate()`-rejected tuple sets `last_result` to `None` or to the returned
  `ErrorInfo`-bearing result respectively (FR-006/FR-006a) — never a stale result from a
  different input set.

**Validation rule**: `last_result` MUST be recomputed (or cleared) before render whenever the input
tuple it was cached against no longer matches `session_state`'s current values — this is FR-006's
"MUST NOT display a result computed from a different, no-longer-current set of inputs" as a data
invariant, not just a UI behavior.

### `SessionUI` (top-level, replaces `NavigationState`)

The single persistent session object `app.py` owns for the whole run — 017's `NavigationState`
(a `current_screen` + `screen_stack` pair modeling mutually-exclusive full-screen navigation) no
longer fits, since the menu bar, tree, and an open `OperationScreen` can all be simultaneously
present (FR-005a).

| Field | Type | Notes |
|---|---|---|
| `menu_bar` | `MenuBar` | Static entry set (above). |
| `tree` | `MachiningTree` | Expand/collapse state (above). |
| `open_operation` | `OperationScreen \| None` | The currently-open operation screen, if any; `None` at the top-level menu bar/tree state (Acceptance Scenario 5's "return to the main menu"). |
| `drilling_state` | `DrillingSessionState` | Persists across visits per FR-012, independent of whether Drilling is the `open_operation` right now. |
| `milling_states` | `dict[MillingSubOperation, MillingSessionState]` | One per sub-operation, same carryover guarantee, mirroring `app.py`'s existing `milling_states` dict today. |
| `locale` | `str` | Resolved once at startup (unchanged from 017/PR #94). |
| `materials_config_path` | `str \| None` | Unchanged from today. |

**State transitions**:
- Selecting a leaf operation sets `open_operation` to a new `OperationScreen` wrapping the
  corresponding persisted `drilling_state`/`milling_states[...]` entry (not a fresh, empty state —
  FR-012's carryover guarantee).
- Returning to the main menu (Acceptance Scenario 5) sets `open_operation = None`; `tree`'s own
  expand state is left as-is ("not necessarily still expanded to the same leaf" — Acceptance
  Scenario 5 permits but does not require collapsing it).
- Collapsing/expanding `tree` never touches `open_operation` (FR-005a) — the two fields are
  independent, enforced by construction (no code path writes both from the same handler).
- A mid-session terminal resize (FR-013a) touches none of these fields — it is a redraw concern
  handled by `prompt-toolkit`'s own resize handling on the one persistent `Application`, not a
  `SessionUI` state transition.

**Validation rule**: exactly the invariant FR-005a exists to guarantee — there is no code path
where `tree`'s state alone determines whether a required `OperationScreen` field is reachable,
since `OperationScreen`'s own fields (above) are always present in the left pane regardless of
`tree.expanded`.

## Entity relationship summary

```text
SessionUI
├── menu_bar: MenuBar (static)
├── tree: MachiningTree (independent expand/collapse state)
├── open_operation: OperationScreen | None
│   ├── session_state: DrillingSessionState | MillingSessionState  (reused unchanged, FR-012)
│   ├── selected_field: FieldId
│   ├── field_buffer: str
│   └── last_result: CalculationResult | None
├── drilling_state: DrillingSessionState        (persists regardless of open_operation)
└── milling_states: dict[MillingSubOperation, MillingSessionState]  (persists regardless of open_operation)
```
