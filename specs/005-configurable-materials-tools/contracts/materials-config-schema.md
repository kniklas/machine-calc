# Contract: Materials/Tools Configuration File Schema

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This is the schema for **both** the bundled default files
(`src/machine_calc/data/materials.toml`,
`src/machine_calc/operations/drilling/data/tools.toml`) and any
user-supplied override/addition file passed via `--materials-config PATH`.
A user file may include a `[[materials]]` array, a `[[tools]]` array, both, or
neither — any section it omits is simply not overridden/extended for that
kind (FR-002).

## Top-level shape

```toml
[[materials]]
name = "..."
reference_cutting_speed = 0.0
reference_feed_per_rev = 0.0
specific_cutting_force = 0.0
unit_system = "metric"          # optional; "metric" (default) or "imperial"

[materials.translations]         # optional; nests under the preceding [[materials]] entry
fr = "..."
de = "..."

[[tools]]
name = "..."
cutting_speed_factor = 0.0
feed_factor = 0.0
unit_system = "metric"          # optional; "metric" (default) or "imperial"; accepted but has
                                  # no numeric effect (research.md #5) since both factors are
                                  # dimensionless multipliers

[tools.translations]
fr = "..."
```

## `[[materials]]` entry fields

| Key | Required | Type | Unit (declared) | Notes |
|---|---|---|---|---|
| `name` | Yes | string | — | Unique within the effective (merged) set (FR-006) |
| `reference_cutting_speed` | Yes | float > 0 | m/min if `unit_system = "metric"` (or omitted); ft/min if `"imperial"` | Converted to canonical m/min internally (research.md #5) |
| `reference_feed_per_rev` | Yes | float > 0 | mm/rev if metric/omitted; in/rev if imperial | Converted to canonical mm/rev internally |
| `specific_cutting_force` | Yes | float > 0 | N/mm² (≡ MPa) if metric/omitted; psi if imperial | Converted to canonical N/mm² internally |
| `unit_system` | No | `"metric"` \| `"imperial"` | — | Default `"metric"` when omitted (FR-011) |
| `translations` (sub-table) | No | table of `locale -> string` | — | Locale codes are free-form strings (e.g. `"fr"`, `"de"`); merged per-locale on override (FR-015) |

## `[[tools]]` entry fields

| Key | Required | Type | Notes |
|---|---|---|---|
| `name` | Yes | string | Unique within the effective (merged) set (FR-006) |
| `cutting_speed_factor` | Yes | float > 0 | Dimensionless multiplier; unaffected by `unit_system` |
| `feed_factor` | Yes | float > 0 | Dimensionless multiplier; unaffected by `unit_system` |
| `unit_system` | No | `"metric"` \| `"imperial"` | Default `"metric"`; stored/displayed only (no conversion) |
| `translations` (sub-table) | No | table of `locale -> string` | Same semantics as materials |

## Validation rules (enforced identically for bundled and user files)

1. `name` is required and non-empty for every entry.
2. All required numeric fields MUST be present and strictly positive
   *after* unit conversion (FR-006). A non-positive or missing required
   numeric field raises `RegistryConfigError`
   (`error.materials_config.invalid_entry`).
3. `unit_system`, if present, MUST be exactly `"metric"` or `"imperial"`
   (case-sensitive); any other value raises `RegistryConfigError`
   (`error.materials_config.invalid_entry`).
4. Within a single file, two `[[materials]]` entries (or two `[[tools]]`
   entries) MUST NOT share the same `name` — this raises
   `RegistryConfigError` (`error.materials_config.duplicate_entry`) (FR-016).
   Note: a user file entry sharing a name with a *bundled* entry is not a
   duplicate — it is a valid override (FR-003).
5. A file that fails to parse as TOML at all raises `RegistryConfigError`
   (`error.materials_config.malformed`) and none of its entries (nor any
   valid ones alongside a malformed one) are applied (FR-007).
6. A `config_path` that is `None`, does not exist, or is not a readable file
   is **not** an error: it yields the bundled defaults unchanged plus a
   `notice_key` (`notice.materials_config.not_found`) for the caller to
   surface (FR-005).

## Example: bundled `materials.toml` (excerpt, lossless re-encoding of today's `_MATERIALS`)

```toml
[[materials]]
name = "Mild Steel"
reference_cutting_speed = 25.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0
unit_system = "metric"

[[materials]]
name = "Stainless Steel"
reference_cutting_speed = 15.0
reference_feed_per_rev = 0.15
specific_cutting_force = 2400.0
unit_system = "metric"
```

## Example: user override/addition file

```toml
# Adds a new material not in the bundled defaults, authored from an
# imperial-unit data sheet (converted automatically at load time).
[[materials]]
name = "Bronze"
reference_cutting_speed = 250.0   # ft/min
reference_feed_per_rev = 0.008    # in/rev
specific_cutting_force = 130000.0 # psi
unit_system = "imperial"

[materials.translations]
fr = "Bronze"
de = "Bronze"

# Overrides the built-in "Mild Steel" reference cutting speed and adds a
# French translation, while an existing German translation shipped in the
# bundled defaults (if any) for this entry is preserved (FR-015).
[[materials]]
name = "Mild Steel"
reference_cutting_speed = 28.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0

[materials.translations]
fr = "Acier doux"

# Adds a new drilling tool.
[[tools]]
name = "Ceramic"
cutting_speed_factor = 4.0
feed_factor = 1.0
```

## Consumers

- `src/machine_calc/registry_config.py`: kind-agnostic parse/fallback/
  duplicate-detection/merge implementation shared by both consumers below.
- `src/machine_calc/registry.py`: parses `[[materials]]` against this schema,
  converts declared-imperial fields to canonical metric, constructs
  `WorkpieceMaterial` instances, and validates.
- `src/machine_calc/operations/drilling/tools.py`: parses `[[tools]]` against
  this schema, constructs `DrillingTool` instances (no unit conversion, per
  research.md #5), and validates.
