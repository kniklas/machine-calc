# Contract: Library API & CLI Extensions (Materials/Tools Configuration)

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This documents the additive changes this feature makes to the existing
contracts in `specs/001-metal-drilling-calc/contracts/library-api.md` and
`cli-repl.md`. It does not restate or supersede those contracts — every
existing signature, field, and behavior they describe remains valid; this
file lists only what is added.

## Library API additions

```python
def calculate(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    materials_config_path: str | None = None,   # NEW (FR-002)
) -> CalculationResult: ...

def list_materials(config_path: str | None = None) -> list[str]: ...   # NEW optional param
def get_material(name: str, config_path: str | None = None) -> WorkpieceMaterial | None: ...  # NEW optional param
def list_tools(config_path: str | None = None) -> list[str]: ...       # NEW optional param
def get_tool(name: str, config_path: str | None = None) -> DrillingTool | None: ...  # NEW optional param
```

- `config_path` (the new trailing parameter, module-local to each function)
  is the path to a user-supplied materials/tools configuration file
  (`contracts/materials-config-schema.md`); it is unrelated to
  `calculate()`'s pre-existing `config_path` parameter, which continues to
  mean only the validation-bounds file (`machine_calc.config.Configuration`,
  FR-017 — unchanged).
- Every function's behavior with `config_path=None` (the default) is
  byte-for-byte identical to its pre-this-feature behavior (FR-014, User
  Story 1) — bundled defaults only, same names, same values.
- `list_materials()` / `list_tools()` continue to return **stable English
  names** (unchanged return type/contents contract) — translated display
  names are a presentation-layer concern (research.md #7), not part of this
  return value.
- `calculate(..., materials_config_path=...)` MAY raise
  `machine_calc.registry_config.RegistryConfigError` when the supplied file
  exists but is malformed or contains a duplicate/invalid entry
  (`contracts/materials-config-schema.md` rules 2-5) — this is a new,
  narrowly-scoped exception analogous to the pre-existing allowance for "a
  malformed `config_path` file that cannot be parsed at all" already
  documented in `library-api.md`; it is not part of the `CalculationResult`
  structured-error contract (FR-015 is unaffected — normal calculation
  validation failures are still always returned, never raised). A missing or
  unreadable `materials_config_path` is **not** an error (FR-005) — it
  behaves exactly like `config_path=None`.

## New: display-name resolution (data-driven, not catalog-driven)

```python
material = get_material("Mild Steel", config_path=materials_config_path)
material.display_name(locale) -> str   # translated name, or English `name` fallback
```

Available identically on `WorkpieceMaterial` and `DrillingTool`
(data-model.md). Not part of the message catalog (`machine_calc.i18n`); see
research.md #7 for why.

## CLI (`cli.py` / `__main__.py`) additions

```text
machine-calc [--materials-config PATH]
```

- New, optional flag. Omitting it reproduces today's exact CLI behavior
  (User Story 1).
- Resolved once at startup (like locale), held fixed for the whole REPL
  session (research.md #3) — never re-read mid-session even if the
  underlying file changes.
- Startup sequence when the flag **is** supplied:
  1. If the path is missing/unreadable: print the translated notice
     (`notice.materials_config.not_found`) and proceed with bundled defaults
     only (FR-005) — this is not fatal.
  2. If the path exists but is malformed or invalid (`RegistryConfigError`):
     print the translated error and exit without entering the REPL loop and
     without a raw traceback (FR-007) — this is fatal, since the effective
     material/tool set cannot be safely determined.
- Material/tool selection prompts (`_prompt_choice` for material and tool)
  display each entry's `display_name(locale)` instead of its raw `name`
  (User Story 3), while still resolving the user's selection back to the
  canonical English `name` before calling `calculate()` (research.md #7),
  exactly as `_prompt_mode` already does for calculation modes.

## Unchanged

- `contracts/cli-repl.md`'s prompt *sequence* (unit system → mode → material
  → tool → diameter → depth → mode-specific inputs → result) is unchanged;
  only the material/tool prompts' *displayed labels* change (translated
  instead of raw English), and only when a translation exists for the active
  locale.
- `contracts/library-api.md`'s `CalculationResult` shape, error codes, and
  "never raises for expected validation failures" guarantee are unchanged.
