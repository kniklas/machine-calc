# Feature Specification: Constrained Drilling Calculation Modes (Power-Limited & Fixed-RPM)

**Feature Branch**: `002-constrained-calculation-modes`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "add requirement that spindle calculation should be calculated accordingly to given available power, so machining parameters could be adjusted; similarly it should be possible to define/constrain spindle RPM and other parameters should be calculated including required power of the machining tool"

## Clarifications

### Session 2026-07-10

- Q: How should the interactive REPL let the user choose between standard calculation, power-constrained mode, and fixed-RPM mode? → A: Add one new REPL prompt (after unit system, before material/diameter) asking the user to pick a calculation mode: standard / power-constrained / fixed-RPM. Subsequent prompts adapt accordingly (power-constrained mode prompts for available power as the constraint, not advisory; fixed-RPM mode prompts for a target RPM instead of deriving it, with available power remaining optional/advisory).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adjust Calculation to Fit Available Machine Power (Priority: P1)

A machinist whose machine or tool has a known maximum available power wants
the module to automatically determine the fastest safe spindle speed and
feed rate that stay within that power limit, rather than simply being
warned after the fact that the material's normally-recommended settings
exceed it.

**Why this priority**: Today, supplying an available power rating only
produces an advisory warning (existing FR-012) — the user still has to
manually guess a lower diameter/material/tool combination by trial and
error. Automatically adjusting the recommendation to fit the real
constraint is the core value of this feature.

**Independent Test**: Can be fully tested by requesting a power-constrained
calculation with an available power below what the material/tool/diameter
combination would normally require at the standard recommended spindle
speed, and verifying the returned spindle speed, feed rate, machining time,
torque, and required power are all mutually consistent and the required
power no longer exceeds the available power.

**Acceptance Scenarios**:

1. **Given** a supplied available power that is lower than the power
   required at the material/tool's normally-recommended spindle speed,
   **When** the user requests a power-constrained calculation, **Then** the
   module returns a reduced spindle speed (and correspondingly recalculated
   feed rate, machining time, and torque) such that the required power no
   longer exceeds the available power.
2. **Given** a supplied available power that is already sufficient for the
   normally-recommended spindle speed, **When** the user requests a
   power-constrained calculation, **Then** the module returns the same
   values as the standard (unconstrained) calculation — no unnecessary
   de-rating is applied.
3. **Given** a supplied available power so low that no positive spindle
   speed can bring the required power within budget, **When** the user
   requests a power-constrained calculation, **Then** the module rejects
   the request with a clear, structured error and performs no calculation,
   rather than returning an unsafe, degenerate (e.g., near-zero RPM), or
   silently-exceeding result.

---

### User Story 2 - Calculate Parameters for a User-Specified Spindle RPM (Priority: P2)

A machinist operating a machine that only supports specific fixed spindle
speeds (e.g., a stepped-pulley drill press, or a machine already set up at
a particular RPM) wants to enter that fixed spindle speed directly and have
the module calculate the resulting feed rate, machining time, torque, and
required power for their chosen material, tool, and diameter — instead of
only ever receiving the material/tool's own recommended RPM.

**Why this priority**: This directly complements User Story 1 by supporting
the reverse workflow: instead of deriving RPM from material/tool and
adjusting it for a power limit, the user provides the RPM their equipment
is actually capable of and needs the remaining parameters, including the
power the operation will require, calculated from it.

