# Feature Specification: Milling Calculation Modes (Power-Constrained & Fixed-RPM)

**Feature Branch**: `010-milling-calculation-modes`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Add Calculation mode (standard, power-constrained, fixed-rpm)"

## Clarifications

### Session 2026-08-19

- Q: `009-milling-calculations` deliberately shipped milling (end-milling and
  face-milling) with only the standard calculation mode, documenting that
  "milling offers no calculation-mode prompt... which is what keeps the flow
  within the SC-001 prompt budget." Should this feature extend
  power-constrained and fixed-RPM modes to milling, reusing drilling's
  existing `002-constrained-calculation-modes` design (shared
  `CalculationMode` enum, error codes, and mode-selection UX pattern)? →
  A: Yes — extend both new modes to both milling sub-operations (end-milling
  and face-milling), following the same mode-selection prompt placement and
  mutual-exclusivity/validation rules already established for drilling, so
  the three operations behave consistently.
- Q: Drilling places its calculation-mode prompt immediately after the
  unit-system prompt, before material/tool/diameter. Where should milling's
  mode prompt go relative to its material-type/material/tool/geometry
  prompts? → A: Immediately after the unit-system prompt, before
  material-type, material, and tool selection — matching drilling's prompt
  position exactly, for consistent UX across all three operations.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Milling Parameters Within an Available Power Budget (Priority: P1)

A machinist running a smaller or older milling machine with a known
spindle motor power rating wants to enter that available power as a hard
constraint and have the module reduce the spindle speed (and recompute the
dependent feed rate, machining time, torque, and material removal rate) so
the operation never demands more power than the machine can deliver —
instead of only receiving an advisory warning after the fact.

**Why this priority**: This is the most requested capability parity gap
between drilling (which already has it) and milling: without it, a
resource-constrained user must manually trial-and-error diameters, depths,
or tools to keep required power within budget, one milling calculation at
a time.

