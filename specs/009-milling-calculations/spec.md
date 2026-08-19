# Feature Specification: Milling Calculations Module

**Feature Branch**: `009-milling-calculations`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Add a feature which allows calculation of milling parameters, in REPL mode user first select machining operation"

## Clarifications

### Session 2026-08-19

- Q: What scope of milling should this feature cover initially? → A: Both end milling and face milling as distinct sub-operations, each with its own formulas. *(Recorded verbatim. A later design decision — see FR-007 and Assumptions — kept the two sub-operations distinct in tooling, inputs, labelling and validation, while allowing them to share one internal formula implementation, because the full-engagement assumption makes their arithmetic identical.)*
- Q: How should the user specify feed for milling calculations? → A: Feed per tooth (chip load, mm/tooth or in/tooth) combined with the number of flutes/teeth on the tool.
- Q: The spec didn't include a "length of cut" (travel distance) input needed to compute estimated machining time — how should this be handled? → A: Add a required "length of cut" input (mm/in) that the user enters directly, used with the calculated feed rate to compute machining time.
- Q: What should the milling torque/power calculation be based on? → A: Specific cutting force (kc, N/mm²) per material, combined with chip cross-sectional area — the industry-standard approach for milling.
- Q: For face milling, should the formulas account for cutter offset/engagement position (chip-thinning effects)? → A: No — assume full/symmetric cutter engagement (simple average chip thickness = feed per tooth); no separate entry/exit angle or offset input.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select a Machining Operation Before Calculating (Priority: P1)

A machinist or manufacturing engineer starts the interactive text interface (REPL) and is first asked which machining operation they want to perform (e.g., drilling or milling) before any operation-specific prompts (material, tool, dimensions) appear. Choosing an operation routes the user into that operation's own prompt flow and calculation logic.

**Why this priority**: This is the entry point for every other capability in this feature. Without an explicit operation-selection step, the REPL cannot support more than one operation, and neither end-milling nor face-milling calculations (User Stories 2 and 3) can be reached.

**Independent Test**: Can be fully tested by launching the interactive text interface and verifying it prompts for an operation choice (drilling vs. milling) before any material/tool/dimension prompts, that selecting "drilling" reproduces the existing drilling flow unchanged, and that selecting "milling" leads into a milling-specific sub-flow.

**Acceptance Scenarios**:

1. **Given** a user launches the interactive text interface, **When** it starts, **Then** the first prompt asks the user to choose a machining operation from the available operations (at minimum, drilling and milling).
2. **Given** a user selects "drilling", **When** they proceed, **Then** the interface behaves exactly as the existing drilling calculation flow (material, tool, diameter, depth, etc.).
3. **Given** a user selects "milling", **When** they proceed, **Then** the interface next asks them to choose a milling sub-operation (end milling or face milling) before prompting for material, tool, and dimensions.
4. **Given** a user enters an unrecognized operation choice, **When** they submit it, **Then** the interface rejects the input with a clear validation message and re-prompts for a valid operation choice.
5. **Given** a user completes one calculation and chooses to run another, **When** the loop restarts, **Then** they are given the opportunity to change the previously selected operation (not forced to repeat the same one).

---

### User Story 2 - Calculate End Milling Parameters Interactively (Priority: P1)

Having selected "milling" then "end milling", the user selects a workpiece material and an end-mill tool, and enters the tool diameter, number of flutes/teeth, axial depth of cut, radial depth (width) of cut, feed per tooth, and length of cut (the travel distance to be machined), so the module calculates the recommended spindle speed (RPM), feed rate (table feed), estimated machining time, material removal rate, and the torque and power required. Torque and power are derived from the material's specific cutting force (kc) and the chip cross-sectional area, consistent with standard milling practice. As with drilling, the tool's/machine's available power rating can optionally be supplied for a feasibility check; if it is not known, the module still reports the power the operation itself requires.

**Why this priority**: End milling (slotting, pocketing, peripheral/profile milling) is the most common milling operation and the primary reason a machinist would reach for this feature; it must work before face milling is layered on.

