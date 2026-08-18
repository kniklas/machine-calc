# Feature Specification: Material Categorization System

**Feature Branch**: `008-material-categorization`

**Created**: 2026-08-18

**Status**: Implemented

**Input**: User description: "metal materials and wood should be categorised into: 'metal' and 'wood', with option to add more material types in the future (e.g. cement or plastic), while selection of the material first user selects material type, then specific material"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Selects Material Type (Priority: P1)

User needs to choose a material type (metal, wood, or a future type) as the first step of the material selection flow in the interactive CLI.

**Why this priority**: This is the core interaction pattern that scopes every downstream material choice. Without it, the material prompt lists every material in one flat, ever-growing line.

**Independent Test**: Can be fully tested by starting the REPL and verifying a "Material type" prompt appears before the "Material" prompt, lists the registered types, and rejects unknown input.

**Acceptance Scenarios**:

1. **Given** the REPL has asked for unit system and calculation mode, **When** the material step begins, **Then** a `Material type (Metal, Wood)` prompt is shown listing every registered type
2. **Given** the material-type prompt is shown, **When** the user enters a valid type, **Then** the REPL proceeds to a material prompt scoped to that type
3. **Given** the user completes a calculation and chooses to run another, **When** the material-type prompt is shown again, **Then** the previously chosen type is offered as the default

---

### User Story 2 - User Selects Specific Material (Priority: P1)

After choosing a material type, the user selects a specific material from within that type. This completes the two-step material selection workflow.

**Why this priority**: This completes the selection journey and determines which material properties feed the drilling calculation.

**Independent Test**: Can be fully tested by choosing a type and verifying only that type's materials are offered and selectable.

**Acceptance Scenarios**:

1. **Given** the user selected `Metal`, **When** the material prompt is displayed, **Then** it lists exactly the metal materials (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium) and no wood materials
2. **Given** a material list is displayed, **When** the user selects a material, **Then** the calculation proceeds using that material's cutting data
3. **Given** the user switches to a different type on a repeat calculation, **When** the material prompt is displayed, **Then** the remembered material from the previous type is not offered as a default and an explicit in-type choice is required

---

### User Story 3 - Administrator Adds a New Material Type (Priority: P2) — *Out of scope*

**Status**: Dropped. Superseded by the delivered configuration-driven design.

Originally specified as an admin CRUD API for creating material types and materials. In the delivered design a material type is created simply by writing `material_type = "<new type>"` on a `[[materials]]` entry in the bundled `materials.toml` or in a user file passed via `--materials-config`. The new type appears in the material-type prompt on the next run with no code change and no deployment, which already satisfies FR-004 and FR-005. A CRUD API would add a second, redundant way to do the same thing, so it was not built.

Consequently FR-009 (concurrent-edit conflict resolution) is moot: there is no write API, and TOML files are managed by the user's own editor and version control.

---

### User Story 4 - User Sees Which Materials Belong to a Type (Priority: P3)

The user can see, at the point of selection, exactly which materials belong to the chosen type, so they can confirm the categorization is what they expect.

**Why this priority**: This provides the context that makes the two-step flow trustworthy rather than opaque.

**Independent Test**: Can be fully tested by selecting each type in turn and verifying the offered material list matches that type's membership.

**Acceptance Scenarios**:

1. **Given** a type is selected, **When** the material prompt is rendered, **Then** it enumerates that type's members inline in the prompt text
2. **Given** a user config adds a material with a new type, **When** that type is selected, **Then** the added material appears in its list

---

### Edge Cases

