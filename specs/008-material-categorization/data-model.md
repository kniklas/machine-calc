# Data Model: Material Categorization System

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This feature adds one field and two derived-list functions to the existing
shared materials registry (`specs/005-configurable-materials-tools`). It does
not introduce a new entity, table, or file format.

## Entity: `WorkpieceMaterial`

Defined in `src/machine_calc/registry.py` as a frozen dataclass. Unchanged
fields are listed for context; only `material_type` is new to this feature.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | Unique display name, e.g. `"Mild Steel"`, `"Oak"` (unchanged) |
| `reference_cutting_speed_m_min` | `float` | Canonical-metric HSS-baseline cutting speed (unchanged) |
| `reference_feed_per_rev_mm` | `float` | Canonical-metric HSS-baseline feed per revolution (unchanged) |
| `specific_cutting_force_kc` | `float` | N/mm², used in torque/power calculations (unchanged) |
| `unit_system` | `str` | `"metric"` or `"imperial"`; authoring-time unit system, retained for display (unchanged) |
| `translations` | `dict[str, str]` | Locale code → translated display name (unchanged) |
| `material_type` | `str` | **New.** Category identifier for the two-step selection flow. Free-form, not an enum. Default: `DEFAULT_MATERIAL_TYPE = "uncategorized"` |

`WorkpieceMaterial.is_usable` (property) and `display_name(locale)` (method)
are unchanged and do not consider `material_type`.

### `material_type` validation

Resolved by `registry._parse_material_type(entry, issues)` at load time, one
entry at a time, before the `WorkpieceMaterial` is constructed:

- Key absent from the merged entry's `fields` → `DEFAULT_MATERIAL_TYPE`
  (`"uncategorized"`), no issue recorded.
- Present, non-empty string (after `.strip()`) whose characters are all
  outside the Unicode `Cc` (C0/C1 controls), `Zl` and `Zp` (line/paragraph
  separator) categories → used verbatim. Printable non-ASCII spacing such as
  a non-breaking space is allowed.
- Present but not a string, an empty/whitespace-only string, or a string
  containing a control character such as a tab, a newline (reachable via a
  TOML multiline string, and unselectable because `input()` returns a single
  line) or a terminal control such as `U+009B` → an issue is
  appended to that material's `MaterialValidationRecord.issues` (existing
  entity, unchanged shape) and the value falls back to
  `DEFAULT_MATERIAL_TYPE`. This is **warn-and-continue**, matching the
  registry's existing policy for invalid numeric fields — the material stays
  registered and selectable; it is not rejected.

There is no separate "MaterialType" entity, validation record, or table.

## TOML key → dataclass field mapping

| TOML key (`[[materials]]`) | `WorkpieceMaterial` field | Required | Default |
|---|---|---|---|
| `name` | `name` | Yes | — |
| `reference_cutting_speed` | `reference_cutting_speed_m_min` | Yes | — |
| `reference_feed_per_rev` | `reference_feed_per_rev_mm` | Yes | — |
| `specific_cutting_force` | `specific_cutting_force_kc` | Yes | — |
| `unit_system` | `unit_system` | No | `"metric"` |
| `translations` | `translations` | No | `{}` |
| `material_type` | `material_type` | No | `DEFAULT_MATERIAL_TYPE` (`"uncategorized"`) |

The full authoritative schema (including the sticky-merge rule below) lives
in
[`specs/005-configurable-materials-tools/contracts/materials-config-schema.md`](../005-configurable-materials-tools/contracts/materials-config-schema.md);
this document does not duplicate it beyond the mapping above.

## Merge behavior: sticky fields

`registry_config.merge_entries(bundled, user, sticky_fields=())` is a
generic, kind-agnostic function (shared with drilling tools). `registry.py`
calls it with `sticky_fields=("material_type",)`.

Normal (non-sticky) merge rule: a user entry whose `name` matches a bundled
entry replaces that entry's `fields` **wholesale** (per-locale translation
merge is a separate exception, unaffected by this feature).