**Independent Test**: Can be fully tested by selecting power-constrained
mode for end-milling or face-milling, supplying an available power below
the material/tool/geometry combination's normally-required power, and
verifying the returned spindle speed and feed rate are reduced
consistently (with recomputed required power equal to the supplied
budget, and torque unchanged — cutting torque does not depend on spindle
speed, research.md #1) so the required power no longer exceeds the
supplied budget.

**Acceptance Scenarios**:

1. **Given** a supplied available power below the power normally required
   at the material/tool/geometry combination's recommended spindle speed,
   **When** the user requests a power-constrained milling calculation,
   **Then** the module returns a reduced spindle speed (and consistently
   recomputed feed rate, machining time, torque, and material removal
   rate) at which the required power no longer exceeds the supplied
   budget.
2. **Given** a supplied available power that is already sufficient
   (including exactly equal, within floating-point tolerance) for the
   normally-recommended spindle speed, **When** the user requests a
   power-constrained milling calculation, **Then** the module returns the
   same values as the standard (unconstrained) calculation — no
   unnecessary de-rating is applied.
3. **Given** a supplied available power so low that no positive spindle
   speed can bring the required power within budget, **When** the user
   requests a power-constrained milling calculation, **Then** the module
   rejects the request with a clear, structured error and performs no
   calculation, rather than returning an unsafe, degenerate, or
   silently-exceeding result.

---

### User Story 2 - Calculate Milling Parameters for a User-Specified Spindle RPM (Priority: P2)

A machinist operating a mill that only supports specific fixed spindle
speeds (e.g., a belt-and-pulley knee mill, or a machine already set up at
a particular RPM) wants to enter that fixed spindle speed directly and
have the module calculate the resulting feed rate, machining time, torque,
material removal rate, and required power for their chosen material,
tool, and geometry — instead of only ever receiving the material/tool's
own recommended RPM.

**Why this priority**: This directly complements User Story 1 by
supporting the reverse workflow: the user provides the RPM their
equipment is actually capable of and needs the remaining parameters,
including the power the operation will require, calculated from it.

**Independent Test**: Can be fully tested by supplying a specific target
spindle RPM (distinct from the material/tool's own recommended RPM) along
with the milling geometry, material, and tool, and verifying the returned
feed rate, machining time, torque, material removal rate, and required
power are calculated consistently from that specified RPM rather than
from the material/tool's own recommended value.

**Acceptance Scenarios**:

1. **Given** a user supplies a target spindle RPM instead of relying on
   the material/tool-derived recommendation, **When** a milling
   calculation is requested, **Then** the feed rate, machining time,
   torque, material removal rate, and required power are all computed
   using that specified RPM.
2. **Given** a specified spindle RPM that is zero, negative, or
   non-numeric, **When** a milling calculation is requested, **Then** the
   module rejects the request with a clear, structured error and performs
   no calculation.
3. **Given** a specified spindle RPM together with a known available
   power, **When** the required power at that specified RPM exceeds the
   available power, **Then** the result includes a feasibility warning
   (the same behavior as the existing advisory available-power input),
   without altering the user-specified RPM itself.

---

### Edge Cases

- What happens when a power-constrained milling calculation would reduce
  spindle speed to an impractically small value? This feature does not
  impose a minimum spindle speed floor beyond positivity, mirroring
  drilling's existing behavior — only a non-positive/undefined solution is
  rejected (see Acceptance Scenario 1.3).
- What happens when a user-specified target RPM is far above what any
  bundled end-mill or face-mill tool would normally support for that
  material? The module does not reject a specified RPM for being "too
  high" — it calculates and returns the resulting feed rate, torque, and
  required power, which may themselves be very large, consistent with
  `009-milling-calculations`' existing decision not to model a machine
  RPM/feed-rate ceiling.
- How does the module behave if both a power constraint and a target-RPM
  constraint are supplied on the same milling request? Rejected as
  `MODE_CONFLICT`, mirroring drilling's FR-009.
- How does specifying a target RPM interact with imperial vs. metric unit
  systems? RPM is unit-system-independent, so a target RPM is entered and
  reported identically under both unit systems; only feed rate, torque,
  power, and material removal rate convert per `UnitSystem`, exactly as
  they already do for standard milling calculations.
- Does this feature change end-milling's and face-milling's shared module
  boundary (`009-milling-calculations` FR-014, keeping each sub-operation's
  own `formulas.py`)? No — mode dispatch is added to the shared milling
  orchestration layer once, exactly as the validation/registry-lookup
  order is already shared, so end-milling and face-milling do not each
  reimplement it.
- Does power-constrained/fixed-RPM mode apply differently to face milling
  than end milling given their different radial-engagement semantics
  (radial depth of cut vs. width of cut)? No — the reduction/direct-input
  math operates on spindle speed and its dependents identically for both;
  only the existing radial-engagement label and validation differ,
  unchanged from `009-milling-calculations`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The module MUST allow an end-milling or face-milling
  calculation request (via the interactive text interface or the library
  API) to optionally select a **power-constrained calculation mode**,
  supplying a known available power as the constraining input, using the
  same `CalculationMode` enum and semantics already established for
  drilling (`002-constrained-calculation-modes`).
- **FR-001a**: The interactive text interface's milling flow MUST present
  a calculation-mode selection prompt (offering *standard*,
  *power-constrained*, and *fixed-RPM*) immediately after the unit-system
  prompt and before the material-type, material, and tool selection
  prompts, matching drilling's exact prompt position (Clarifications
  2026-08-19) rather than being placed later in the flow. The mode chosen
  there determines which subsequent prompts are shown: standard mode keeps
  the existing optional advisory available-power prompt; power-constrained
  mode replaces it with a required available-power prompt used as a hard
  constraint (FR-002/FR-004); and fixed-RPM mode adds a required
  target-RPM prompt (FR-005/FR-007) plus the existing optional advisory
  available-power prompt (FR-008). An invalid or empty entry at the
  mode-selection prompt MUST be re-prompted, never silently falling back
  to a default mode. This prompt and its dispatch logic MUST be shared
  between the end-milling and face-milling sessions rather than
  duplicated per sub-operation.
- **FR-002**: When power-constrained mode is used for a milling
  calculation and the power required at the material/tool/geometry
  combination's normally-recommended spindle speed **exceeds** the
  supplied available power (i.e., is strictly greater, per FR-003's
  boundary rule), the module MUST reduce the spindle speed (and
  correspondingly recompute the feed rate, machining time, torque, and
  material removal rate using the existing milling formula relationships)
  to the highest value at which the required power no longer exceeds the
  available power.
- **FR-003**: When power-constrained mode is used for a milling
  calculation and the supplied available power is already sufficient for
  the normally-recommended spindle speed — including the boundary case
  where it is exactly equal to the required power (within floating-point
  tolerance) — the module MUST return the same result as the standard
  (unconstrained) calculation, without applying any unnecessary reduction.
- **FR-004**: When power-constrained mode is used for a milling
  calculation and no positive spindle speed can bring the required power
  within the supplied available power budget, the module MUST reject the
  request with a clear, structured error under the same
  `INFEASIBLE_POWER_BUDGET` code drilling already uses, and MUST NOT
  return a calculation result.
- **FR-005**: The module MUST allow an end-milling or face-milling
  calculation request to optionally select a **fixed-RPM calculation
  mode**, supplying a target spindle RPM directly instead of deriving it
  from the selected material and milling tool.
- **FR-006**: When fixed-RPM mode is used for a milling calculation, the
  module MUST calculate feed rate, machining time, torque, material
  removal rate, and required power from the supplied target RPM (combined
  with the selected material's and milling tool's reference values and the
  entered geometry), using the same underlying milling formulas as the
  standard calculation (`009-milling-calculations` FR-005/FR-007), but with
  spindle speed taken as a direct input rather than a derived output.
- **FR-007**: The module MUST validate a supplied milling target RPM as a
  positive, finite number and MUST reject zero, negative, non-numeric,
  `NaN`, or `Infinity` values — all under the same `INVALID_TARGET_RPM`
  error code drilling already uses, with no calculation performed. No
  additional maximum/minimum range validation or clamping is applied
  beyond finiteness and positivity.
- **FR-008**: When fixed-RPM mode is used for a milling calculation
  together with a supplied available power, the module MUST apply the
  existing feasibility-warning behavior: a warning is included in the
  result if the power required at the specified RPM exceeds the available
  power, without altering the user-specified RPM. Supplying
  `available_power` while `mode=FIXED_RPM` is always accepted as this
  optional/advisory input — it is never treated as a `MODE_CONFLICT`.
- **FR-009**: Power-constrained mode (FR-001) and fixed-RPM mode (FR-005)
  MUST be mutually exclusive on a single milling calculation request, with
  the same `MODE_CONFLICT` rules drilling already uses: `mode=STANDARD`
  (the default) simply ignores any supplied `target_rpm`/`available_power`;
  `mode=POWER_CONSTRAINED` with a supplied `target_rpm`, or with no
  `available_power` supplied, is rejected as `MODE_CONFLICT`.
- **FR-010**: Both new calculation modes MUST continue to satisfy
  `009-milling-calculations`' FR-012 (never raising exceptions for expected
  validation failures; always returning a structured result) and FR-016
  equivalent (the interactive text interface and the library API MUST
  produce identical results for identical inputs and mode selection), for
  both end-milling and face-milling.