**Independent Test**: Can be fully tested by running the interactive text interface, selecting milling → end milling, entering a material, tool, diameter, number of flutes, axial/radial depth of cut, and feed per tooth, then verifying the output returns spindle speed, feed rate, material removal rate, machining time, torque, and power matching known reference values for that combination; and by verifying the power result is still produced when the tool's power rating is left unknown.

**Acceptance Scenarios**:

1. **Given** a user has selected a workpiece material and end-mill tool and entered valid diameter, number of flutes, axial depth of cut, radial depth of cut, feed per tooth, and length of cut, **When** they request a calculation, **Then** the interface displays spindle speed (RPM), feed rate, material removal rate, estimated machining time, torque, and power.
2. **Given** a user enters a tool diameter, depth of cut, or feed per tooth of zero or a negative value, **When** they request a calculation, **Then** the interface rejects the input with a clear validation message and performs no calculation.
3. **Given** a user has not yet selected a material or an end-mill tool, **When** they request a calculation, **Then** the interface prompts them to make the missing selection(s) before proceeding.
4. **Given** a user selects a different end-mill tool for the same material, **When** the calculation refreshes, **Then** the recommended spindle speed, feed rate, torque, and power reflect the selected tool's own cutting parameters and number of flutes.
5. **Given** a user knows and supplies their tool's or machine's available power rating, **When** the estimated power required exceeds that rating, **Then** the interface displays a clear warning that the operation may not be feasible with that tool/machine.
6. **Given** a user does not know their tool's or machine's power rating, **When** they request a calculation, **Then** the interface still calculates and displays the estimated power the operation requires, without attempting a feasibility comparison.
7. **Given** a radial depth of cut greater than the tool diameter is entered, **When** the user requests a calculation, **Then** the interface rejects the input with a clear validation message, since the radial depth of cut cannot exceed the tool diameter.

---

### User Story 3 - Calculate Face Milling Parameters Interactively (Priority: P2)

Having selected "milling" then "face milling", the user selects a workpiece material and a face-mill tool, and enters the tool (cutter) diameter, number of inserts/teeth, axial depth of cut, width of cut, feed per tooth, and length of cut (the travel distance to be machined), so the module calculates the recommended spindle speed (RPM), table feed rate, estimated machining time, material removal rate, and the torque and power required, using the milling torque/power model derived from the material's specific cutting force (kc) and chip cross-sectional area, with face-milling-specific inputs, labelling (width of cut) and validation, and assuming full/symmetric cutter engagement (no chip-thinning/entry-exit-angle modeling for this feature).

**Why this priority**: Face milling is a distinct, common operation (e.g., surfacing large flat areas) with its own tooling, input semantics and engagement geometry; it extends the module's coverage but is not required for the module to deliver initial value, so it is prioritized after end milling.

**Independent Test**: Can be fully tested by running the interactive text interface, selecting milling → face milling, entering a material, tool, cutter diameter, number of inserts, axial depth of cut, width of cut, feed per tooth, and length of cut, then verifying the output returns spindle speed, feed rate, material removal rate, machining time, torque, and power matching known reference values for that combination.

**Acceptance Scenarios**:

1. **Given** a user has selected a workpiece material and face-mill tool and entered valid cutter diameter, number of inserts, axial depth of cut, width of cut, feed per tooth, and length of cut, **When** they request a calculation, **Then** the interface displays spindle speed (RPM), feed rate, material removal rate, estimated machining time, torque, and power.
2. **Given** a user enters a cutter diameter, width of cut, or feed per tooth of zero or a negative value, **When** they request a calculation, **Then** the interface rejects the input with a clear validation message and performs no calculation.
3. **Given** a width of cut greater than the cutter diameter is entered, **When** the user requests a calculation, **Then** the interface rejects the input with a clear validation message, since the width of cut cannot exceed the cutter diameter.
4. **Given** a user knows and supplies their tool's or machine's available power rating, **When** the estimated power required exceeds that rating, **Then** the interface displays a clear warning that the operation may not be feasible with that tool/machine.

---

### User Story 4 - Embed Milling Calculations in Another Application (Priority: P1)

A software developer building their own user interface (graphical, web, or otherwise) wants to reuse the same end-milling and face-milling calculation logic as a callable library, passing in the relevant tool/material/geometry parameters and (optionally) a known tool/machine power rating, and receiving structured results back—including torque and power—without needing to build or invoke the interactive text interface.