Sticky-field exception: for each key in `sticky_fields`, if the user entry's
`fields` omits that key, the bundled entry's value for that key is copied
into the merged `fields` before the `WorkpieceMaterial` is built. Concretely,
for `material_type`: a user override of `"Mild Steel"` that does **not**
restate `material_type` keeps `material_type = "metal"` from the bundled
entry, rather than losing it to `DEFAULT_MATERIAL_TYPE`. If the user override
*does* restate `material_type`, the user's value wins normally.

This is the mechanism that keeps pre-008 `--materials-config` files (written
before `material_type` existed) loading with their materials in the same
categories as before, with no changes required to those files.

## Derived data: material types

There is no persisted list of categories. `list_material_types(config_path=None)`
(`registry.py`) computes one on demand:

```python
list(dict.fromkeys(material.material_type for material in materials.values()))
```

- Categories are derived from whichever materials are currently registered
  (bundled, or bundled+user-merged if `config_path` is given).
- Order is **first appearance** in the material list (bundled materials in
  file order, then any user-added materials in their file order) — a `dict`
  preserves insertion order and de-duplicates automatically. There is no
  separate ordering field; reordering categories means reordering (or
  relocating) the materials that introduce them in the TOML file.
- A category with zero materials cannot exist; declaring `material_type =
  "cement"` on any material entry is both necessary and sufficient to
  register `"cement"` as a selectable category.

## Bundled data set (`src/machine_calc/data/materials.toml`)

13 materials, unchanged from `005-configurable-materials-tools` except for
the added `material_type` key on each:

| `material_type = "metal"` | `material_type = "wood"` |
|---|---|
| Mild Steel | Oak |
| Stainless Steel | Maple |
| Aluminum | Pine |
| Cast Iron | Spruce |
| Brass | Fir |
| Titanium | Plywood |
| | MDF |

No other materials (e.g. no "AISI 1045", no "Aluminum 6061-T6") exist in the
bundled catalog.

## i18n additions (`src/machine_calc/locales/en.py`)

| Key | Value |
|---|---|
| `cli.label.material_type` | `"Material type"` |
| `material_type.metal` | `"Metal"` |
| `material_type.wood` | `"Wood"` |
| `material_type.uncategorized` | `"Uncategorized"` |

Only the `en` locale exists in this project. A `material_type.<id>` key with
no catalog entry (any category introduced purely via TOML data, e.g.
`"plastic"`) is not an error: `cli._material_type_label()` detects the
missing entry (`translate()` returns the key unchanged) and falls back to a
title-cased rendering of the identifier (e.g. `"plastic"` → `"Plastic"`,
`"composite-fibre"` → `"Composite Fibre"`).

## Functions added/changed

| Function | Module | Change |
|---|---|---|
| `list_material_types(config_path=None) -> list[str]` | `registry.py` | **New.** Returns categories in first-appearance order. |
| `list_materials(config_path=None, material_type=None) -> list[str]` | `registry.py` | **Extended.** New optional `material_type` filter parameter; omitting it preserves the exact pre-008 signature and return value. An unknown `material_type` yields `[]`, not an error. |
| `merge_entries(bundled, user, sticky_fields=())` | `registry_config.py` | **Extended.** New optional `sticky_fields` parameter (default `()`, i.e. no behavior change for existing callers that don't pass it). |
| `load_and_merge(...)` / `_load_and_merge_uncached` / `_load_and_merge_cached` | `registry_config.py` | **Extended.** `sticky_fields` threaded through to `merge_entries`. |
| `_parse_material_type(entry, issues)` | `registry.py` | **New**, private. |
| `_material_type_label(material_type, locale)` | `cli.py` | **New**, private. |
| `_prompt_material_type_choice(material_types, default, locale)` | `cli.py` | **New**, private. |

## Out of scope

No entity, table, or function exists for creating, updating, or deleting a
material type or material at runtime (User Story 3, dropped — see
research.md "Scope Decisions"). The only way to add a material or a category
is to add a `[[materials]]` entry to a TOML file (bundled or
`--materials-config`).
