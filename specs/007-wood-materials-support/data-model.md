# Phase 1 Data Model: Wood Materials Support

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This feature extends the existing material registry model from
`specs/005-configurable-materials-tools`.

## Entity: WorkpieceMaterial (extended usage)

No new public dataclass type is required. Existing `WorkpieceMaterial` fields
are reused:

| Field | Type | Notes |
|---|---|---|
| `name` | str | Includes wood identifiers (Oak, Maple, Pine, Spruce, Fir, Plywood, MDF) |
| `reference_cutting_speed_m_min` | float | Canonical metric cutting speed |
| `reference_feed_per_rev_mm` | float | Canonical metric feed per rev |
| `specific_cutting_force_kc` | float | Canonical metric specific cutting force |
| `unit_system` | `"metric"` \| `"imperial"` | Declared source unit system |
| `translations` | dict[str, str] | Optional localized display labels |

## Entity: MaterialValidationRecord (design-level)

Represents load-time validation outcome per material entry.

| Field | Type | Notes |
|---|---|---|
| `material_name` | str | Canonical entry name |
| `status` | `valid` \| `warning` | Warning means entry has missing/invalid parameter(s) |
| `issues` | list[str] | Human-readable issue details logged at warning level |
| `source_path` | str | Bundled file or user override path |

### Validation rules (FR-008)

- At registration/load time, validate each material’s required numeric fields:
  cutting speed, feed per rev, specific cutting force.
- Missing fields, non-numeric values, or values `<= 0` produce warnings.
- Initialization continues after warnings; entry remains present in registry
  for listing/override compatibility.

## Entity: EffectiveMaterialRegistry

Merged runtime view of bundled + user-defined materials, including woods.

| Field | Type | Notes |
|---|---|---|
| `entries` | dict[str, WorkpieceMaterial] | Name-keyed effective registry |
| `validation` | dict[str, MaterialValidationRecord] | Validation status per entry |

### Relationships

- `EffectiveMaterialRegistry.entries[name]` ↔
  `EffectiveMaterialRegistry.validation[name]`
- User override file may replace any built-in wood entry by matching `name`.

## State transitions

```text
Parsed -> Validated
Validated(valid) -> UsableForCalculation
Validated(warning) -> ListedWithWarnings
ListedWithWarnings + UserOverrideFix -> Validated(valid)
```

Notes:
- `ListedWithWarnings` entries remain discoverable/listable.
- Calculation path should reject unusable entries with clear error messaging if
  required fields remain invalid at use-time.