- **FR-011**: All new user-facing text introduced by this feature
  (mode-selection prompts/parameters, adjusted-vs-recommended value
  labeling, and any new error messages) MUST be sourced from the existing
  shared message catalog, reusing drilling's existing catalog entries
  where the wording is mode-generic rather than duplicating them per
  operation.
- **FR-012**: A milling calculation result produced in power-constrained
  or fixed-RPM mode MUST clearly and structurally indicate which mode
  produced it via the existing shared `CalculationResult.mode:
  CalculationMode` field, exactly as drilling results already do.
- **FR-013**: When the interactive text interface loops for another
  milling calculation and the user changes the calculation mode from the
  previous run, any previously entered mode-specific value (a target RPM,
  or an available-power value entered as a power-constrained hard
  constraint) MUST be cleared rather than carried over as an editable
  default; shared inputs (unit system, material, tool, geometry) continue
  to be retained as editable defaults exactly as
  `009-milling-calculations` already requires, and this clearing behavior
  MUST be tracked per milling sub-operation session state exactly as
  other editable defaults already are.
- **FR-014**: This feature MUST NOT change end-milling's or face-milling's
  own formula module (`formulas.py`) boundary: spindle-speed reduction
  (FR-002) and direct-RPM substitution (FR-006) MUST be implemented once
  in the shared milling orchestration layer, consistent with
  `009-milling-calculations` FR-014's module-boundary requirement.

