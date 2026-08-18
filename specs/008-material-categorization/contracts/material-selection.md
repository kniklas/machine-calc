# API Contract: Material Selection & Registry

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This documents the actual public surface added/changed by this feature. It
covers two modules: `machine_calc.registry` (materials, library-level) and
`machine_calc.cli` (interactive REPL, internal to the CLI). There is no
separate "materials package" — see `research.md` for why that was rejected.

## `machine_calc.registry`

### `list_material_types(config_path: str | None = None) -> list[str]`

Returns the registered material-type identifiers, in first-appearance order
(bundled materials first, then any user-supplied additions), with no
duplicates.

```python
from machine_calc.registry import list_material_types

list_material_types()
# ['metal', 'wood']

list_material_types(config_path="my_materials.toml")
# ['metal', 'wood', 'plastic']   # if my_materials.toml adds a PVC entry
# with material_type = "plastic"
```

- `config_path=None` (default): bundled catalog only, cached at import time.
- `config_path=<path>`: merged bundled+user catalog for that path, cached
  per path (`functools.cache` via `registry._build_registry_cached`).
- Never raises for an empty registry; returns `[]` only if no materials are
  registered at all (not reachable with the bundled catalog present).

### `list_materials(config_path: str | None = None, material_type: str | None = None) -> list[str]`

Pre-existing function (`005-configurable-materials-tools`), extended with
one new optional keyword argument.

```python
from machine_calc.registry import list_materials

list_materials()
# ['Mild Steel', 'Stainless Steel', 'Aluminum', 'Cast Iron', 'Brass',
#  'Titanium', 'Oak', 'Maple', 'Pine', 'Spruce', 'Fir', 'Plywood', 'MDF']

list_materials(material_type="wood")
# ['Oak', 'Maple', 'Pine', 'Spruce', 'Fir', 'Plywood', 'MDF']

list_materials(material_type="cement")
# []   -- unknown category yields an empty list, not an error
```

- `material_type=None` (default): every registered material, in registration
  order — byte-for-byte the pre-008 behavior and signature.
- `material_type=<id>`: only materials whose `material_type` equals `<id>`
  (exact string match; not case-insensitive).

### `get_material(name: str, config_path: str | None = None) -> WorkpieceMaterial | None`

Unchanged signature. The returned `WorkpieceMaterial` now carries a
`material_type: str` attribute (see data-model.md); callers that don't use
it are unaffected.

### `get_material_validation(name: str, config_path: str | None = None) -> MaterialValidationRecord | None`

Unchanged. An invalid `material_type` value in the source TOML (not a
string, or empty) surfaces as an entry in `.issues`, e.g.:

```
"field 'material_type' must be a non-empty string, got 123"
```

The record's `status` becomes `"warning"`, matching the existing policy for
any other invalid field — the material remains registered and selectable.

## `machine_calc.registry_config`

### `merge_entries(bundled, user, sticky_fields: tuple[str, ...] = ()) -> list[RawRegistryEntry]`

Pre-existing function, extended with an optional `sticky_fields` parameter
(default `()`: no behavior change for existing callers that omit it, e.g.
`operations/drilling/tools.py`).

`registry.py` is the only caller that passes a non-empty value:

```python
merge_entries(bundled, user, sticky_fields=("material_type",))
```

Effect: if a `user` entry overrides a `bundled` entry by `name` but omits a
key listed in `sticky_fields`, that key's value is copied from the bundled
entry into the merged result instead of being dropped by the normal
wholesale-`fields`-replace rule. See data-model.md "Merge behavior: sticky
fields" for the full rule and rationale.

### `load_and_merge(bundled_package, bundled_resource, user_path, table_key, sticky_fields=()) -> MergeResult`

Pre-existing function; `sticky_fields` threaded straight through to
`merge_entries`. `registry._build_registry()` calls it as:

```python
load_and_merge(
    "machine_calc.data", "materials.toml", config_path, "materials",
    ("material_type",),
)
```

## `machine_calc.cli` (internal, not part of the library's public API)

### `_material_type_label(material_type: str, locale: str) -> str`

Returns a display label for a category id: the `material_type.<id>`
catalog entry if one exists, else a title-cased fallback derived from the id
(underscores and hyphens become spaces).

```python
_material_type_label("metal", "en")     # "Metal"
_material_type_label("plastic", "en")   # "Plastic"    (no catalog entry)
_material_type_label("composite-fibre", "en")  # "Composite Fibre"
```

### `_prompt_material_type_choice(material_types: list[str], default: str | None, locale: str) -> str`

Step one of the two-step selection flow. Prompts with translated labels,
returns the stable identifier the caller passed in `material_types`. Follows
the same label-dict/reverse-lookup pattern as the pre-existing
`_prompt_material_choice`/`_prompt_tool_choice`.

## Interactive CLI flow (contract observed by end users)

`run()` (`machine_calc/cli.py`) prompts, per calculation, in this order:

1. Unit system
2. Calculation mode
3. **Material type** (new)
4. Material — scoped to the chosen type via
   `list_materials(config_path=..., material_type=<chosen type>)`
5. Drilling tool
6. Drill diameter
7. Hole depth
8. Available power (mode-dependent)
9. "Run another calculation?"

Verified example (`--materials-config` adds a `"plastic"` category via a
`PVC` entry with no catalog label for `"plastic"`):

```
$ printf 'metric\n\nPlastic\nPVC\nCarbide\n10\n25\n\nn\n' \
    | python -m machine_calc --materials-config my.toml
Unit system [metric/imperial] (metric):
Calculation mode (standard, power-constrained, fixed-rpm) (standard):
Material type (Metal, Wood, Plastic):
Material (PVC):
Drilling tool (HSS, Cobalt, Carbide):
Drill diameter (mm):
Hole depth (mm):
Available power (kW, blank if unknown):
Spindle speed:     15915.5 RPM   (recommended)
...
Run another calculation? [y/N]:
```

("Plastic" here is the title-cased fallback label for `material_type =
"plastic"`, since no `material_type.plastic` catalog entry exists.)

### Cross-category default handling

If the user switches material type between repeated calculations, the
material chosen last time is not offered as a default if it doesn't belong
to the newly chosen type — `_prompt_material_choice` resolves its default
via a `label -> name` dict built only from the *current* type's material
list, so an out-of-scope previous choice simply isn't in that dict. No reset
call exists or is needed; this is a direct consequence of the existing
default-resolution mechanism (verified interactively: choosing Aluminum
under "Metal", then switching to "Wood", presents `Material (Oak, Maple,
Pine, Spruce, Fir, Plywood, MDF):` with no default shown).

## Error handling

No new exception types were introduced. `RegistryConfigError`
(`registry_config.py`, pre-existing) is unchanged; an invalid `material_type`
value never raises it — invalid values are warn-and-continue (see
data-model.md), not a load-time failure. A malformed TOML file or a
duplicate material name still raises `RegistryConfigError` exactly as before
008.

## Out of scope

No CRUD API (`create_material_type`, `update_material`,
`delete_material_type`, etc.) exists or is planned for this feature. Adding
or changing a material type is done by editing a TOML file — see
research.md, "Scope Decisions".
