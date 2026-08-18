# Phase 0 Research: Material Categorization System Design Decisions

**Feature**: [spec.md](./spec.md) | **Data model**: [data-model.md](./data-model.md)

## Executive Summary

The feature was delivered by **extending the existing shared materials
registry** (`specs/005-configurable-materials-tools`) rather than building a
new subsystem. No new package, service layer, or persistence format was
introduced. The two-step "material type → material" selection flow is
implemented with:

- one new column, `material_type` (free-form string), on each bundled/user
  TOML material entry,
- one new generic mechanism, `sticky_fields`, in the kind-agnostic merge
  layer (`registry_config.py`), so overriding a pre-existing material
  doesn't silently drop its category,
- two new/extended registry functions (`list_material_types`,
  `list_materials(..., material_type=...)`),
- one new CLI prompt step (`_prompt_material_type_choice`) inserted before
  the existing material prompt.

This section replaces an earlier draft that proposed a parallel
`machine_calc/materials/` package (domain/service/repository/i18n layers),
pydantic validation, a JSON registry file, and an admin CRUD API. None of
that was built; it is documented here only to record why it was rejected.

## Research Questions & Decisions

### 1. Where does `material_type` live?

**Decision**: As an additional key on the existing `[[materials]]` TOML
entries (`src/machine_calc/data/materials.toml`), not a separate
`[[material_types]]` table or file.

**Rationale**: The registry already has an established
bundled-TOML-plus-optional-user-override pipeline
(`registry_config.load_and_merge`) built for `005-configurable-materials-tools`.
`RawRegistryEntry.fields` already captures "every key except
`name`/`unit_system`/`translations`" generically, so `material_type` needed
zero special-casing at the parsing layer — it simply appears in
`entry.fields["material_type"]`. A separate types table would require its
own file, its own merge/duplicate-detection pass, and a join key, for no
material benefit: the spec's extensibility requirement ("declare a new
category without code changes") is satisfied just as well by a value that
has never been seen before.