- A material that omits `material_type` is grouped under `uncategorized` rather than being dropped or causing an error.
- A material with an invalid `material_type` (empty string, non-string) records a validation warning and falls back to `uncategorized`; startup continues (warn-and-continue, consistent with invalid numeric fields).
- A pre-008 user config that overrides a bundled material without mentioning `material_type` keeps the bundled type, rather than silently decategorizing it (sticky-field merge).
- A material type is never empty by construction: types are derived from the materials that declare them, so a type exists only if at least one material belongs to it.
- Invalid input at the material-type prompt is re-prompted with the list of valid choices, exactly like every other CLI choice prompt.
- An unknown type identifier with no message-catalog entry is displayed title-cased (`composite-fibre` → `Composite Fibre`) instead of failing or showing a raw key.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST prompt the user to select a material type before selecting a specific material (initial types: metal, wood)
- **FR-002**: System MUST display and accept only the materials belonging to the selected material type
- **FR-003**: System MUST remember the selected material type as the default for the next calculation within the same session
- **FR-004**: System MUST support adding new material types without code modification (e.g. cement, plastic), by declaring the type on a material in a configuration file
- **FR-005**: System MUST support assigning specific materials to each material type via the same configuration mechanism
- **FR-006**: System MUST expose the set of registered material types derived from the effective (bundled + user) material set
- **FR-006a**: Material type identifiers MUST be compared as exact strings, so one identifier denotes exactly one type
- **FR-007**: Material names MUST remain unique across the effective merged set (unchanged from feature 005); a name identifies exactly one material regardless of type
- **FR-008**: System MUST reject a material that does not belong to the selected material type
- **FR-009**: *(Reserved; intentionally omitted from v1 scope)* Conflict detection and merge resolution for concurrent edits — moot given there is no write API; configuration files are managed by the user's editor and version control
- **FR-010**: System MUST present material types in a configurable order, controlled by the order in which materials are authored in configuration (bundled entries first, then user entries)
- **FR-011**: System MUST degrade gracefully when a material's type is missing or invalid, defaulting to `uncategorized` and continuing to serve the material
- **FR-012**: Material type labels MUST be resolved through the message catalog so translations can be added later without code changes; unknown identifiers fall back to a title-cased label

### Key Entities

- **Material Type**: A free-form string identifier on a material (e.g. `metal`, `wood`, `plastic`). Not a separate stored record — the set of types is derived from the materials that declare them, which is what makes a new type require no code and no schema change.
- **Material**: An existing `WorkpieceMaterial` (name, cutting speed, feed per rev, specific cutting force, unit system, translations), extended with a `material_type` field.
- **Material Selection**: The in-session pair of chosen type and chosen material, remembered as prompt defaults across repeat calculations in the REPL loop.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach a specific material in exactly two prompts (type, then material)
- **SC-002**: The bundled catalog ships at least 2 material types with at least 5 materials each (delivered: 6 metal, 7 wood)
- **SC-003**: A new material type added to a configuration file appears in the material-type prompt on the very next run, with no code change and no deployment
- **SC-004**: The selected type and material persist as defaults for the duration of the REPL session
- **SC-005**: Type and material lookup adds no measurable startup cost, remaining within the project's resource-constrained hardware budget
- **SC-006**: A user given an invalid or out-of-type material choice is re-prompted with the valid options rather than failing the run

## Assumptions

- Initial material types are `metal` and `wood`, covering the existing bundled catalog; no material is left uncategorized in the bundled data
- Material type and material management is handled by editing TOML configuration (bundled data or `--materials-config`), requiring no schema change and no admin API
- The type is an attribute of a material rather than a separate entity, so the type set is always consistent with the material set by construction
- Future material types (cement, plastic, etc.) follow the same structure with no special handling
- This feature integrates with the existing drilling calculation only by narrowing which material the user picks; the calculation itself is unchanged
- Access control is out of scope: whoever can edit the configuration file already controls the catalog
- Existing user configuration files written before this feature continue to work unchanged, keeping the bundled type of any material they override

## Clarifications

### Session 2026-08-18

- Q: Are material type names globally unique, and are material names unique within a type or globally? → A: Type identifiers are exact strings, so one identifier denotes one type. Material names remain globally unique across the merged set, as established by feature 005.
- Q: How does this material categorization system integrate with the existing drilling/cutting calculation features? → A: Loosely coupled: categorization only scopes the material prompt; the calculation consumes the same `WorkpieceMaterial` as before.
- Q: Should material definitions support multi-language localization, or is a single language sufficient for v1? → A: v1 launches with English only; type labels resolve through the existing message catalog so translations need no code or schema change.
- Q: Can administrators bulk-import materials (CSV/JSON), or is manual entry sufficient for the v1 launch? → A: Configuration files are the import mechanism — a single TOML file can define any number of materials and types at once.
- Q: What should happen when two administrators simultaneously edit the same material definition? → A: Not applicable in the delivered design; there is no write API, and configuration files are managed by the user's editor and version control.

### Post-implementation revision 2026-08-18

The original draft of this specification described a web-style application with clicks, page refreshes, session storage, a database, and an admin CRUD surface, and assumed 100+ types and 1000+ materials. That framing did not match this project, which is a single-user interactive CLI backed by a TOML registry. The scenarios, requirements, success criteria, and assumptions above were rewritten to describe the delivered behavior; User Story 3 was dropped for the reason recorded in its section.
