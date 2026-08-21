# Contract: Milling Tools Configuration Schema (addendum)

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Addendum to `specs/005-configurable-materials-tools/contracts/materials-config-schema.md`.
That contract defines the single optional user configuration file (supplied
via `--materials-config` / `materials_config_path`) containing `[[materials]]`
and `[[tools]]` array-of-tables. This feature adds two further top-level
array-of-tables to the **same** file (FR-015). No second configuration file
and no new loader is introduced.

## Added sections

```toml
# End-mill tools (new in 009)
[[end_mill_tools]]
name = "Carbide"
cutting_speed_factor = 1.8
unit_system = "metric"

  [end_mill_tools.translations]
  pl = "Weglik spiekany"

# Face-mill tools (new in 009)
[[face_mill_tools]]
name = "Coated Carbide"
cutting_speed_factor = 2.2
unit_system = "metric"
```

### Field rules

| Field | Required | Rules |
|---|---|---|
| `name` | yes | non-empty string; case-insensitive unique within its own section; matching an existing bundled name performs an override/merge, exactly as for `[[tools]]` |
| `cutting_speed_factor` | yes for a new entry, optional when overriding | number `> 0` |
| `unit_system` | no | `"metric"` \| `"imperial"`; defaults to `"metric"` |
| `translations` | no | table of locale code -> translated display name |

There is deliberately **no** `feed_factor` field: feed per tooth is a direct
per-calculation input for milling (research.md #4). Supplying `feed_factor`
in a milling section is an unknown field and is rejected/ignored by the same
rule the 005 contract already applies to `[[tools]]`.

## Section isolation (normative)

Each registry loads **only** its own `table_key` and MUST ignore every other
top-level section:

| Registry | `table_key` |
|---|---|
| Materials | `materials` |
| Drilling tools | `tools` |
| End-mill tools | `end_mill_tools` |
| Face-mill tools | `face_mill_tools` |

Consequences that MUST hold (and are covered by a regression test):

1. A config file containing only `[[end_mill_tools]]` leaves the drilling
   tool registry byte-for-byte identical to the bundled default, and the
   drilling flow starts and calculates normally (FR-002, SC-005).
2. A pre-existing config file written before this feature (only
   `[[materials]]` and `[[tools]]`) stays valid, keeps affecting drilling
   only, and adds nothing to either milling tool registry.
3. Because `[[tools]]` entries require `feed_factor` and milling entries
   have none, the two MUST never be merged into a common list — doing so
   would raise `RegistryConfigError` at startup and break an already-shipped
   operation.
4. An unparsable or invalid milling section produces the same structured
   `RegistryConfigError` behaviour the 005 contract already specifies, with
   a message naming the offending section and entry.
