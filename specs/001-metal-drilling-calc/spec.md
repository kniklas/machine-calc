# Feature Specification: Metal Drilling Calculations Module

**Feature Branch**: `001-metal-drilling-calc`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Metal drilling calculations module"

## Clarifications

### Session 2026-07-09

- Q: What unit system should the module support for diameter, depth, feed, power, and torque? → A: Both metric and imperial, with the user/caller selecting the unit system per session/request.
- Q: What interaction style should the interactive text interface use? → A: Interactive REPL that prompts step-by-step for material, tool, diameter, depth, and unit system, and loops to allow further calculations.
- Q: What upper bounds should validation enforce on drill diameter and hole depth? → A: Fixed realistic default max bounds (diameter ≤100 mm/4in, depth ≤500 mm/20in), overridable via a configuration file.
- Q: How should the module handle a material/drilling tool combination with no defined reference parameters? → A: Reject with a clear structured error stating the combination has no defined reference parameters; no calculation is performed.
- Q: How should the library API report validation/error conditions to calling programs? → A: Always return a structured result object with a distinct error/warning field (error code + message); never raise exceptions for expected validation failures.
- Q: What unit should estimated machining time be reported in? → A: Minutes (fractional, e.g., 0.42 min), regardless of the selected unit system.
- Q: How do a drilling tool's cutting-speed/feed characteristics combine with a workpiece material's reference values to produce the recommended spindle speed and feed rate? → A: Multiplicative — the tool applies a cutting-speed factor and a feed factor that multiply the material's reference cutting speed and feed-per-revolution values, respectively.
- Q: Does SC-002's "within 5%" tolerance apply independently to each calculated value or as an aggregate across all four? → A: Independently — spindle speed, feed rate, torque, and power MUST each individually be within 5% of the published reference value.
- Q: Should the module model a machine's maximum RPM/feed-rate as a feasibility check, similar to FR-012's power check? → A: Out of scope for this feature — no machine RPM/feed-rate limit is modeled; only the power feasibility check (FR-012) applies.

### Session 2026-07-10

- Q: How should a user of the interactive REPL select a non-default (non-English) locale? → A: Environment variable (e.g. `MACHINE_CALC_LOCALE`) read at startup; no new REPL prompt step is added.
- Q: What format should locale message-catalog files use? → A: Python module per locale (e.g. `locales/en.py`, a `dict[str, str]`); no JSON/YAML parsing or gettext toolchain dependency required.
- Q: What is the initial scope for actual translated languages beyond English? → A: Infrastructure only — ship the English catalog now; no other language is shipped as part of this feature.
- Q: Should the CLI/library auto-detect locale from the OS/system locale (e.g. `LANG`/`LC_ALL`) as an additional fallback? → A: No — rely solely on `MACHINE_CALC_LOCALE`, defaulting to English if unset; no OS locale detection.
- Q: How should the message catalog handle messages that include dynamic values (e.g. "Unknown workpiece material: {material}")? → A: `str.format()`-style named placeholders in catalog strings (e.g. `{material}`), populated at lookup time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Core Drilling Parameters Interactively (Priority: P1)

A machinist or manufacturing engineer, working directly in an interactive text-based interface, enters the drill diameter, workpiece material, drilling tool, and hole depth so the module can calculate the recommended spindle speed (RPM), feed rate, estimated machining time, and the torque and power required to drill the hole. The tool's available power rating can be supplied as a known input; if it is not known, the module still determines and reports the power the operation itself requires, so the user can judge what power of tool or machine is needed.

**Why this priority**: This is the fundamental capability of the module. Without it, no other drilling calculation feature has value. It directly answers the machinist's most common questions: "What settings do I use to drill this hole safely and efficiently?" and "What power/torque does this operation need, and is my tool capable of it?"

**Independent Test**: Can be fully tested by running the interactive text interface, entering a drill diameter, selecting a material and a drilling tool, and entering hole depth, then verifying the output returns spindle speed, feed rate, machining time, torque, and power that match known reference values for that material/tool/diameter combination; and by verifying the power result is still produced when the tool's power rating is left unknown.

