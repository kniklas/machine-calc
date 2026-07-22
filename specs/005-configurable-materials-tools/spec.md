# Feature Specification: Configurable Materials & Tools

**Feature Branch**: `005-configurable-materials-tools`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "It should be simple and easy to add new materials or tools to machine-calc. Ideally, materials and tools are defined in a configuration file embedded/bundled inside the Python package itself (shipped as package data, providing sensible built-in defaults out of the box), with the ability to additionally supply an extra/override configuration file as a parameter when invoking the package from the command line (so users can add or override materials/tools without modifying the installed package). Names of materials and tools should be in English by default, with an option to provide a translation (this ties into the existing constitution Principle VIII requiring translatable user-facing messages with English fallback). Additionally, each material and tool entry should specify whether it uses metric or imperial units (since machine-calc is a metal drilling / machining calculator per specs/001-metal-drilling-calc and specs/002-constrained-calculation-modes)."

## Current State (Baseline)

`specs/001-metal-drilling-calc` and `specs/002-constrained-calculation-modes` established the
existing behavior that this feature evolves, rather than replaces:

- Workpiece materials are hard-coded Python objects in `src/machine_calc/registry.py`
  (`_MATERIALS` list of `WorkpieceMaterial` dataclass instances), each with a single English
  `name` plus canonical-metric reference cutting speed, feed, and specific cutting force.
- Drilling tools are hard-coded Python objects in
  `src/machine_calc/operations/drilling/tools.py` (`_TOOLS` list of `DrillingTool` dataclass
  instances), each with a single English `name` plus cutting-speed and feed factors relative
  to the HSS baseline.
- Adding, removing, or renaming a material or tool today requires editing these Python source
  files and shipping a new package release — there is no way for a user to add or override an
  entry without modifying the installed package.
- Reference values in both registries are stored canonically in metric units; unit conversion
  to imperial for CLI display already exists in `src/machine_calc/units.py`, but neither
  registry currently records which unit system its *reference values* were authored in — they
  are implicitly assumed metric.
- A separate TOML configuration mechanism already exists (`src/machine_calc/config.py`,
`load_configuration`) for validation bounds (`max_diameter_mm`, `max_depth_mm`), loaded from
  an optional file path and falling back to built-in defaults when the file or a key is
  absent. This feature extends that same override philosophy to materials and tools, but the
  existing bounds configuration is out of scope for this feature beyond reuse of its loading
  pattern.
- The CLI (`src/machine_calc/cli.py`, `main()`) does not currently parse any command-line
  arguments; there is no existing `--config` (or similar) flag to extend.
- All user-facing strings (including material/tool names shown in CLI prompts and output) are
  otherwise sourced through the message-catalog mechanism in `src/machine_calc/i18n.py`
  (Constitution Principle VIII), which resolves a locale from `MACHINE_CALC_LOCALE` and falls
  back to the bundled English catalog for missing locales or keys. Material/tool names
  themselves are not currently part of that catalog — they are the literal `name` field on the
  hard-coded dataclasses — so today they cannot be translated at all.

This feature externalizes material and tool definitions from hard-coded Python source into
package-bundled configuration data, adds a user-supplied override/extension file, and adds
per-entry translation and unit-system metadata — without changing the calculation formulas,
canonical-metric internal computation, or existing validation behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Built-in materials and tools work out of the box (Priority: P1)

A user installs machine-calc and runs a drilling calculation without supplying any
configuration. They see the same set of materials and tools that ship today (Mild Steel,
Stainless Steel, Aluminum, Cast Iron, Brass, Titanium; HSS, Cobalt, Carbide), with the same
reference values, and get identical calculation results to the current release.

**Why this priority**: This is the non-negotiable backward-compatibility baseline — externalizing
configuration must not silently change existing users' results or remove any built-in entry.

**Independent Test**: Run the CLI/library with no extra configuration supplied; confirm the list
of available materials and tools, and a sample calculation's results, match current (pre-feature)
behavior exactly.

**Acceptance Scenarios**:

1. **Given** no extra configuration file is supplied, **When** the user lists available materials
   or tools, **Then** the system shows exactly the built-in set shipped with the package.
2. **Given** no extra configuration file is supplied, **When** the user runs a calculation using a
   built-in material and tool, **Then** the numeric results match the values produced before this
   feature was introduced.
3. **Given** the package is installed from a distributed wheel/sdist (not run from a source
   checkout), **When** the user requests the built-in materials/tools, **Then** they are still
   available (i.e., the configuration data is packaged, not merely present in the source tree).

