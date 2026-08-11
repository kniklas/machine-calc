# Feature Specification: Wood Materials Support

**Feature Branch**: `007-wood-materials-support`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "add to materials hardwood, soft wood and recommend if plywood or furniture chest should be added too"

## Current State (Baseline)

Building on `specs/005-configurable-materials-tools`, which established the mechanism for adding custom materials to machine-calc:

- Materials registry (`WorkpieceMaterial` dataclass) currently supports metallic and non-metallic hard materials (Mild Steel, Stainless Steel, Aluminum, Cast Iron, Brass, Titanium).
- Each material stores canonical-metric cutting speed, feed, and specific cutting force parameters.
- The configurable materials system allows users to define custom materials via configuration files.
- Wood materials have not yet been included in the built-in registry or example configurations.

This feature extends the built-in materials registry to include common wood types used in machining operations, leveraging the configurable materials framework.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add hardwood materials to built-in registry (Priority: P1)

A woodworking shop uses machine-calc to plan drilling and cutting operations on hardwood pieces (oak, maple). They install the package and expect to see hardwood options available in the materials list alongside metals.

**Why this priority**: Hardwoods are commonly machined and are essential for enabling machine-calc to serve the woodworking community. This is the core MVP value.

**Independent Test**: List available materials after installation; confirm hardwood entries (oak, maple) are present with appropriate cutting speed parameters.

**Acceptance Scenarios**:

1. **Given** machine-calc is freshly installed, **When** the user requests the list of available materials, **Then** at least oak and maple hardwoods are included.
2. **Given** a hardwood material is selected, **When** a drilling calculation is performed, **Then** the system uses hardwood-appropriate cutting parameters and returns valid results.
3. **Given** the package is installed from a distributed wheel/sdist, **When** the user lists materials, **Then** hardwood entries are still available (packaged, not just in source).

---

### User Story 2 - Add soft wood materials to built-in registry (Priority: P1)

A carpentry or construction company uses machine-calc for softwood operations (pine, spruce, fir). Soft woods have different cutting characteristics than hardwoods and require their own set of parameters.

**Why this priority**: Soft woods are equally essential for practical woodworking use cases. Together with hardwoods (User Story 1), they complete the core wood materials support.

**Independent Test**: List available materials; confirm soft wood entries (pine, spruce, fir) are present with appropriate cutting speed parameters distinct from hardwoods.

**Acceptance Scenarios**:

1. **Given** machine-calc is freshly installed, **When** the user requests available materials, **Then** at least pine and spruce soft woods are included.
2. **Given** a soft wood material is selected, **When** a drilling calculation is performed, **Then** the system uses soft wood-appropriate parameters (which differ from hardwood parameters due to different cutting speeds and feed rates).
3. **Given** the package is installed from a distributed wheel/sdist, **When** the user lists materials, **Then** soft wood entries are available (packaged).

---

### User Story 3 - Include engineered wood materials in built-in registry (Priority: P1)

Some workshops use engineered/composite wood products (plywood, medium-density fiberboard). These materials are sufficiently common and can be reliably sourced from industry machining handbooks, making them suitable for inclusion in the MVP built-in registry.

**Why this priority**: Engineered wood products are common in woodworking and machining operations. By including them in the MVP alongside solid woods, machine-calc serves a broader range of practical use cases.

**Independent Test**: Verify that engineered wood materials (plywood, MDF) are present in the built-in registry after installation and that a calculation using an engineered wood material returns valid results.

**Acceptance Scenarios**:

1. **Given** machine-calc is freshly installed, **When** the user requests the list of available materials, **Then** at least plywood and MDF are included.
2. **Given** an engineered wood material (e.g., plywood) is selected, **When** a drilling calculation is performed, **Then** the system uses engineered-wood-appropriate parameters and returns valid results.
3. **Given** the package is installed from a distributed wheel/sdist, **When** the user lists materials, **Then** engineered wood entries are still available (packaged, not just in source).