**Acceptance Scenarios**:

1. **Given** a user has selected a workpiece material and drilling tool and entered a valid drill diameter and hole depth, **When** they request a calculation, **Then** the interface displays the recommended spindle speed (RPM), feed rate, estimated machining time, and the estimated torque and power required.
2. **Given** a user enters a drill diameter of zero or a negative value, **When** they request a calculation, **Then** the interface rejects the input with a clear validation message and performs no calculation.
3. **Given** a user has not yet selected a material or a drilling tool, **When** they request a calculation, **Then** the interface prompts them to make the missing selection(s) before proceeding.
4. **Given** a user selects a different drilling tool for the same material and diameter, **When** the calculation refreshes, **Then** the recommended spindle speed, feed rate, torque, and power reflect the selected tool's own cutting parameters (which may differ from other tools for the same material).
5. **Given** a user knows and supplies their tool's or machine's available power rating, **When** the estimated power required exceeds that rating, **Then** the interface displays a clear warning that the operation may not be feasible with that tool/machine.
6. **Given** a user does not know their tool's or machine's power rating, **When** they request a calculation, **Then** the interface still calculates and displays the estimated power the operation requires, without attempting a feasibility comparison.

---

### User Story 2 - Embed Calculations in Another Application (Priority: P1)

A software developer building their own user interface (graphical, web, or otherwise) wants to reuse the same drilling calculation logic as a callable library, passing in drill diameter, material, tool, hole depth, and (optionally) a known tool/machine power rating, and receiving structured results back—including torque and power—without needing to build or invoke the interactive text interface.

**Why this priority**: The calculation engine must work standalone as a library from day one, since both the interactive text interface and any future application build on the same underlying logic. Treating this as equally foundational to User Story 1 avoids rework later.

**Independent Test**: Can be fully tested by calling the module's calculation functions directly from another Python program with a given diameter, material, tool, depth, and optional power rating, and verifying the returned structured result (including torque and power) matches the same values produced by the interactive text interface for identical inputs.

**Acceptance Scenarios**:

1. **Given** a calling program supplies valid drill diameter, hole depth, material, and drilling tool values directly to the library, **When** it requests a calculation, **Then** the library returns a structured result containing spindle speed, feed rate, machining time, torque, and power, without requiring any interactive text prompts.
2. **Given** a calling program supplies an invalid input (e.g., zero or negative diameter) to the library, **When** it requests a calculation, **Then** the library reports a clear, structured error instead of raising an unhandled failure or returning an incorrect result.
3. **Given** the same inputs are provided once through the interactive text interface and once through direct library calls, **When** both calculations run, **Then** they produce identical results.
4. **Given** a calling program supplies a known tool/machine power rating, **When** the estimated power required exceeds it, **Then** the library's structured result includes a feasibility warning; **when** the power rating is omitted, **Then** the library still returns the estimated power requirement without a feasibility warning.
5. **Given** a calling program supplies a `locale` parameter, **When** an error or feasibility warning occurs, **Then** the library's structured result contains the message text localized per that parameter, falling back to English for any missing translation.

---

### Edge Cases