**Independent Test**: Can be fully tested by supplying a specific target
spindle RPM (distinct from the material/tool's own recommended RPM) along
with diameter, material, and tool, and verifying the returned feed rate,
machining time, torque, and required power are calculated consistently
from that specified RPM rather than from the material/tool's own
recommended value.

**Acceptance Scenarios**:

1. **Given** a user supplies a target spindle RPM instead of relying on the
   material/tool-derived recommendation, **When** a calculation is
   requested, **Then** the feed rate, machining time, torque, and required
   power are all computed using that specified RPM.
2. **Given** a specified spindle RPM that is zero, negative, or
   non-numeric, **When** a calculation is requested, **Then** the module
   rejects the request with a clear, structured error and performs no
   calculation.
3. **Given** a specified spindle RPM together with a known available
   power, **When** the required power at that specified RPM exceeds the
   available power, **Then** the result includes a feasibility warning
   (same behavior as the existing FR-012), without altering the
   user-specified RPM itself.

---

### Edge Cases

- What happens when a power-constrained calculation would reduce spindle
  speed to an impractically small value (e.g., so slow that machining time
  becomes unreasonably long)? This feature does not impose a minimum
  spindle speed floor beyond positivity — an extremely low but positive
  adjusted RPM is still returned; only a non-positive/undefined solution is
  rejected (see Acceptance Scenario 1.3).
- What happens when a user-specified target RPM is far above what any
  bundled drilling tool would normally support for that material? Per this
  feature and the existing spec's Assumptions (no machine RPM/feed-rate
  ceiling is modeled), the module does not reject a specified RPM for
  being "too high" — it simply calculates and returns the resulting feed
  rate, torque, and required power, which may themselves be very large.
- How does the module behave if both a power constraint and a target-RPM
  constraint are supplied on the same request? See FR-009 (Clarification
  Q3 resolved below).
- How does specifying a target RPM interact with imperial vs. metric unit
  systems? RPM itself is unit-system-independent (per the existing spec's
  data model), so a target RPM is entered and reported identically under
  both unit systems; only feed rate, torque, and power convert per
  `UnitSystem`, exactly as they already do for standard calculations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST allow a calculation request (via the
  interactive text interface or the library API) to optionally select a
  **power-constrained calculation mode**, supplying a known available
  power as the constraining input. In the interactive text interface,
  this selection MUST be made via a dedicated calculation-mode prompt
  (FR-001a), not by overloading the existing advisory available-power
  input.
- **FR-001a**: The interactive text interface MUST present a single
  calculation-mode selection prompt (offering *standard*,
  *power-constrained*, and *fixed-RPM*) after the unit-system prompt and
  before the material/tool/diameter/depth prompts. The mode chosen there
  determines which subsequent prompts are shown: standard mode keeps the
  base spec's existing optional advisory available-power prompt (FR-012
  of the base spec); power-constrained mode replaces it with a required
  available-power prompt used as a hard constraint (FR-002/FR-004); and
  fixed-RPM mode adds a required target-RPM prompt (FR-005/FR-007) plus
  the existing optional advisory available-power prompt (FR-008).
- **FR-002**: When power-constrained mode is used and the power required
  at the material/tool's normally-recommended spindle speed exceeds the
  supplied available power, the module MUST reduce the spindle speed (and
  correspondingly recompute the feed rate using the existing tool/material
  feed relationship, plus machining time and torque) to the highest value
  at which the required power no longer exceeds the available power.
- **FR-003**: When power-constrained mode is used and the supplied
  available power is already sufficient for the normally-recommended
  spindle speed, the module MUST return the same result as the standard
  (unconstrained) calculation, without applying any unnecessary reduction.
- **FR-004**: When power-constrained mode is used and no positive spindle
  speed can bring the required power within the supplied available power
  budget, the module MUST reject the request with a clear, structured
  error (distinct from the existing `MISSING_MATERIAL`/`MISSING_TOOL`/
  `INVALID_DIAMETER`/`INVALID_DEPTH`/`UNSUPPORTED_COMBINATION` codes) and
  MUST NOT return a calculation result.
- **FR-005**: The module MUST allow a calculation request to optionally
  select a **fixed-RPM calculation mode**, supplying a target spindle RPM
  directly instead of deriving it from the selected material and drilling
  tool.
- **FR-006**: When fixed-RPM mode is used, the module MUST calculate feed
  rate, machining time, torque, and required power from the supplied
  target RPM (combined with the selected material's and drilling tool's
  reference values), using the same underlying formulas as the standard
  calculation (FR-007/FR-008/FR-011 of the base drilling spec), but with
  spindle speed taken as a direct input rather than a derived output.
- **FR-007**: The module MUST validate a supplied target RPM as a
  positive, finite number and MUST reject zero, negative, or non-numeric
  values with a clear, structured error, performing no calculation — the
  same validation posture as diameter and depth in the base drilling spec
  (FR-009).