---

### User Story 2 - Add or override materials/tools via a user-supplied file (Priority: P1)

A user who needs a material or tool not shipped by default (e.g., a specific alloy, or a drill
coating not in the built-in list) creates their own configuration file describing the new
entry (or an override of an existing entry's reference values) and points the CLI at it via a
command-line parameter, without modifying the installed package.

**Why this priority**: This directly delivers the feature's primary goal — "simple and easy to
add new materials or tools" without editing installed package source.

**Independent Test**: Supply a user configuration file that adds one new material and overrides
one built-in tool's factors; confirm the new material appears in the list and is usable in a
calculation, and the overridden tool's factors take effect in calculation results, while all
other built-in entries remain unchanged.

**Acceptance Scenarios**:

1. **Given** a user configuration file defining a new material not present in the built-in set,
   **When** the CLI is invoked with that file supplied as a parameter, **Then** the new material
   is listed and can be selected for a calculation.
2. **Given** a user configuration file that redefines the reference values of a built-in material
   or tool (same name), **When** the CLI is invoked with that file, **Then** calculations using
   that name use the user-supplied values instead of the built-in ones.
3. **Given** a user configuration file with entries that do not conflict with any built-in name,
   **When** the CLI is invoked with that file, **Then** the effective set is the built-in entries
   plus the user's additions, with no built-in entries lost.
4. **Given** no such parameter is supplied, **When** the CLI runs, **Then** behavior is identical
   to User Story 1 (the override file is strictly additive/optional).

---

### User Story 3 - Material/tool names are translatable (Priority: P2)

A user running the CLI in a non-English locale sees material and tool names in their configured
language where a translation is provided, and automatically falls back to the English name when
no translation exists for a given entry or locale — consistent with how all other user-facing
text already behaves (Constitution Principle VIII).

**Why this priority**: Directly requested by the feature description and required for consistency
with the existing i18n principle, but depends on Story 1/2's configuration model existing first.

**Independent Test**: Define a material with an English name and one additional-language name in
configuration; run the CLI with the locale environment variable set to that language and confirm
the translated name is shown; run again with an unsupported/missing locale and confirm the
English name is shown instead.

**Acceptance Scenarios**:

1. **Given** a material or tool entry with a translated name for the active locale, **When** it is
   displayed in the CLI, **Then** the translated name is shown.
2. **Given** a material or tool entry with no translation for the active locale, **When** it is
   displayed in the CLI, **Then** the English name is shown as a fallback.
3. **Given** a material or tool entry that omits translations entirely, **When** it is displayed
   in any locale, **Then** the English name is shown (English is always present and always a
   valid fallback).
4. **Given** a user-supplied override file adds a translation for a built-in entry, **When** the
   CLI runs in that locale, **Then** the added translation is used instead of the English name.

---

### User Story 4 - Each material/tool declares its unit system (Priority: P2)

A contributor or user adding a new material or tool entry can specify whether the reference
values they are supplying are expressed in metric or imperial units, so the system can convert
them correctly regardless of which unit system the original data source used.

**Why this priority**: Improves correctness and lowers the barrier to contributing new entries
(users can copy reference data straight from imperial-unit sources), but the feature is usable
without it (defaulting to metric, today's implicit assumption) so it is not P1.

**Independent Test**: Define a new material whose reference values are supplied in imperial units
and marked as such; confirm a calculation using that material produces the same result as if the
equivalent metric-converted values had been entered directly, in both metric-mode and
imperial-mode calculations.

**Acceptance Scenarios**:

1. **Given** a material or tool entry whose configuration declares imperial reference units,
   **When** the system loads that entry, **Then** its reference values are converted to the
   canonical metric representation used internally, and calculations produce correct results in
   both metric and imperial output modes.
2. **Given** a material or tool entry whose configuration declares metric reference units (or
   omits the field), **When** the system loads that entry, **Then** its reference values are used
   as-is (today's behavior is unchanged).
3. **Given** an entry's declared unit system, **When** it is displayed to the user (e.g., in a
   listing or detail view), **Then** the declared unit system is available/visible so the origin
   of the reference values is not ambiguous.

### Edge Cases

- What happens when the user-supplied configuration file path does not exist or is not
  readable? The system MUST fall back to the built-in (bundled) materials/tools only, consistent
  with the existing `load_configuration` precedent of falling back to defaults on a missing
  file, and MUST inform the user (as a translatable, English-fallback message) rather than
  failing silently or crashing.
- What happens when the user-supplied configuration file is malformed (invalid syntax)? The
  system MUST reject the invalid file with a clear, translatable error message and MUST NOT
  silently ignore it or partially apply it; it MUST NOT crash with an unhandled exception/raw
  traceback.
- What happens when a user-supplied entry has the same name as a built-in entry? The
  user-supplied entry's values MUST take precedence (an explicit override), per User Story 2.
- What happens when a user-supplied entry's values are physically invalid (e.g., zero or
  negative cutting speed, feed, or force)? The system MUST reject that specific entry using the
  same validation rules already applied to built-in entries, with a clear error identifying which
  entry failed and why, rather than allowing an invalid entry to reach calculation logic.
- What happens when two user-supplied entries within the same override file declare the same
  name? The system MUST treat this as a configuration error and report it clearly, rather than
  silently picking one arbitrarily.
- What happens when a translation is supplied for a locale that has no bundled message catalog
  at all? The name translation MUST still be honored independent of whether other unrelated
  message-catalog strings exist for that locale (name translations are data-driven and not
  required to have a full example catalog to be usable), while still falling back to English
  when that specific locale/translation is absent.
- What happens when an entry omits the unit-system field entirely? The system MUST default to
  metric, preserving today's implicit assumption (per User Story 4, Acceptance Scenario 2).
- What happens when both a bundled default and a user override file define overlapping but not
  identical translation sets for the same entry (e.g., built-in has a French name, override adds
  a German name)? The system MUST merge per-language translations for the same entry rather than
  discarding the built-in translations wholesale when an override touches that entry, unless the
  override explicitly redefines that same language's translation (in which case the override
  wins for that language only).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ship a bundled configuration file, packaged as part of the
  installed Python package (available even when installed from a built distribution, not only
  from a source checkout), that defines all built-in workpiece materials and drilling tools
  currently hard-coded in `registry.py` and `operations/drilling/tools.py`, with no loss of any
  currently-available entry or change to its reference values.