**Why this priority**: Consistent with the existing drilling module, the calculation engine must work standalone as a library from day one, since both the interactive text interface and any future application build on the same underlying logic.

**Independent Test**: Can be fully tested by calling the module's end-milling and face-milling calculation functions directly from another Python program with given inputs, and verifying the returned structured results (including torque and power) match the values produced by the interactive text interface for identical inputs.

**Acceptance Scenarios**:

1. **Given** a calling program supplies valid parameters for an end-milling or face-milling calculation directly to the library, **When** it requests a calculation, **Then** the library returns a structured result containing spindle speed, feed rate, material removal rate, machining time, torque, and power, without requiring any interactive text prompts.
2. **Given** a calling program supplies an invalid input (e.g., zero or negative feed per tooth, or radial/width of cut exceeding tool diameter), **When** it requests a calculation, **Then** the library reports a clear, structured error instead of raising an unhandled failure or returning an incorrect result.
3. **Given** the same inputs are provided once through the interactive text interface and once through direct library calls, **When** both calculations run, **Then** they produce identical results.
4. **Given** a calling program supplies a known tool/machine power rating, **When** the estimated power required exceeds it, **Then** the library's structured result includes a feasibility warning; **when** the power rating is omitted, **Then** the library still returns the estimated power requirement without a feasibility warning.
5. **Given** a calling program supplies a `locale` parameter, **When** an error or feasibility warning occurs, **Then** the library's structured result contains the message text localized per that parameter, falling back to English for any missing translation.

---

### Edge Cases