---

### Edge Cases

- What happens when a user requests a calculation with a wood material but the cutting tool is not designed for wood (e.g., a metal-specific carbide insert)? → System should allow the request and compute results; user bears responsibility for tool compatibility.
- How does the system handle wood density variations within a species (softness varies by growth conditions)? → Built-in values use industry-standard reference values; users can override via custom configuration for specific sources.
- If a user has an older config file with metal materials only, do wood materials still appear in the built-in list? → Yes, wood materials are built-in; custom config only supplements/overrides.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include at least two hardwood materials (oak and maple) in the built-in registry with industry-standard cutting speed and feed parameters.
- **FR-002**: System MUST include at least two soft wood materials (pine and spruce) in the built-in registry with industry-standard cutting speed and feed parameters distinct from hardwoods.
- **FR-003**: Wood materials MUST follow the same `WorkpieceMaterial` dataclass schema as existing materials (name, cutting speed, feed, specific cutting force).
- **FR-004**: Wood materials MUST specify a unit system (metric or imperial) in their registry entries, consistent with `specs/005-configurable-materials-tools` design.
- **FR-005**: System MUST allow users to override or extend wood materials via custom configuration files (inheriting capability from `specs/005-configurable-materials-tools`).
- **FR-006**: Calculations using wood materials MUST return numerically valid results using the same cutting-speed and feed-rate formulas as metal materials.
- **FR-007**: System MUST include engineered wood materials (plywood, MDF) in the built-in registry with industry-standard reference values as part of the MVP. Other engineered wood types can be added via user configuration or in future releases.
- **FR-008**: System MUST validate material parameter values (cutting speed, feed, specific cutting force) at registration/load time. Invalid or missing parameters (e.g., values ≤ 0, missing required fields) MUST be logged as warnings; materials MUST still be registered to allow partial use and user override via custom configuration.
- **FR-009**: System MUST use an explicit multi-source normalization rule for built-in wood parameters: collect candidate values from Machinery's Handbook, at least one CNC machining guide, and ISO/industry-standard references where available; choose the canonical built-in value as the median of available valid sources, and record the source citations used for each parameter.

### Key Entities

- **Hardwood Material**: Species (oak, maple) with metric reference cutting speed (m/min), feed (mm/rev), and specific cutting force (N/mm²).
- **Soft Wood Material**: Species (pine, spruce, fir) with metric reference cutting speed, feed, and specific cutting force.
- **Engineered Wood Material**: Types (plywood, MDF) with reference parameters, included in the MVP built-in registry. Other engineered wood types (particle board, OSB, chipboard) can be added via user configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select from at least 6 wood materials (2+ hardwoods, 2+ soft woods, 1 plywood, 1 MDF) in the CLI/library without additional configuration.
- **SC-002**: A drilling calculation using any wood material (hardwood, soft wood, plywood, or MDF) completes successfully and produces results within ±10% of benchmark reference outputs defined by a fixed validation case set (minimum 12 cases: 2 per built-in wood material), using the same input tuples across runs.
- **SC-003**: Wood materials are identical before and after packaging (wheel/sdist distribution); no loss of data in bundling.
- **SC-004**: Documentation/release notes clearly state which wood materials are included, their category (hardwood, soft wood, engineered), and their canonical built-in parameter values.
- **SC-005**: For every built-in wood material parameter, documentation provides traceable source citations and the applied normalization method (median-of-sources) used to derive the canonical value.

## Assumptions