- **FR-002**: The system MUST allow a user to supply an additional configuration file path as a
  command-line parameter when invoking the CLI, whose contents are merged with the bundled
  defaults without requiring any modification to the installed package.
- **FR-003**: When a user-supplied entry shares a name with a bundled entry, the system MUST use
  the user-supplied entry's values in place of the bundled entry's values for that name (override
  semantics), while leaving all other bundled entries unaffected.
- **FR-004**: When a user-supplied entry's name does not match any bundled entry, the system MUST
  add it to the effective set of available materials/tools (additive semantics).
- **FR-005**: The system MUST NOT require a user-supplied configuration file to be present; when
  none is supplied, or the supplied path is missing/unreadable, the effective set of
  materials/tools MUST be exactly the bundled defaults, and the system MUST surface a
  translatable notice rather than crashing when a supplied path could not be used.
- **FR-006**: The system MUST validate every material and tool entry (bundled or user-supplied)
  against the same correctness rules currently enforced on hard-coded entries (all numeric
  reference values MUST be positive; names MUST be unique within the effective set after
  merging), and MUST reject invalid entries with a specific, actionable error rather than passing
  them to calculation logic.
- **FR-007**: The system MUST reject a configuration file with malformed syntax with a clear,
  translatable error identifying that the supplied file could not be parsed, and MUST NOT apply
  any part of a file that fails to parse.
- **FR-008**: Each material and tool entry MUST support an English display name as the required
  baseline (consistent with Constitution Principle VIII's requirement that English always be
  available as a fallback).
- **FR-009**: Each material and tool entry MUST support zero or more additional per-locale
  translated display names, keyed by locale, that are used in place of the English name when the
  active locale matches and a translation is present.
- **FR-010**: When no translation exists for the active locale for a given entry, the system MUST
  display that entry's English name, consistent with the existing i18n fallback behavior
  (Constitution Principle VIII / `machine_calc.i18n.translate`).
- **FR-011**: Each material and tool entry MUST declare which unit system (metric or imperial)
  its numeric reference values are expressed in; when this is not declared, the system MUST
  default to treating the values as metric (preserving current behavior).
- **FR-012**: When an entry's declared unit system is imperial, the system MUST convert its
  reference values to the canonical metric representation used internally before they are used
  in any calculation, using the existing conversion utilities' semantics. Tool entries' factors
  are dimensionless multipliers relative to a material's own reference values, so they carry no
  independent physical unit to convert; for tool entries this requirement is satisfied by
  recording the declared `unit_system` for display (FR-013) without a numeric conversion step.