### Key Entities

- **Calculation Mode**: The existing shared `CalculationMode` value
  (*standard*, *power-constrained*, *fixed-RPM*) that already applies to
  drilling, now also selectable for end-milling and face-milling
  calculation requests. Exactly one mode applies per request (FR-009).
- **Power Constraint**: An available-power input used to bound (rather
  than merely warn about) the calculated milling spindle speed and its
  dependent feed rate, machining time, torque, and material removal rate,
  when power-constrained mode is selected.
- **Spindle Speed Constraint**: A caller-supplied target RPM used as a
  direct input (rather than a derived output) to an end-milling or
  face-milling calculation, when fixed-RPM mode is selected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a supplied available power below a milling
  material/tool/geometry combination's normal power requirement, users
  receive an adjusted spindle speed/feed-rate recommendation that fits
  their machine's real capability in a single calculation request, for
  both end-milling and face-milling, with no manual trial-and-error
  across multiple materials, tools, or geometries.
- **SC-002**: Given a fixed target spindle RPM, users receive complete
  milling parameters (feed rate, machining time, torque, material removal
  rate, required power) for that RPM in the same single request,
  completing within 0.5-1.0s, the same numeric performance target as a
  standard milling calculation.
- **SC-003**: 100% of power-constrained milling results have a required
  power that does not exceed the supplied available power (using the same
  floating-point tolerance convention as drilling's equivalent guarantee),
  or are rejected with a clear structured error; never silently returning
  a result that exceeds the stated power budget.
- **SC-004**: Existing standard (unconstrained, no mode selected) milling
  calculations continue to produce identical results after this feature
  ships as they did before it (no regression to `009-milling-calculations`'
  behavior).
- **SC-005**: Drilling, end-milling, and face-milling calculation requests
  all expose and behave consistently under the same three calculation
  modes, so a user or integrator does not need to learn a different mode
  model per operation.

## Assumptions

- This feature extends the existing `009-milling-calculations` feature's
  `calculate_end_milling()`/`calculate_face_milling()` library API and
  interactive text interface; it does not introduce a separate calculation
  engine, a new top-level entry point, or a new `CalculationMode` value
  beyond the three drilling already defines.
- In power-constrained mode, only spindle speed (and its dependent feed
  rate, machining time, torque, and material removal rate) is adjusted;
  the underlying material and milling-tool reference values themselves are
  never altered.
- No machine-specific maximum-RPM database or per-machine profile is
  introduced by this feature, consistent with drilling's existing
  equivalent assumption.
- Both new calculation modes are additive and optional: a milling
  calculation request that specifies neither an available-power
  constraint nor a target RPM behaves exactly as the existing
  (pre-this-feature) standard milling calculation (SC-004).
- This feature reuses drilling's existing error codes
  (`INFEASIBLE_POWER_BUDGET`, `INVALID_TARGET_RPM`, `MODE_CONFLICT`) and
  message-catalog entries rather than introducing milling-specific
  duplicates, since the underlying semantics are identical across
  operations.
- `009-milling-calculations`' explicit decision to omit a calculation-mode
  prompt from milling (documented in its CLI implementation) is
  superseded by this feature for the two new modes; the standard mode's
  existing default-first, no-extra-prompt behavior (SC-004) is preserved
  for users who do not need power-constrained or fixed-RPM behavior.