- What happens when the entered tool diameter, number of flutes/teeth/inserts, axial depth of cut, radial depth/width of cut, or feed per tooth is non-numeric, missing, or extremely large (e.g., outside realistic machining ranges)?
- How does the module handle a workpiece material that is not in the supported material list, or one whose milling reference data is unusable (e.g. a missing or non-positive specific cutting force, which torque and power depend on)? The module rejects the request with a clear, structured error naming the material and the offending field (FR-010) and performs no calculation. There is no separate "unsupported material/tool combination" state for milling: any registered milling tool works with any material whose reference data is valid.
- How does the module handle a radial depth (or width) of cut greater than the tool/cutter diameter? Rejected with a clear validation message; no calculation is performed.
- What happens when calculated feed rate or spindle speed would exceed practical machine limits? Out of scope for this feature — consistent with drilling, the module does not model a machine's maximum RPM or feed rate; only the tool/machine power feasibility check applies.
- How does the module behave when the tool's or machine's power rating is left unspecified (unknown)? The estimated power requirement is still calculated and reported, without a feasibility comparison.
- How does the REPL behave if a user picks "milling" but then wants to switch to "drilling" (or vice versa) without restarting the program? The run-again loop lets the user re-select the operation, not just re-enter operation-specific values.
- How does the library-facing interface (User Story 4) report errors so calling programs can handle them programmatically rather than as human-readable text only?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interactive text interface (REPL) MUST prompt the user to select a machining operation (at minimum: drilling, milling) as the first step, before any operation-specific prompts (material, tool, dimensions) are shown.
- **FR-002**: Selecting "drilling" MUST preserve the existing drilling calculation flow and results unchanged.
- **FR-003**: Selecting "milling" MUST prompt the user to select a milling sub-operation — end milling or face milling — before any material/tool/dimension prompts for that sub-operation are shown.
- **FR-004**: The system MUST allow users to calculate end-milling parameters by selecting a workpiece material and an end-mill tool and entering tool diameter, number of flutes/teeth, axial depth of cut, radial depth of cut, feed per tooth (chip load), and length of cut (travel distance).
- **FR-005**: The system MUST calculate, for end milling, the recommended spindle speed (RPM), table feed rate, material removal rate, estimated machining time, and the estimated torque and power required, with torque and power derived from the workpiece material's specific cutting force (kc) and the chip cross-sectional area.
- **FR-006**: The system MUST allow users to calculate face-milling parameters by selecting a workpiece material and a face-mill tool and entering cutter diameter, number of inserts/teeth, axial depth of cut, width of cut, feed per tooth (chip load), and length of cut (travel distance).
- **FR-007**: The system MUST calculate, for face milling, the recommended spindle speed (RPM), table feed rate, material removal rate, estimated machining time, and the estimated torque and power required, based on the material's specific cutting force and chip cross-sectional area, assuming full/symmetric cutter engagement without chip-thinning or entry/exit-angle modeling. Face milling MUST be a separately selectable sub-operation with its own tool set, its own input labelling (width of cut rather than radial depth of cut), and its own validation, so that a future refinement to either sub-operation's physical model can be made independently of the other.
- **FR-008**: The system MUST reject a tool diameter, number of flutes/teeth/inserts, axial depth of cut, radial depth/width of cut, feed per tooth, or length of cut of zero, negative, non-numeric, or missing value, with a clear validation message, and perform no calculation. A number of flutes/teeth/inserts that is numeric but not a whole number (e.g. `4.5`) MUST likewise be rejected, since a cutter cannot have a fractional number of teeth.
- **FR-009**: The system MUST reject a radial depth of cut (end milling) or width of cut (face milling) that exceeds the tool/cutter diameter, with a clear validation message, and perform no calculation.
- **FR-010**: The system MUST reject a request whose selected workpiece material has missing or invalid reference data (in particular a missing or non-positive specific cutting force, which milling torque/power depend on), with a clear, structured error naming the material and the offending field; no calculation is performed. Any registered milling tool is usable with any material whose reference data is valid — unlike drilling, milling defines no separate per-combination reference table, so there is no "unsupported combination" state beyond unusable material data.
- **FR-011**: Users MAY optionally supply a known tool/machine power rating; when supplied and the estimated power required exceeds it, the system MUST display/return a clear feasibility warning. When not supplied, the system MUST still calculate and report the estimated power requirement without a feasibility comparison.
- **FR-012**: The end-milling and face-milling calculation logic MUST be callable as a library (independent of the interactive text interface), returning a structured result object with a distinct error/warning field (error code + message), consistent with the drilling module's library API, and MUST never raise exceptions for expected validation failures.
- **FR-013**: The system MUST support both metric and imperial unit systems for milling inputs and outputs (diameter, depth of cut, feed per tooth, machining time in minutes, torque, power), consistent with the drilling module's unit handling.
- **FR-014**: Milling-specific operation logic (end-milling and face-milling formulas) MUST live behind per-operation modules/interfaces, following the same architectural pattern as the existing drilling module, so future milling refinements or additional operations do not require modifying unrelated operations' code.
- **FR-015**: Milling workpiece materials and tools MUST be defined via the same extensible registry/configuration mechanism already used for drilling materials and tools, allowing new milling materials or tools to be added via configuration rather than code changes. Each tool kind (drilling tool, end-mill tool, face-mill tool) MUST occupy its own distinct, independently addressable section of the configuration format, so that adding or overriding a milling tool can never alter, invalidate, or fail the loading of another operation's tool set.
- **FR-016**: All user-facing text introduced for milling (REPL prompts, labels, error/warning messages) MUST be sourced from the existing message-catalog/localization mechanism, consistent with the rest of the module.
- **FR-017**: When a user completes a calculation and chooses to run another, the interface MUST allow them to re-select the machining operation (and milling sub-operation, if applicable) rather than forcing them to repeat the previously selected one.
- **FR-018**: The system MUST validate milling inputs against configurable realistic upper bounds (maximum cutter diameter, maximum depth/width of cut, maximum length of cut), rejecting values above those bounds with a clear validation message. Defaults MUST be usable without any configuration, and MUST be overridable through the same optional configuration file already used to override drilling's diameter/depth bounds — not a second, separate file.

### Key Entities *(include if feature involves data)*