- What happens when the entered drill diameter, hole depth, or other numeric input is non-numeric, missing, or extremely large (e.g., outside realistic machining ranges)?
- How does the module handle a workpiece material that is not in the supported material list?
- How does the module handle a drilling tool that is not in the supported tool list, or a tool/material combination with no defined reference parameters? The module rejects the request with a clear, structured error (see FR-010) and performs no calculation.
- How does the module handle a hole depth greater than commonly available drill lengths (deep-hole drilling scenarios)?
- What happens when calculated feed rate or spindle speed would exceed practical machine limits? Out of scope for this feature — the module does not model a machine's maximum RPM or feed rate; only the tool/machine power feasibility check (FR-012) applies.
- How does the module behave when the tool's or machine's power rating is left unspecified (unknown)?
- How does the library-facing interface (User Story 2) report errors so calling programs can handle them programmatically rather than as human-readable text only?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST expose its drilling calculation logic as a callable library so it can be embedded and invoked directly by other Python programs that provide their own user interface, independent of any interactive text interface.
- **FR-002**: The module MUST provide an interactive text-based interface, built on top of the same calculation logic used by the library, for direct human use. This interface MUST be a step-by-step, prompt-driven (REPL-style) session: it prompts the user in sequence for unit system, material, drilling tool, drill diameter, and hole depth (and optional power rating), displays the calculation result, and then loops to allow further calculations or input changes without restarting the program. All prompts and displayed text MUST be sourced from the message catalog (FR-019), not hard-coded; the active locale is read once from the `MACHINE_CALC_LOCALE` environment variable at startup (FR-019) and is not part of this prompt sequence.
- **FR-003**: The module MUST allow drill diameter, hole depth, workpiece material, and drilling tool to be supplied as inputs for a drilling operation, whether via the interactive text interface or direct library calls.
- **FR-004**: The module MUST provide a predefined list of common workpiece materials, each associated with standard reference cutting speed and feed-per-revolution values.
- **FR-005**: The module MUST provide a predefined list of drilling tools (e.g., differing by material composition such as high-speed steel, cobalt, or carbide), each with its own reference cutting speed and feed adjustments, so that selecting a different tool for the same material and diameter can change the recommended results.
- **FR-006**: The module MUST calculate the recommended spindle speed (RPM) based on the selected material's reference cutting speed multiplied by the selected drilling tool's cutting-speed factor, combined with the entered drill diameter.
- **FR-007**: The module MUST calculate the recommended feed rate based on the selected material's reference feed-per-revolution value multiplied by the selected drilling tool's feed factor, combined with the calculated spindle speed.
- **FR-008**: The module MUST calculate the estimated machining time, in minutes (fractional, regardless of the selected unit system), based on hole depth, feed rate, and a standard allowance for drill point engagement.
- **FR-009**: The module MUST validate all numeric inputs (drill diameter, hole depth) and reject zero, negative, non-numeric, or out-of-range values, reporting a clear, actionable error (sourced from the message catalog per FR-019) in both the interactive text interface and the library API. Default maximum bounds are drill diameter ≤100 mm (≈4 in) and hole depth ≤500 mm (≈20 in); these defaults MUST be overridable via a configuration file without requiring code changes.
- **FR-010**: The module MUST require a material selection and a drilling tool selection before performing any calculation and MUST report the missing selection(s) (sourced from the message catalog per FR-019), whether via an interactive prompt (text interface) or a structured error (library). If the selected material/drilling tool combination has no defined reference cutting parameters, the module MUST reject the request with a clear, structured error stating the combination is unsupported, and MUST NOT perform a calculation or fall back to generic/default values.
- **FR-011**: The module MUST calculate and return the estimated cutting torque and estimated power required for every drilling operation, as a standard part of the core calculation result (not a separate optional step).
- **FR-012**: The module MUST accept the drilling tool's or machine's maximum available power as an optional input parameter that MAY be left unknown; when supplied, the module MUST report a clear warning if the estimated required power exceeds it; when left unknown, the module MUST still calculate and return the estimated power requirement without attempting a feasibility comparison.
- **FR-013**: The module MUST present all calculated results with their units of measure clearly labeled, in both the interactive text interface and the library's structured results; all labels MUST be sourced from the message catalog (FR-019).
- **FR-014**: The module MUST allow any input (diameter, depth, material, drilling tool, tool/machine power rating) to be changed and the calculated results refreshed accordingly, whether through repeated interactive entry or repeated library calls.
- **FR-015**: The library API MUST report invalid input or missing selections as structured, programmatically identifiable errors (not only human-readable text), so calling programs can handle them without parsing free-form text. The library MUST NOT raise exceptions for expected validation failures (e.g., invalid input, missing selection, unsupported material/tool combination, or feasibility warnings); instead, it MUST always return a structured result object containing a distinct error/warning field (an error code plus a human-readable message, the message text sourced from the message catalog per FR-019 and keyed by the error code) alongside any successfully calculated values.
- **FR-016**: The interactive text interface and the library API MUST produce identical calculated results for identical inputs.
- **FR-017**: The module MUST support both metric units (mm, mm/rev, RPM, kW, N·m) and imperial units (inches, in/rev, RPM, HP, in-lb), allowing the unit system to be selected per session (interactive text interface) or per request (library API); all inputs, outputs, and displayed labels MUST consistently reflect the selected unit system.
- **FR-018**: The module MUST support an external configuration file (separate from source code) for overriding default validation bounds (e.g., maximum drill diameter and hole depth); when no configuration override is present, the module MUST fall back to its built-in default bounds.
- **FR-019**: All user-facing text presented by the interactive text interface (REPL prompts, labels, validation/error messages, feasibility warnings) MUST be sourced from a message catalog rather than hard-coded inline strings, per the following sub-requirements:
  - **FR-019a** (Catalog format): The catalog MUST be one pure-Python module per locale (e.g. `locales/en.py`, exposing a `dict[str, str]` of message ID → string), keyed by a stable, language-independent identifier, rather than a JSON/YAML/gettext-based mechanism.
  - **FR-019b** (Dynamic values): Catalog strings requiring dynamic values (e.g. a material or tool name) MUST use `str.format()`-style named placeholders (e.g. `"Unknown workpiece material: {material!r}."`), populated by the caller at lookup time. If a value required by a placeholder is missing at lookup time, the lookup MUST NOT raise an exception to the caller; it MUST still return a usable (if imperfect) string, with any formatting failure surfaced only via an English-language log entry (see the logging exclusion below).
  - **FR-019c** (Interactive interface locale selection): The interactive text interface MUST select its locale solely from the `MACHINE_CALC_LOCALE` environment variable, read exactly once at startup, without adding a new interactive prompt step and without any OS/system locale (e.g. `LANG`/`LC_ALL`) auto-detection. The locale so selected MUST remain fixed for the lifetime of that interactive session (including across the REPL loop in FR-002/FR-014); it is not re-read or changed mid-session. "Unset or unrecognized" (triggering English fallback) means the environment variable is absent, empty, or does not match the name of any locale module bundled with the installation.
  - **FR-019d** (Library API locale parameter): The library API MUST accept an optional `locale` parameter (defaulting to English when omitted or empty) and MUST return `ErrorInfo.message` and any warning text localized per that parameter, using the same catalog as the interactive text interface — the library is not limited to English-only output.
  - **FR-019e** (Fallback behavior): The module MUST bundle an English catalog module as the default and fallback locale; if a requested locale or a specific message key is missing from a non-English catalog module, the module MUST fall back to the English entry for that key rather than fail or show a blank message.
  - **FR-019f** (Logging exclusion): This requirement does not apply to internal application/diagnostic logging, which MUST always be written in English regardless of the active user-facing locale.

