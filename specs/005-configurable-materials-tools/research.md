# Phase 0 Research: Configurable Materials & Tools

**Feature**: [spec.md](./spec.md) | **Date**: 2026-07-22

This document resolves the technical unknowns needed before Phase 1 design. Each
topic follows the Decision / Rationale / Alternatives Considered format.

## 1. Configuration file format & schema shape

- **Decision**: Reuse TOML (the same format `config.py` already uses for bounds,
  research.md #3 of `001-metal-drilling-calc`), with materials and tools each
  represented as a TOML array-of-tables (`[[materials]]`, `[[tools]]`), and a
  nested sub-table for translations per entry (`[materials.translations]` /
  `[tools.translations]`, keyed by locale code). Both bundled defaults and the
  optional user-supplied override file use the *same* schema (see
  `contracts/materials-config-schema.md`), so a user-supplied file is
  structurally identical to (a subset/superset of) the bundled one — there is
  no separate "override-only" dialect to learn.
- **Rationale**: TOML array-of-tables is the natural fit for "a list of named
  records with a few scalar fields plus an optional nested map", is
  human-editable with comments (unlike JSON), and keeps a single mental model
  and a single parser dependency (`tomllib`/`tomli`) across both the existing
  bounds config and this feature's config, per FR-017's requirement not to
  introduce a second configuration mechanism.
- **Alternatives considered**: JSON was rejected for the same reason as
  `001-metal-drilling-calc` #3 (no comments). A flat `key = value` per
  material (e.g. `mild_steel.speed = 25.0`) was rejected — it cannot express a
  variable-length list of per-locale translations per entry without an
  awkward key-naming convention, whereas array-of-tables with a nested
  sub-table expresses this directly.

## 2. Bundled package-data delivery mechanism

- **Decision**: Ship two bundled default TOML files as package data —
  `src/machine_calc/data/materials.toml` (cross-cutting materials, alongside
  `registry.py`) and `src/machine_calc/operations/drilling/data/tools.toml`
  (drilling-specific tools, alongside `operations/drilling/tools.py`) — and
  read them at runtime via the standard-library `importlib.resources.files()`
  API (available since Python 3.9, matching the existing minimum version;
  research.md #1 of `001-metal-drilling-calc`). Both files are declared under
  `[tool.setuptools.package-data]` in `pyproject.toml` so they are included in
  both wheel and sdist builds, not only present in the source checkout.
- **Rationale**: `importlib.resources.files()` is the standard, dependency-free
  way to read package data that works identically whether the package is
  installed from a wheel, an sdist, or run from a source checkout (satisfying
  FR-001's "available even when installed from a built distribution"
  requirement), with no added runtime dependency (Constitution Principle V).
  Splitting the two files across `machine_calc/data/` and
  `operations/drilling/data/` mirrors the existing `registry.py` (shared) vs.
  `operations/drilling/tools.py` (operation-specific) split mandated by
  Constitution Principle VI, so a future operation (turning, milling) can ship
  its own `operations/<op>/data/tools.toml` without touching the shared
  materials file.
- **Alternatives considered**: Reading the bundled file via a hard-coded
  filesystem path relative to `__file__` was rejected — it silently breaks for
  zip-safe/zipapp installs and is exactly the anti-pattern
  `importlib.resources` exists to replace. A single combined
  `machine_calc/data/defaults.toml` (materials + tools together) was
  considered but rejected: it would blur the Principle VI shared/
  operation-specific boundary and force every future operation to edit a
  shared file to add its own tool-like data.

## 3. CLI flag design

- **Decision**: Add `argparse`-based argument parsing to `cli.py`/
  `__main__.py` (the CLI currently parses zero arguments) with a single new
  optional flag, `--materials-config PATH`, resolved once at startup
  alongside the existing once-per-session locale resolution
  (`get_locale()`). The resolved path (or `None`) is threaded through
  `list_materials()`, `list_tools()`, and every `calculate()` call for the
  session, exactly like the existing `locale` value.
- **Rationale**: A dedicated, explicitly-named flag avoids overloading the
  existing (currently CLI-unexposed) bounds `config_path` concept with a
  second, structurally unrelated file format, keeping FR-017's "do not change
  the existing validation-bounds configuration mechanism" boundary crisp.
  `argparse` is standard library (Principle V — no new dependency) and is the
  conventional choice for a single optional flag on a console-script entry
  point.
- **Alternatives considered**: Reusing the existing (unexposed) `config_path`
  parameter for both bounds and materials/tools was rejected — the two files
  have unrelated schemas and independent lifecycles (spec Assumptions:
  "existing bounds configuration is out of scope... beyond reuse of its
  loading *pattern*"); conflating them would force a user who only wants to
  add a material to also understand/avoid touching bounds keys, and vice
  versa. An environment variable (mirroring `MACHINE_CALC_LOCALE`) was
  considered but rejected — a file *path* is naturally a per-invocation CLI
  argument, not session-environment state, and the spec explicitly frames this
  as "a command-line parameter."

## 4. Merge/override algorithm

- **Decision**: A single shared helper module, `src/machine_calc/registry_config.py`,
  implements format-agnostic merge logic reused by both `registry.py`
  (materials) and `operations/drilling/tools.py` (tools):
  1. Parse the bundled TOML (always present, always valid — covered by unit
     tests) into a list of raw entry dicts.
  2. If a user path is supplied and is a readable file, parse it; on a TOML
     syntax error, raise `RegistryConfigError` (FR-007) instead of returning
     partial data. If the path is `None`, or the file does not exist / is not
     readable, treat the user entry list as empty and record a *notice* (not
     an error) for the caller to surface (FR-005).
  3. Detect duplicate names *within* the user file's own entry list for the
     same kind (material/tool) and raise `RegistryConfigError` (FR-016) before
     any merging happens.
  4. Merge by name: a user entry with a name matching a bundled entry
     replaces that entry's scalar fields and unit system wholesale, but
     *merges* the `translations` sub-table per-locale — the user's value for
     a given locale key wins for that locale only; other bundled locale keys
     for that same entry are preserved (FR-015). A user entry whose name does
     not match any bundled entry is appended (FR-004).
  5. The merged raw entries are then validated (positivity of numeric fields)
     and converted from their declared unit system to canonical metric
     (research.md #5) by the *caller* (`registry.py`/`tools.py`), which also
     constructs the existing `WorkpieceMaterial`/`DrillingTool` frozen
     dataclasses — so `registry_config.py` itself stays dataclass-agnostic
     and reusable by any future operation-specific registry.
- **Rationale**: Factoring the generic parse/fallback/duplicate-detection/
  translation-merge logic into one shared module (rather than duplicating it
  in both `registry.py` and `tools.py`) satisfies Constitution Principle VI's
  "shared behavior... MUST be factored into reusable components rather than
  duplicated"; keeping dataclass construction and unit conversion in the
  per-kind callers preserves the existing `WorkpieceMaterial`/`DrillingTool`
  types and their existing `_validate()` functions unchanged in spirit,
  satisfying FR-006's "same correctness rules currently enforced."
- **Alternatives considered**: A single generic `RegistryEntry` dataclass used
  directly by calculation code (replacing `WorkpieceMaterial`/`DrillingTool`)
  was rejected — it would break FR-014's "continue to expose the same public
  listing/lookup capabilities" and needlessly widen this feature's blast
  radius into calculation-facing code untouched by this feature (FR-017).

## 5. Unit-system declaration & conversion

- **Decision**: Add an optional `unit_system` field (`"metric"` | `"imperial"`,
  default `"metric"` when omitted, FR-011) to both material and tool TOML
  entries. For materials, when `unit_system = "imperial"`, three new
  conversion helpers are added to `units.py` (extending its existing
  mm↔in/N·m↔in-lb/kW↔HP helpers, all with cited constants per Constitution
  Principle III):
  - `ft_min_to_m_min` / `m_min_to_ft_min` for `reference_cutting_speed`.
  - `in_to_mm` / `mm_to_in` (already exist, reused as-is) for
    `reference_feed_per_rev` — a feed-per-revolution figure converts by the
    same linear length factor as a bare length, since "per revolution" is a
    dimensionless denominator.
  - `psi_to_n_per_mm2` / `n_per_mm2_to_psi` for `specific_cutting_force`
    (declared in psi when `unit_system = "imperial"`; 1 MPa = 145.037738 psi,
    N/mm² ≡ MPa).
  For **tools**, `cutting_speed_factor` and `feed_factor` are dimensionless
  multipliers relative to the material's own reference values — they carry no
  independent physical unit, so `unit_system` on a tool entry is accepted and
  stored/displayed (satisfying FR-011/FR-013's "declare" and "available/
  visible" requirements) but performs no numeric conversion, which is
  documented explicitly in `data-model.md` to avoid this being mistaken for
  an oversight.
- **Rationale**: This lets a contributor copy reference numbers straight from
  an imperial-unit source (SC-004) while all internal calculation continues
  in canonical metric (research.md #4 of `001-metal-drilling-calc`,
  unchanged by this feature per FR-017). Converting immediately at load time
  (rather than deferring conversion into calculation code) keeps
  `operations/drilling/formulas.py` completely unaware that a value's origin
  was ever imperial, preserving FR-017's "no change to any existing
  calculation formula."
- **Alternatives considered**: Requiring all entries to always be declared in
  metric (no imperial authoring) was rejected — it directly contradicts
  FR-012/SC-004. Converting at calculation time instead of load time was
  rejected — it would require threading a per-entry unit flag through
  `formulas.py`, violating FR-017's "no change to calculation formulas" and
  Constitution Principle VI's operation/shared boundary.

## 6. Configuration error handling & messaging

- **Decision**: Introduce `RegistryConfigError` (a plain `Exception` subclass
  in `registry_config.py`) carrying a message-catalog key and `str.format()`
  kwargs (mirroring how `ErrorInfo` already carries a translated message, but
  as an exception since no `CalculationResult` exists yet at CLI-startup
  config-loading time). The CLI catches this exception once at startup
  (around the first `list_materials()`/`list_tools()` call), translates it via
  `machine_calc.i18n.translate`, prints it, and exits without a raw traceback
  (FR-007). A missing/unreadable user file is *not* an error condition — it
  produces a separate translatable **notice** message (new message keys,
  `notice.materials_config.not_found` and similar) printed once at startup,
  after which the CLI proceeds using bundled defaults only (FR-005).
- **Rationale**: This distinguishes "user asked for a file that isn't there"
  (graceful, non-fatal fallback, consistent with `load_configuration`'s
  existing missing-file behavior) from "user's file exists but is broken"
  (fatal, must not partially apply, per FR-007) exactly as the spec's Edge
  Cases section requires them to be treated differently. Routing both
  through the existing `i18n.translate` mechanism keeps every new user-facing
  string compliant with Constitution Principle VIII (translatable, English
  fallback) without inventing a second messaging mechanism.
- **Alternatives considered**: Silently ignoring a malformed file (falling
  back to defaults, like the missing-file case) was rejected — it directly
  contradicts FR-007's "MUST NOT silently ignore it or partially apply it."
  Raising the built-in `tomllib.TOMLDecodeError` uncaught was rejected — it
  would surface a raw Python traceback to the end user, violating FR-007 and
  the general expectation (Constitution Principle III) that invalid input
  produces a clear, actionable error rather than a crash.

## 7. Translated display names in the CLI

- **Decision**: Extend `WorkpieceMaterial` and `DrillingTool` with a
  `translations: dict[str, str]` field (locale code → translated display
  name; empty by default). Add a small resolution helper (e.g.
  `WorkpieceMaterial.display_name(locale)` / the equivalent on `DrillingTool`)
  that returns the locale's translation if present, else the entry's English
  `name` — mirroring `i18n.translate`'s own fallback rule, but for
  data-driven names rather than catalog keys. The CLI's material/tool prompts
  are changed to the same "label dict / reverse-lookup dict" pattern already
  used for `_prompt_mode` (`labels_by_mode` / `modes_by_label`): the
  *canonical* English `name` remains the stable identifier passed to
  `calculate()` and returned by `list_materials()`/`list_tools()` (FR-014
  compatibility), while the CLI presents (and accepts back) the translated
  label for the active locale only at the prompt layer.
- **Rationale**: Keeps the public library surface (`list_materials`,
  `get_material`, `list_tools`, `get_tool`) returning stable English
  identifiers exactly as today (FR-014), while still satisfying FR-009/
  FR-010's requirement that the *displayed* name be translated with English
  fallback — the same separation of "stable key" vs. "presentation label"
  the CLI already uses for calculation modes.
- **Alternatives considered**: Translating names via the existing
  `machine_calc.locales.*` message catalog (one catalog key per material/tool
  name) was rejected — catalog keys must be stable, code-independent
  identifiers (Constitution Principle VIII), whereas material/tool names are
  *data* that this feature explicitly moves out of code and into
  configuration; forcing every new material/tool to also add a
  hand-authored catalog key in every locale file would defeat the "simple and
  easy to add" goal driving this feature.

## 8. Backward-compatible API evolution

- **Decision**: `list_materials()`, `get_material()`, `list_tools()`, and
  `get_tool()` all gain a new trailing optional parameter,
  `config_path: str | None = None`, defaulting to `None` (bundled defaults
  only — today's behavior, unchanged). `calculate()` gains a new optional
  keyword parameter, `materials_config_path: str | None = None`, threaded
  internally to the same lookups. No existing parameter, return type, or
  default behavior changes.
- **Rationale**: Directly satisfies FR-014 ("existing callers of these
  capabilities are not broken") and User Story 1's zero-config baseline —
  every existing call site (including all of today's tests) continues to
  compile and behave identically without modification.
- **Alternatives considered**: A module-level "current config path" global,
  set once and read implicitly by `get_material`/`get_tool`, was rejected —
  it would make the effective registry depend on hidden global state rather
  than an explicit, testable parameter, complicating parallel/test-isolated
  usage (each test can currently construct its own `tmp_path` config file
  independently, which a global would hinder).

## 9. Caching bundled/user TOML parses

- **Decision**: Cache the parsed-and-merged result of
  `registry_config.load_and_merge(bundled_resource, user_path, kind)` keyed on
  `(bundled_resource, user_path)` using `functools.lru_cache`, since a CLI
  session's `materials_config_path` (like its locale) is fixed for the
  session and re-parsing the same TOML file on every prompt/calculation would
  be wasted I/O.
- **Rationale**: Keeps calculation latency well within the Constitution
  Principle V legacy-hardware performance target (0.5-1.0s) even though this
  feature adds a file-parsing step ahead of every `list_materials()`/
  `get_material()` call; `lru_cache` is standard library, adding no
  dependency.
- **Alternatives considered**: No caching (re-parse every call) was
  considered simplest but rejected as an unnecessary, easily-avoided
  per-calculation I/O cost, especially for the REPL's tight prompt loop that
  calls `list_materials()`/`list_tools()` every iteration.

## Outcome

All technical unknowns needed for Phase 1 design are resolved above. No open
`NEEDS CLARIFICATION` items remain blocking Phase 1 design.