- **FR-008**: When fixed-RPM mode is used together with a supplied
  available power, the module MUST apply the existing feasibility-warning
  behavior (base spec FR-012): a warning is included in the result if the
  power required at the specified RPM exceeds the available power, without
  altering the user-specified RPM.
- **FR-009**: Power-constrained mode (FR-001) and fixed-RPM mode (FR-005)
  MUST be mutually exclusive on a single calculation request — supplying
  inputs for both at once MUST be rejected with a clear, structured error
  distinct from a feasibility warning, rather than the module silently
  prioritizing one over the other.
- **FR-010**: Both new calculation modes MUST continue to satisfy the base
  drilling spec's FR-015 (never raising exceptions for expected validation
  failures; always returning a structured result) and FR-016 (the
  interactive text interface and the library API MUST produce identical
  results for identical inputs and mode selection).
- **FR-011**: All new user-facing text introduced by this feature
  (mode-selection prompts/parameters, adjusted-vs-recommended value
  labeling, and any new error messages) MUST be sourced from the message
  catalog per the base drilling spec's FR-019, not hard-coded — this
  feature does not introduce any exception to Constitution Principle VIII.
- **FR-012**: A calculation result produced in power-constrained or
  fixed-RPM mode MUST clearly and structurally indicate which mode
  produced it (e.g., a mode/source field alongside the numeric results),
  so calling programs and the interactive text interface can distinguish
  an adjusted or user-specified spindle speed from the material/tool's own
  recommended one.

### Key Entities

- **Calculation Mode**: Represents which of the three ways a drilling
  calculation was performed: *standard* (spindle speed derived from
  material/tool reference values, as in the base drilling spec),
  *power-constrained* (spindle speed reduced to fit a supplied available
  power), or *fixed-RPM* (spindle speed supplied directly by the caller).
  Exactly one mode applies per calculation request (FR-009).
- **Power Constraint**: Represents an available-power input used to bound
  (rather than merely warn about) the calculated spindle speed and its
  dependent feed rate, machining time, and torque, when power-constrained
  mode is selected.
- **Spindle Speed Constraint**: Represents a caller-supplied target RPM
  used as a direct input (rather than a derived output) to the drilling
  calculation, when fixed-RPM mode is selected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a supplied available power below the material/tool's
  normal power requirement, users receive an adjusted spindle
  speed/feed-rate recommendation that fits their machine's real capability
  in a single calculation request, with no manual trial-and-error across
  multiple materials, tools, or diameters.
- **SC-002**: Given a fixed target spindle RPM, users receive complete
  drilling parameters (feed rate, machining time, torque, required power)
  for that RPM in the same single request, with the same response time as
  a standard calculation.
- **SC-003**: 100% of power-constrained results have a required power that
  does not exceed the supplied available power (within floating-point
  tolerance), or are rejected with a clear structured error — never
  silently returning a result that exceeds the stated power budget.
- **SC-004**: Existing standard (unconstrained, no mode selected)
  calculations continue to produce identical results after this feature
  ships as they did before it (no regression to the base drilling spec's
  behavior).

## Assumptions

- This feature extends the existing `001-metal-drilling-calc` feature's
  `calculate()` API and interactive text interface; it does not introduce
  a separate calculation engine or a new top-level entry point.
- In power-constrained mode, only spindle speed (and its dependent feed
  rate, via the existing tool/material feed-per-revolution relationship)
  is adjusted; the underlying material and drilling-tool reference values
  themselves are never altered.
- No machine-specific maximum-RPM database or per-machine profile is
  introduced by this feature; if a future need arises to bound a supplied
  target RPM, it would reuse the existing `Configuration` file mechanism
  (base drilling spec FR-018), analogous to the diameter/depth bounds.
- Both new calculation modes are additive and optional: a calculation
  request that specifies neither an available-power constraint nor a
  target RPM behaves exactly as the existing (pre-this-feature) standard
  calculation (SC-004).
- This feature does not change the base drilling spec's decision to omit
  a machine RPM/feed-rate ceiling as a feasibility check (base spec Edge
  Cases); a fixed-RPM request is never rejected merely for being
  "unrealistically high."