- **Hardwood reference values** are sourced from multiple authoritative industry references (Machinery's Handbook, CNC programming guides, ISO standards where available) and represent oak and maple as representative hardwoods; users can add other hardwoods via custom config. Cross-referencing multiple sources provides confidence in data accuracy.
- **Soft wood reference values** use industry-standard parameters from the same multi-source approach (Machinery's Handbook, CNC guides, ISO standards) for pine and spruce as representatives of the soft wood category; fir and other soft woods can be added by users via custom configuration.
- **Engineered wood reference values** (plywood, MDF) are sourced using the same multi-source methodology (Machinery's Handbook + CNC machining guides + ISO/industry standards) and represent common products; they are included in the MVP built-in registry alongside solid woods.
- **Engineered wood granularity** uses single generic entries per type (one "Plywood" entry, one "MDF" entry) rather than differentiated variants by thickness, ply-count, or density grade. This simplifies the MVP while reflecting typical machinist practice; users needing variant-specific control can create custom material entries via configuration.
- **Data validation strategy**: Material parameters (cutting speed, feed, specific cutting force) are validated at registration/load time per FR-008. Missing or invalid values (≤ 0, null) trigger a warning logged to facilitate debugging and manual review, but do not prevent material registration. This allows partial material use while flagging incomplete sourcing; users can override or extend via custom configuration.
- **Wood material parameters** (cutting speed, feed) are canonically stored in metric units (m/min, mm/rev) matching the existing material registry, with unit conversion to imperial handled by existing `src/machine_calc/units.py` functionality.
- **Calculation formulas** do not change; wood materials use the same cutting-speed and feed-rate algorithms as metals. The difference is purely in the reference parameter values.
- **No new CLI flags or library APIs** are required; wood materials are loaded via the existing `specs/005-configurable-materials-tools` configuration mechanism.
- **Testing and validation** will reuse existing unit test infrastructure from `specs/001-metal-drilling-calc` and `specs/002-constrained-calculation-modes`, with new test cases for wood materials added to those existing suites. Tests MUST cover validation scenarios (missing parameters, invalid values).
- **SC-002 benchmark protocol** uses a fixed, versioned validation case set with at least 12 cases (2 per built-in wood material), each case containing input tuple + expected reference output + tolerance rule, so test results are reproducible across contributors and CI runs.
- **i18n support** for wood material names will follow the same pattern as existing materials (defined in English by default, translatable via the `src/machine_calc/i18n.py` message catalog per Constitution Principle VIII).

## Clarifications

### Session 2026-08-11

- Q: Should engineered wood materials (plywood, MDF) be included in the built-in registry or deferred to user configuration? → A: Include in MVP alongside solid woods with industry-average reference values.
- Q: Which authoritative source(s) should be used for wood material cutting parameter reference values? → A: Multiple authoritative sources (Machinery's Handbook + CNC machining guides + ISO/industry standards) to provide higher confidence in data accuracy and balance multiple perspectives.
- Q: Which specific engineered wood types should be included in the built-in registry? → A: Plywood and MDF only. Both are common, have reliable reference values, and cover the majority of engineered wood use cases. Other types (particle board, OSB, chipboard) can be added by users via custom configuration or in a follow-up feature.
- Q: Should engineered wood materials be differentiated by variant (e.g., plywood by ply-count, MDF by density) or use single generic entries per type? → A: Single entry per type (one Plywood, one MDF). Simplifies MVP scope and reflects typical machinist practice. Users needing fine-grained control by variant can create custom material entries via configuration.
- Q: How should the system handle incomplete or invalid material parameter values (e.g., missing cutting speed, negative feed rate) discovered during registration? → A: Validate at registration/load time with warnings logged but initialization continues. Invalid/missing parameters trigger clear warnings to users, materials still register for partial use, users can override via custom config.

## Recommendation on Scope

**Regarding plywood and engineered wood materials:**

This spec **includes plywood and MDF materials in the built-in registry** as part of the MVP. Engineered wood products are common in woodworking and machining operations, and industry-average reference values can be reliably sourced from machining handbooks. This decision expands the scope of FR-007 to make engineered wood a core feature rather than a deferred option.

**Furniture chest** (as a monolithic entity) does not fit the materials registry — materials are raw workpiece materials (oak, pine, plywood), not finished products. This specification assumes "furniture chest" was mentioned as an example of an application or product that might use these materials, not as a literal registry entry.