**Rejected alternative**: A dedicated `MaterialType` entity/table (with id,
display name, description, order) as originally planned. Rejected because
categories have exactly one property that matters to this feature (their
identifier/label) and ordering falls out of TOML authoring order for free
(see #4 below); a full entity would add a layer with no behavior.

### 2. Type identifier representation

**Decision**: `material_type` is a **free-form, non-empty string** field on
`WorkpieceMaterial` (`registry.py`), validated but not constrained to an
enum or fixed set. Materials that omit the key default to
`DEFAULT_MATERIAL_TYPE = "uncategorized"`.

**Rationale**: The spec's core future-proofing requirement is "operators
must be able to add material types (e.g. cement, plastic) without code
changes." A closed Python `Enum` would violate that directly. Keeping it a
string means declaring `material_type = "plastic"` in a bundled or
`--materials-config` TOML file is sufficient by itself — no registry code
changes, no new prompt strings beyond an optional label.

### 3. Backward compatibility for existing user config files (sticky fields)

**Decision**: `registry_config.merge_entries()` gained a generic
`sticky_fields: tuple[str, ...] = ()` parameter, threaded through
`_load_and_merge_uncached`, `_load_and_merge_cached`, and `load_and_merge`.
When a user override entry omits a sticky key, the bundled entry's value for
that key is carried over instead of being dropped by the normal
wholesale-replace merge rule. `registry.py` calls
`load_and_merge(..., sticky_fields=("material_type",))`; `registry_config.py`
itself has no knowledge of `material_type` and stays reusable for
`operations/drilling/tools.py`.

**Rationale**: Before this feature, a user could write a `--materials-config`
file that overrides, say, the bundled `"Mild Steel"` entry's cutting
parameters. Such a file was written before `material_type` existed, so it
cannot mention the key. Without stickiness, the existing wholesale-replace
merge rule (user entry's `fields` fully replaces the bundled entry's
`fields`) would silently move that material to `"uncategorized"` on the very
first run after upgrading — a real regression for anyone with an existing
config file, not a hypothetical one.

**Rejected alternative**: Requiring every user override to also restate
`material_type`. Rejected because it breaks working configs with no warning
and no migration path.

### 4. Category ordering

**Decision**: `list_material_types()` derives the category list from the
merged material set via `dict.fromkeys(material.material_type for material in materials.values())`,
which yields **first-appearance order** (a Python `dict` preserves insertion
order and de-duplicates on first insert).

**Rationale**: The spec requires configurable category order but nothing in
the design calls for a second per-category "order" field. Because materials
are already ordered (bundled entries in file order, then any appended user
entries), first-appearance order gives category order "for free": moving a
material earlier in the TOML file, or introducing a category via an earlier
material, changes the category order with no additional schema.

**Rejected alternative**: A numeric `order` field on a separate
`MaterialType` entity. Rejected as unnecessary complexity given the above.

### 5. Label lookup for unrecognized categories

**Decision**: `cli.py::_material_type_label()` looks up the message-catalog
key `material_type.<id>` via `machine_calc.i18n.translate()`. Because
`translate()` returns the key **verbatim** when it has no entry, an absent
label is detected by `label != key` and falls back to a title-cased form of
the raw identifier (e.g. `composite-fibre` → `Composite Fibre`,
underscores/hyphens replaced with spaces).

**Rationale**: This keeps "declare a new category with zero code changes"
true for the CLI prompt too. Catalog entries only exist for
`metal`/`wood`/`uncategorized` (`locales/en.py`); any other value entered in
a TOML file is still shown as a readable label without a code or catalog
change, at the cost of losing translation for that one label until a
catalog entry is added.

### 6. Validation policy for `material_type`

**Decision**: `registry._parse_material_type()` follows the registry's
existing **warn-and-continue** policy (the same one used for invalid numeric
fields, which become `nan` but leave the material registered). A present but
invalid value (not a string, or empty/whitespace) is recorded on the
existing `MaterialValidationRecord.issues` and the material falls back to
`DEFAULT_MATERIAL_TYPE`; it is never rejected outright.

**Rationale**: Consistency with the rest of the registry's error handling
avoids introducing a second validation philosophy for one field. A material
with a bad `material_type` value is still fully usable for calculations
(its numeric fields are independent), so hard-failing the whole entry would
be disproportionate.

### 7. CLI selection flow

**Decision**: Insert one new prompt, `_prompt_material_type_choice`, before
the existing material prompt in `run()`'s REPL loop. It reuses the same
"build a label dict, prompt over labels, reverse-lookup to the stable id"
pattern as the existing `_prompt_material_choice`/`_prompt_tool_choice`, so
no new prompting primitive was needed.

**Rationale**: Minimizes new code by reusing an established prompting idiom
already proven correct (locale-aware default handling, invalid-input
re-prompt) for materials and tools.

### 8. Cross-category default handling

**Decision**: No explicit "reset the remembered material when the type
changes" code was added. When the user picks a new type, `list_materials(...,
material_type=new_type)` returns a different name list, and
`_prompt_material_choice` resolves its displayed default via
`labels_by_name.get(default)`, which returns `None` for a name that is not
in the new list — so no default is offered.

**Rationale**: An initial implementation added an explicit reset. Removing
it and running the existing test suite showed no test depended on it (the
lookup already produced `None` for out-of-scope defaults), so the explicit
reset was dead code and was deleted; the behavior is a natural consequence
of how the existing prompt-default mechanism works, verified interactively
(switching from an Aluminum/Metal selection to Wood offers no default and
lists only Oak, Maple, Pine, Spruce, Fir, Plywood, MDF).

## Scope Decisions

### User Story 3 (admin CRUD API) — dropped

**Decision**: Out of scope. No `MaterialRegistry` service, no
create/update/delete functions, no CRUD CLI subcommands were built.

**Rationale**: In the delivered design, adding a material or an entire new
material type is done by editing a TOML file — either the bundled
`src/machine_calc/data/materials.toml` or a user file passed via
`--materials-config`. That already satisfies the spec's extensibility
requirement with zero application code; a CRUD API would duplicate that
capability behind more moving parts (a mutable store, concurrency handling,
persistence) for no additional user value in a single-process CLI tool.

**Consequence**: FR-009 (conflict detection for concurrent admin edits) is
moot — it was already marked reserved for v2+ in the spec, and there is no
admin-edit code path for it to guard.

## Environment & Tooling Facts

- Python **>= 3.9** (`pyproject.toml: requires-python = ">=3.9"`); ruff/black
  target `py39`. No 3.11-only syntax was introduced.
- The only runtime dependency is `tomli` (`tomli>=2.0; python_version < '3.11'`);
  Python >= 3.11 uses the standard-library `tomllib` instead. No pydantic or
  other third-party validation library is used anywhere in the registry.
- Bundled data is **TOML**, read via `importlib.resources`, not JSON.
- Quality gates (CI and local): `ruff check src/ tests/`, `black --check src/
  tests/`, `mypy src/machine_calc`, `bandit -r src -ll`,
  `python scripts/check_maintainability.py src/`, `pytest --cov-fail-under=90`,
  and `sphinx-build -b html docs/source docs/_build/html -W`.

## Testing Delivered

- `tests/unit/shared/test_registry_material_types.py` — 30 tests covering
  bundled categorization, `material_type` filtering, extensibility (new
  category via TOML alone), backward compatibility (sticky-field merge), and
  invalid-`material_type` handling.
- `tests/integration/test_cli_material_types.py` — 11 tests covering the
  two-step prompt flow, category switching, data-driven categories, label
  localization, and the title-case fallback for unrecognized categories.
- ~30 pre-existing CLI integration tests were updated to answer the new
  "Material type" prompt.
- Final state: 284 passed, 8 skipped, 98.39% coverage; ruff/black/mypy/bandit
  clean; Maintainability Index rank A.

## Cross-References

- `specs/005-configurable-materials-tools/contracts/materials-config-schema.md`
  — canonical schema for `[[materials]]` entries, including the
  `material_type` key and its sticky-merge rule (rule 7 in that document).
- `specs/005-configurable-materials-tools/data-model.md` — the pre-existing
  merge algorithm this feature extended rather than replaced.
