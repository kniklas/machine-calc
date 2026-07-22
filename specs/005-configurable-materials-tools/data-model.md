# Phase 1 Data Model: Configurable Materials & Tools

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

This document defines the entities and merge/validation rules backing this
feature, extending (not replacing) the entities defined in
`specs/001-metal-drilling-calc/data-model.md`.

## Material/Tool Configuration Source

Not a runtime object but the two-file input model described in research.md
#1-#2:

| Source | Location | Presence |
|---|---|---|
| Bundled materials defaults | `src/machine_calc/data/materials.toml` (package data) | Always present; shipped with the package |
| Bundled tools defaults | `src/machine_calc/operations/drilling/data/tools.toml` (package data) | Always present; shipped with the package |
| User-supplied override/addition | Path supplied via CLI `--materials-config PATH` (or a caller-supplied `config_path` to the library functions) | Optional; `None`/missing/unreadable falls back to bundled-only (FR-005) |

The **effective set** used at runtime is the bundled entries merged with the
user-supplied entries (research.md #4): user entries override a bundled entry
of the same name (scalar fields + unit system replaced wholesale;
`translations` merged per-locale, FR-015) or are appended if the name is new
(FR-004).

## RawRegistryEntry (parse-time, kind-agnostic)

Intermediate representation produced by `registry_config.py` while parsing
TOML, before a caller (`registry.py`/`tools.py`) converts it into a
`WorkpieceMaterial`/`DrillingTool`. Not part of the public API.

| Field | Type | Notes |
|---|---|---|
| `name` | str | Required; unique within the merged set for its kind (FR-006, FR-016) |
| `fields` | dict[str, float] | The kind-specific numeric reference fields (see below), still in their *declared* unit system |
| `unit_system` | `"metric"` \| `"imperial"` | Defaults to `"metric"` when the TOML entry omits the key (FR-011) |
| `translations` | dict[str, str] | Locale code → translated display name; may be empty |

### TOML key → dataclass field mapping (I1 remediation)

`registry_config.py` parses TOML keys that omit unit suffixes; `registry.py`/
`tools.py` map them onto the existing (unit-suffixed) dataclass fields
one-to-one when constructing `WorkpieceMaterial`/`DrillingTool` from a merged
`RawRegistryEntry`. The **dataclass field names themselves are never
renamed** — only this parse-time mapping is new:

| TOML key (`fields` dict) | `WorkpieceMaterial`/`DrillingTool` field | Kind |
|---|---|---|
| `reference_cutting_speed` | `reference_cutting_speed_m_min` | material |
| `reference_feed_per_rev` | `reference_feed_per_rev_mm` | material |
| `specific_cutting_force` | `specific_cutting_force_kc` | material |
| `cutting_speed_factor` | `cutting_speed_factor` | tool (unchanged name) |
| `feed_factor` | `feed_factor` | tool (unchanged name) |

## WorkpieceMaterial (extended)

Reference machining data for a selectable workpiece material (FR-004 of
`001-metal-drilling-calc`; extended here). All fields below are additive to
the existing dataclass — no existing field is renamed, retyped, or removed.

| Field | Type | Notes |
|---|---|---|
| `name` | str | Unique English display name / stable identifier (unchanged) |
| `reference_cutting_speed_m_min` | float | Canonical metric (m/min), post-conversion if declared imperial (unchanged storage unit) |
| `reference_feed_per_rev_mm` | float | Canonical metric (mm/rev), post-conversion if declared imperial (unchanged storage unit) |
| `specific_cutting_force_kc` | float | Canonical metric (N/mm²), post-conversion if declared imperial (unchanged storage unit) |
| `unit_system` | `"metric"` \| `"imperial"` | **New.** The unit system the entry was *authored*/declared in (FR-011, FR-013); retained after conversion purely for display/audit — calculation always uses the canonical-metric fields above |
| `translations` | dict[str, str] | **New.** Locale code → translated display name (FR-009); empty by default |

Validation (unchanged + extended):
- `name` MUST be unique within the merged registry (Principle III; FR-006).
- All three numeric fields MUST be positive, checked *after* unit conversion
  to canonical metric (existing `_validate`, unchanged logic/thresholds).
- `unit_system`, if present in TOML, MUST be exactly `"metric"` or
  `"imperial"`; any other value is a `RegistryConfigError` (FR-006).

`display_name(locale)`: returns `translations[locale]` if present, else
`name` (research.md #7; mirrors `i18n.translate`'s English-fallback rule but
operates on data rather than a message catalog).

## DrillingTool (extended)

Reference data for a selectable drill bit type (FR-005 of
`001-metal-drilling-calc`; extended here).

| Field | Type | Notes |
|---|---|---|
| `name` | str | Unique English display name / stable identifier (unchanged) |
| `cutting_speed_factor` | float | Dimensionless multiplier (unchanged) |
| `feed_factor` | float | Dimensionless multiplier (unchanged) |
| `unit_system` | `"metric"` \| `"imperial"` | **New.** Accepted, stored, and displayed per FR-011/FR-013, but performs **no numeric conversion** — both factors are dimensionless ratios relative to the material's own reference values, so they carry no independent physical unit to convert (research.md #5). This is an intentional, documented no-op, not an oversight. |
| `translations` | dict[str, str] | **New.** Locale code → translated display name (FR-009); empty by default |

Validation (unchanged + extended): same positivity rule as today
(`cutting_speed_factor`/`feed_factor` MUST be positive); same `unit_system`
value restriction and `translations` shape as `WorkpieceMaterial` above.

`display_name(locale)`: identical resolution rule as `WorkpieceMaterial`.

## RegistryConfigError (new)

Raised by `registry_config.py` (and propagated by `registry.py`/`tools.py`)
when a user-supplied configuration file cannot be safely applied — never for
a merely missing/unreadable file (that is the separate notice case below).

| Field | Type | Notes |
|---|---|---|
| `message_key` | str | Message-catalog key (Constitution VIII), e.g. `error.materials_config.malformed`, `error.materials_config.duplicate_entry`, `error.materials_config.invalid_entry` |
| `kwargs` | dict[str, object] | `str.format()` placeholder values for the catalog message (e.g. `path`, `name`, `kind`, `details`) |

Raised for (FR-006, FR-007, FR-016):
- Malformed TOML syntax in the user file (`error.materials_config.malformed`).
- Two entries of the same kind sharing a name within the *same* user file
  (`error.materials_config.duplicate_entry`).
- An entry (bundled or user-supplied, post-merge) failing positivity/
  unit-system validation (`error.materials_config.invalid_entry`).

The CLI (`cli.py`) catches this exception once at startup, translates it via
`machine_calc.i18n.translate(locale, message_key, **kwargs)`, prints the
translated message, and exits without a raw traceback (research.md #6).

## Configuration Notice (new, non-error)

A missing or unreadable user-supplied path is **not** a `RegistryConfigError`
(FR-005). `registry_config.py`'s loader instead returns a
`notice_key: str | None` (e.g. `notice.materials_config.not_found`) alongside
the merged entries; the CLI prints this translated notice once (if non-`None`)
at startup and proceeds using the bundled defaults only.

## Merge Algorithm (kind-agnostic; research.md #4)

Input: `bundled: list[RawRegistryEntry]`, `user: list[RawRegistryEntry] | None`.

0. Regardless of whether `user` is supplied, `bundled` itself MUST have no
   duplicate `name` within a kind; this is the same construction-time
   invariant `registry.py`/`tools.py` already enforce today for `_MATERIALS`/
   `_TOOLS` (`ValueError` on duplicate name). Under this feature it is
   re-expressed as a `RegistryConfigError` and is verified defense-in-depth
   at every load, not merely asserted by bundled-file unit tests (U2
   remediation: this is a runtime guarantee, not just a testing convention).
1. If `user` is `None` (no path supplied, or path missing/unreadable): return
   `bundled` unchanged, plus a notice key if a path *was* supplied but could
   not be read.
2. Else, verify `user` has no duplicate `name` within itself for this kind;
   raise `RegistryConfigError` if it does (FR-016).
3. For each `user` entry: if its `name` matches a `bundled` entry, replace
   that bundled entry's `fields`/`unit_system` wholesale, and merge
   `translations` per-locale (user's locale value wins for that locale only;
   other bundled locale keys for that entry are preserved) (FR-003, FR-015).
   If its `name` does not match any `bundled` entry, append it as a new entry
   (FR-004).
4. Return the merged list (bundled entries not touched by `user` are
   unaffected) and no notice key.

## CLI Argument (new)

| Argument | Type | Notes |
|---|---|---|
| `--materials-config PATH` | str \| None | Optional; resolved once at CLI startup (research.md #3), held fixed for the session like `locale`, threaded into `list_materials()`, `list_tools()`, and every `calculate()` call as `materials_config_path` |

## Relationship to existing `001-metal-drilling-calc` entities

- `DrillingOperation` (request) and `CalculationResult` (response) from
  `specs/001-metal-drilling-calc/data-model.md` are **unchanged** by this
  feature (FR-017) except that `calculate()` gains the new optional
  `materials_config_path` keyword described above; every existing field and
  validation rule on those two entities is untouched.
- `MaterialToolCompatibility` (registry-level rule) is unchanged: every
  material × tool combination in the *effective* (merged) registries remains
  defined, exactly as it is for the bundled-only registries today.