### Key Entities

- **Drilling Operation**: Represents a single calculation request; includes drill diameter, hole depth, selected material, selected drilling tool, selected unit system (metric or imperial), and optional tool/machine power rating, along with the resulting spindle speed, feed rate, machining time, torque, and power.
- **Workpiece Material**: Represents a material available for selection; includes a name and its standard reference cutting speed and feed-per-revolution values used in calculations.
- **Drilling Tool**: Represents a specific drill bit type available for selection (e.g., by material/coating such as high-speed steel, cobalt, or carbide); includes reference cutting speed and feed adjustments that combine with the selected workpiece material to influence recommended settings.
- **Calculation Result**: Represents the structured output of a single Drilling Operation (spindle speed, feed rate, machining time, torque, power, unit system used, and any warnings/errors), returned identically whether produced via the interactive text interface or the library API.
- **Configuration**: Represents optional external settings (e.g., a configuration file) that override built-in default validation bounds for drill diameter and hole depth; when absent, built-in defaults (diameter ≤100 mm/4in, depth ≤500 mm/20in) apply.
- **Message Catalog**: Represents the set of translatable user-facing strings (REPL prompts, labels, error/warning text) keyed by a stable message ID per supported locale; English is always present and used as the fallback when a locale or key is missing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can obtain recommended spindle speed, feed rate, machining time, torque, and power for a drilling operation in under 30 seconds from opening the interactive text interface.
- **SC-002**: Calculated spindle speed, feed rate, torque, and power values are each independently within 5% of published industry reference values for the same material, drilling tool, and drill diameter (i.e., every one of the four values MUST individually meet the 5% tolerance, not merely an average across them).
- **SC-003**: 95% of users can successfully complete a single-material, single-tool calculation on their first attempt via the interactive text interface without needing external help.
- **SC-004**: Invalid input is identified and communicated within the same interaction, with zero calculations silently failing or producing incorrect results, in both the interactive text interface and the library API.
- **SC-005**: Users who do not know their tool's or machine's power rating can still obtain an estimated power requirement for their operation in the same amount of time as users who do provide it.
- **SC-006**: A developer can perform a full drilling calculation (including torque and power) through the library API alone, with no interactive text interface involved, and receive the same result as the equivalent interactive session for identical inputs.
- **SC-007**: A new supported language can be added by providing a new message catalog module only (i.e., a new `locales/<code>.py` file, with no changes to any calculation module (`operations/*/formulas.py`), validation module (`validation.py`), or orchestration module (`operations/*/__init__.py`)), and the application still functions correctly (falling back to English) if that catalog is incomplete.

