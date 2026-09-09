# Data Model: Console Text GUI (TUI)

**Feature**: `017-console-text-gui` | **Date**: 2026-09-08

The spec's own Key Entities section says "not applicable... introduces no new persisted data or
domain entities" — correct: this feature adds a presentation layer over calculations and
registries that already exist (`mfgparams.processes.*`, `mfgparams.registry`). What *is* new is the
**UI/navigation model** the text GUI needs to hold in memory for one session. That model is
documented here in place of a domain data model.

## NavigationState

The text GUI's single source of truth for "what's on screen and how did we get here." Held by
`tui/app.py`, not persisted (spec Assumptions: "No new persistence").

| Field | Type | Notes |
|---|---|---|
| `current_screen` | `ScreenId` (enum: `MENU`, `MACHINING_MENU`, `MILLING_FORM`, `DRILLING_FORM`, `CONFIGURATION`, `ABOUT`, `HELP`) | The screen currently rendered. |
| `screen_stack` | `list[ScreenId]` | Prior screens, for "go back" (FR-012's "how to go back" visibility requirement). `MENU` is never pushed — it's the root and has no "back". |
| `locale` | `str` | Resolved once at startup via `mfgparams.console.i18n.get_locale()` and held for the session (spec Assumptions: "single active locale per session"). |
| `materials_config_path` | `str \| None` | Passed through from the same `--materials-config` CLI argument the REPL accepted; read-only for this feature (research.md #4). |

**Transitions**: `MENU` → `MACHINING_MENU` → (`MILLING_FORM` | `DRILLING_FORM`); `MENU` →
`CONFIGURATION`; `MENU` → `ABOUT`; `MENU` → `HELP`. Every non-`MENU` screen can pop back to its
pusher via `screen_stack`. No other transitions exist — the menu structure is closed per FR-009
("exactly these entries").

## MenuEntry

One row in a menu screen (`menu.py`'s top-level menu, `machining_menu.py`'s submenu).

| Field | Type | Notes |
|---|---|---|
| `label_key` | `str` | Message-catalog key (FR-003) — the visible label, translated. |
| `mnemonic` | `str` | Single key that activates this entry directly (FR-010), e.g. `"m"` for Machining. Unique within its menu. |
| `target` | `ScreenId \| MenuEntry list` | Either a screen to navigate to, or a nested list of entries (Machining's submenu). |

**Validation rule**: every `MenuEntry`'s `mnemonic` MUST be unique within its containing menu — a
contract-test invariant (contracts/console-tui-contract.md), not just a convention, since a
collision would make FR-010's "direct mnemonic/accelerator shortcut per menu item" ambiguous.

## OperationForm

The parameter-entry model for Milling and Drilling (`screens/milling.py`, `screens/drilling.py`).
Both reuse the same shape; only the field set and the core function they ultimately call differ.

| Field | Type | Notes |
|---|---|---|
| `fields` | `list[FieldSpec]` | Ordered; rendered top-to-bottom. |
| `submit_target` | `Callable[..., CalculationResult \| ErrorInfo]` | The existing core function this form ultimately calls (e.g. `mfgparams.processes.machining.drilling.calculate`) — unchanged from what the REPL called. |

### FieldSpec

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Parameter name, matching the core function's keyword argument. |
| `label_key` | `str` | Message-catalog key for the field's visible label. |
| `kind` | `enum` (`CHOICE`, `NUMBER`, `OPTIONAL_NUMBER`) | Mirrors the REPL's existing `_prompt_choice`/`_prompt_number`/`_prompt_optional_power` distinction. |
| `unit_key` | `str \| None` | Message-catalog key for the unit suffix shown next to a `NUMBER`/`OPTIONAL_NUMBER` field, if any. |
| `choices` | `list[str] \| None` | For `CHOICE` fields (e.g. material, tool, unit system, mode) — populated from the existing registry lookups (`get_material`, `get_tool`, etc.), not hardcoded. |
| `default` | `Any \| None` | Matches the REPL's existing defaulting behavior per field. |

**Validation rule**: an invalid value produces an `ErrorInfo` (the core's existing type, per
Constitution Principle III) rendered in-place via the message catalog (FR-003, User Story 1
Scenario 2) — the text GUI does not invent a second validation/error representation.

## ConfigurationView (read-only, research.md #4)

| Field | Type | Notes |
|---|---|---|
| `materials_config_path` | `str \| None` | The path currently in effect (from `--materials-config`, or `None` for the bundled defaults). |
| `material_types` | `list[str]` | From `mfgparams.list_material_types()`. |
| `materials_by_type` | `dict[str, list[str]]` | From `mfgparams.list_materials(material_type=...)` per type. |
| `tools` | `list[str]` | From `mfgparams.list_tools()` (drilling tools; milling tool listings are per sub-operation, same pattern). |

No write operations are modeled — v1 scope is display/selection only (research.md #4).