- **Machining Operation**: The top-level user selection in the REPL (drilling, milling) that routes to an operation-specific calculation flow.
- **Milling Sub-Operation**: The choice within milling (end milling, face milling) that determines which set of formulas and input parameters apply.
- **Milling Tool**: An end-mill or face-mill tool definition, identified by name and carrying a cutting-speed factor that multiplies the workpiece material's reference cutting speed, analogous to the existing `DrillingTool`. The number of flutes/teeth/inserts and the feed per tooth are **not** properties of this entity — they vary per physical tool and per cutting-data chart, so they are supplied as per-calculation inputs instead.
- **Milling Material Reference Data**: Per-material reference values used for milling calculations, including a specific cutting force (kc, N/mm²) used to derive torque and power from chip cross-sectional area, alongside the existing reference cutting-speed/feed values already used by drilling.
- **Milling Calculation Inputs**: Tool/cutter diameter, axial depth of cut, radial depth of cut (end milling) or width of cut (face milling), feed per tooth, length of cut, workpiece material, milling tool, unit system, and optional known power rating.
- **Milling Calculation Result**: Structured output containing spindle speed, feed rate, material removal rate, estimated machining time, torque, power, and an error/warning field, mirroring the existing drilling result structure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from launching the interactive text interface to seeing a complete set of end-milling results (spindle speed, feed rate, MRR, machining time, torque, power) in at most 14 prompts, of which at most 12 require typing a value (the optional power rating and every prompt offering a remembered default can be accepted with a single Enter keypress).
- **SC-002**: For a given material/tool/geometry combination, the calculated spindle speed, feed rate, material removal rate, torque, and power for both end milling and face milling are each individually within 5% of published reference values for that combination.
- **SC-003**: 100% of invalid milling inputs (zero/negative/non-numeric values, or radial/width of cut exceeding tool diameter) are rejected with a clear validation message and never produce a calculation result.
- **SC-004**: A developer embedding the module as a library obtains identical milling results to the interactive text interface for the same inputs, in 100% of tested cases.
- **SC-005**: Selecting "drilling" from the new operation-selection prompt reproduces existing drilling behavior with zero regressions, verified across the existing drilling test suite.

## Assumptions

- The interactive text interface currently jumps directly into the drilling flow because drilling is the only operation; this feature adds an explicit operation-selection step ahead of it without altering drilling's own prompts or logic.
- End milling and face milling are modeled as two distinct sub-operations under "milling," each with its own tools, inputs, labelling and validation, consistent with how the constitution anticipates growth beyond drilling into other metal machining operations.
- Feed is specified as feed per tooth (chip load) combined with the tool's number of flutes/teeth/inserts, rather than a directly entered feed rate, matching how milling tools are specified in practice; the module derives the resulting table feed rate from these inputs.
- Milling materials and tools are configured via the same extensible registry/configuration mechanism already used for drilling (per FR-015), so this feature does not introduce a second, incompatible configuration format.
- No machine RPM/feed-rate limit is modeled for milling, consistent with the existing drilling module's scope — only the power feasibility check applies.
- Estimated machining time is reported in minutes, consistent with the drilling module's convention.
- Depth-of-cut terminology follows standard machining usage: axial depth of cut (ap) is the cut depth along the tool axis, and radial depth of cut / width of cut (ae) is the cut width perpendicular to the tool axis.
- Length of cut is a required, directly entered input (the linear travel distance to be machined), analogous to drilling's hole depth, and is used with the calculated feed rate to compute estimated machining time.
- Milling torque and power are calculated from each workpiece material's specific cutting force (kc, N/mm²) and the instantaneous chip cross-sectional area, per standard milling engineering practice, rather than reusing drilling's cutting-speed-based power model.
- Face milling assumes full/symmetric cutter engagement (average chip thickness equal to feed per tooth); cutter offset, entry/exit angle, and chip-thinning effects are out of scope for this feature. Because that assumption makes the two sub-operations' underlying arithmetic identical, end milling and face milling remain separately selectable modules with their own tools, labels, and validation, but MAY share a single internal formula implementation rather than duplicating it (FR-007, FR-014).
- The power the module reports is **net cutting power** at the cutter (the power the cut itself consumes), not motor/input power; no machine drive-efficiency factor is applied. A user-supplied power rating is therefore compared on the same net basis (FR-011). This matches the existing drilling module's convention.
- Milling supports only the standard calculation mode in this feature. The drilling module's power-constrained and fixed-RPM modes are not offered for milling, so the milling prompts never ask for a calculation mode.
- Milling defines no per-material/per-tool combination reference table: any registered milling tool may be used with any material whose reference data is valid, so the only combination-level failure is unusable material reference data (FR-010).