- **FR-013**: The declared unit system for a material or tool entry MUST be available to code
  that lists or displays materials/tools (i.e., not silently discarded after conversion), so the
  origin of the reference values is not ambiguous to a user inspecting available entries.
- **FR-014**: The system MUST continue to expose the same public listing/lookup capabilities
  currently provided by `list_materials`/`get_material` and `list_tools`/`get_tool`, reflecting
  the merged (bundled + user override) effective set, so existing callers of these capabilities
  are not broken.
- **FR-015**: Merging user-supplied translations for an entry that also exists in the bundled
  defaults MUST combine the two translation sets per-locale (the user's translation for a given
  locale replaces the bundled one only for that locale; other bundled locale translations for
  that same entry are preserved), rather than the user override wholesale discarding all bundled
  translations for that entry.
- **FR-016**: The system MUST treat two entries of the same kind (material or tool) with the same
  name declared more than once within the same user-supplied configuration file as a
  configuration error, reported clearly rather than silently resolved.
- **FR-017**: This feature MUST NOT change any existing calculation formula, the canonical-metric
  internal computation model, or the existing validation-bounds configuration mechanism
  (`max_diameter_mm`/`max_depth_mm` in `config.py`); it only changes how material/tool reference
  data is sourced and represented.

### Key Entities *(include if feature involves data)*

- **Material/Tool Configuration Source**: The bundled, package-shipped file providing default
  materials and tools out of the box, plus an optional user-supplied file providing additions or
  overrides; the effective set used at runtime is the result of merging the two, with
  user-supplied values taking precedence per matching name.
- **Workpiece Material Entry**: Represents a machinable material's reference machining data
  (evolution of today's `WorkpieceMaterial`): an English name, zero or more per-locale
  translated names, the declared unit system of its reference values, and the same numeric
  reference fields already tracked today (reference cutting speed, reference feed per
  revolution, specific cutting force).
- **Drilling Tool Entry**: Represents a selectable drill-bit type's reference factors (evolution
  of today's `DrillingTool`): an English name, zero or more per-locale translated names, the
  declared unit system context for its factors, and the same cutting-speed/feed factor fields
  already tracked today.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can add a brand-new material or tool, or override an existing one's
  reference values, by writing a single external file and pointing the CLI at it — with zero
  edits to the installed package's own files.
- **SC-002**: Every material and tool available before this feature remains available afterward,
  with identical calculation results, when no user override file is supplied.
- **SC-003**: A user in a non-English locale sees translated material/tool names wherever a
  translation has been supplied, and never sees a blank or broken name — every entry always
  resolves to at least its English name.
- **SC-004**: A contributor can add a new material or tool sourced from imperial-unit reference
  data without manually converting the numbers by hand, and the resulting calculations are
  numerically consistent with an equivalent metric-authored entry.
- **SC-005**: An invalid or malformed user-supplied configuration file produces a clear,
  actionable message identifying the problem, with no unhandled crash and no silent partial
  application of the bad file.

## Assumptions

- The bundled default configuration file will encode the exact materials, tools, and reference
  values presently hard-coded in `src/machine_calc/registry.py` and
  `src/machine_calc/operations/drilling/tools.py`, so this feature is a lossless externalization,
  not a data revision.
- "Configuration file" format and exact CLI flag name/spelling are implementation decisions for
  the planning phase, not user-facing scope decisions; this spec deliberately does not mandate a
  specific file format or flag syntax, only the required capabilities (bundled defaults, optional
  user override by path, override/additive merge semantics, per-locale name translation with
  English fallback, and per-entry unit-system declaration with metric-default/imperial-conversion
  behavior).
- Only material and tool *names* are addressed by the translation requirement in this feature;
  translating error/help/prompt strings is already covered by the existing i18n mechanism
  (Constitution Principle VIII) and is out of scope here except for new messages this feature
  itself introduces (e.g., invalid-configuration-file errors), which MUST follow that same
  existing mechanism.
- This feature does not introduce new calculation operations, only extends how the existing
  drilling operation's material/tool reference data is sourced; the "operation-specific vs.
  shared" boundary from Constitution Principle VI (Extensibility by Design) is preserved —
  materials remain a cross-cutting registry, drilling tools remain operation-specific.
- Only one user-supplied override file may be specified per CLI invocation; combining multiple
  override files in a single run is out of scope for this feature.
- Changing or removing entries from the bundled defaults themselves (as opposed to overriding
  them via a user-supplied file) is a package-release concern, not something this feature needs
  to support as a runtime capability.