## Assumptions

- The module is implemented as a Python library exposing a calculation engine API; the interactive text-based interface (e.g., a command-line interface) is a thin layer built on top of that same API, and any other future user interface would integrate the same way.
- Users are familiar with basic drilling terminology (drill diameter, feed rate, spindle speed, tool material) but are not expected to perform the underlying calculations manually.
- The initial material list covers common engineering metals (e.g., mild steel, stainless steel, aluminum, cast iron, brass, titanium) using widely published standard reference cutting speed and feed values; the exact list can be extended later without changing core module behavior.
- The initial drilling tool list covers common drill bit types (e.g., high-speed steel, cobalt, carbide) using widely published standard reference cutting speed and feed adjustment factors; the exact list can be extended later without changing core module behavior.
- This feature ships only the English message catalog (FR-019) as an intentional scope boundary, not a partial or incomplete implementation of FR-019: it establishes the full message-catalog infrastructure so additional languages can be added later by contributing a new locale module, without requiring a translated catalog to exist as part of this feature.
- Message catalogs are expected to remain small, dependency-free Python modules (plain string constants, no parsing library or translation-management toolchain); this is consistent with Constitution Principle V's minimal runtime footprint and is expected to continue to hold for any future locale contributed after this feature.
- Calculations assume conventional twist-drill drilling on a rigid setup (e.g., drill press or milling machine) rather than specialized deep-hole or gun-drilling processes.
- Torque and power estimates use standard machining formulas and assume typical drill geometry; they are intended as planning estimates, not certified engineering values.
- Tool/machine power rating is an optional input specifically because it may be unknown; the module always calculates the estimated power requirement and only performs a feasibility check when a rating is supplied.
- The module does not model or validate a machine's maximum spindle speed (RPM) or feed rate capacity; the only feasibility check performed is the optional power comparison in FR-012. Calculated spindle speed and feed rate are reported as recommendations regardless of any particular machine's physical limits.
- The module does not control or communicate directly with physical machine tools; it is used for planning and reference purposes, and as a calculation engine embedded in other software.
- Single-user, single-session usage is assumed; no multi-user collaboration or result-sharing capability is required for this feature.
