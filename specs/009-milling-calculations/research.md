# Phase 0 Research: Milling Calculations Module

**Feature**: `009-milling-calculations` | **Date**: 2026-08-19

## 1. Formula source and physical model

**Decision**: Use the same widely-published Sandvik Coromant "Machining
Formulas" reference already cited for drilling
(`specs/001-metal-drilling-calc/research.md` #4), which also publishes the
standard general-milling formulas for spindle speed, table feed, material
removal rate (MRR), specific cutting force (kc)-based net power, and torque.

- Cutting speed: `vc = material.reference_cutting_speed_m_min * tool.cutting_speed_factor`
  (identical pattern to drilling's `DrillingTool.cutting_speed_factor`).
- Spindle speed: `n [RPM] = (vc * 1000) / (pi * D)` (D = tool/cutter diameter, mm) —
  same formula drilling already uses.
- Table feed rate: `vf [mm/min] = n * fz * zn` (fz = feed per tooth, mm/tooth;
  zn = number of flutes/teeth/inserts on the tool).
- Material removal rate: `Q [cm^3/min] = (ap * ae * vf) / 1000` (ap = axial
  depth of cut, ae = radial depth of cut / width of cut, both mm).
- Net cutting power: `Pc [kW] = (ap * ae * vf * kc) / (60 * 10^6)`, where
  `kc` is the workpiece material's specific cutting force in N/mm^2. This is
  **net power at the cutter**, not motor/input power — no drive-efficiency
  factor (`Pm = Pc / eta`) is applied, matching the drilling module's
  existing convention and `spec.md` Assumptions. Any published reference
  value used to verify SC-002 MUST therefore be a net-power figure, or be
  converted to one before comparison.
- Torque: `Mc [Nm] = (Pc * 9550) / n` — the same power/torque/RPM relation
  drilling already uses (`operations/drilling/formulas.py`), just solved for
  torque instead of power.
- Machining time: `tc [min] = length_of_cut_mm / vf`, directly analogous to
  drilling's `(depth + point-allowance) / feed_rate` (no tool-geometry
  entry/exit allowance is modeled for milling in this feature; the user
  supplies the length of cut to be traversed).

**Rationale**: Reuses a citation and mathematical style already reviewed and
trusted in this codebase (Constitution III: formulas MUST cite an external
source); keeps the milling power/torque model consistent with drilling's
existing "power scales from torque via the n/9550 relation" pattern, which
several other modules (e.g. `002-constrained-calculation-modes`) already
depend on structurally.

**Alternatives considered**: Deriving torque from an average-chip-thickness
model with a chip-thinning/entry-exit-angle correction — rejected per
`spec.md` Clarifications (face milling assumes full/symmetric engagement,
no chip-thinning modeling, for this feature).

## 2. Shared core formula vs. per-sub-operation formula

**Decision**: The spindle-speed/feed-rate/MRR/torque/power formulas above are
identical in their mathematical form for both end milling and face milling
(only the physical meaning/validation constraints of `ae` differ — "radial
depth of cut" for end milling vs. "width of cut" for face milling, both
bounded by the cutter diameter). Implement one shared, private core
calculation function (`operations/milling/_shared.py`,
`calculate_milling_metrics()`), and have each sub-operation's own
`operations/milling/end_milling/` and `operations/milling/face_milling/`
package call it with its own inputs, own tool registry, and own
validation/error messages.

**Rationale**: Satisfies both (a) the user-facing requirement that end
milling and face milling be distinct, independently selectable
sub-operations each with their own prompts/registries/validation
(spec.md Clarifications), and (b) Constitution Principle VI's requirement
that *cross-cutting* logic not be duplicated per operation — duplicating an
identical formula verbatim in two modules would itself be the kind of
copy-paste the constitution warns against. The two sub-operations remain
independently addressable modules (their own `tools.py`, `formulas.py`
wrapper, `__init__.py` entry point) so a future divergence (e.g. face-milling
chip-thinning in a later feature) only touches one module.

**Alternatives considered**: Fully duplicating formula code per
sub-operation — rejected as unnecessary duplication of a physically
identical formula. A single combined "milling" module with an internal
`kind` flag — rejected because it would blur the "per-operation module"
boundary the constitution and `001`/`005` precedent establish (drilling's
own module boundary, and the pattern of `operations/<operation>/tools.py`).

## 3. Milling tool registry design

**Decision**: Two new registries, `operations/milling/end_milling/tools.py`
(`EndMillTool`) and `operations/milling/face_milling/tools.py`
(`FaceMillTool`), each structurally identical to
`operations/drilling/tools.py`'s `DrillingTool` but with only a
`cutting_speed_factor` field (no `feed_factor` — see #4 below). Both are
built from bundled package-data TOML files
(`operations/milling/end_milling/data/tools.toml`,
`operations/milling/face_milling/data/tools.toml`) merged with the existing
`registry_config.load_and_merge()` shared helper, exactly like drilling's
tool registry (`specs/005-configurable-materials-tools`).

**Each registry MUST pass its own distinct `table_key`** to
`load_and_merge()`:

| Registry | `table_key` | TOML array-of-tables |
|---|---|---|
| Materials (existing, shared) | `materials` | `[[materials]]` |
| Drilling tools (existing) | `tools` | `[[tools]]` |
| End-mill tools (new) | `end_mill_tools` | `[[end_mill_tools]]` |
| Face-mill tools (new) | `face_mill_tools` | `[[face_mill_tools]]` |

**Rationale**: Reuses the existing, already-tested merge/override/validation
mechanism unchanged (Constitution VI: cross-cutting concerns shared, not
duplicated); a milling tool conceptually represents a tool material/coating
(e.g. "HSS", "Carbide", "Coated Carbide") whose only effect on the shared
formulas is a cutting-speed multiplier, exactly mirroring `DrillingTool`.

The distinct `table_key` values are **not cosmetic** — they prevent a real
regression. `registry_config.load_and_merge()` selects entries from a single
TOML array-of-tables key, and the user supplies **one** shared
`--materials-config` file for the whole application. Had all three tool
registries read `[[tools]]`, then: (a) a user adding an end-mill tool would
silently inject it into the drilling and face-mill tool lists too, and
(b) because `operations/drilling/tools.py::_to_tool()` treats a missing
`feed_factor` as a hard `RegistryConfigError`, that same entry would make
the **existing drilling flow fail to start** — breaking FR-002/SC-005 and
Constitution Principle VI's rule that a new operation must not require
changes to, or break, unrelated existing operations. Separate keys make each
tool kind independently addressable (FR-015) and keep every pre-existing
user config file valid and drilling-only, unchanged.

**Alternatives considered**: A single combined `MillingTool` shared between
end and face milling — rejected because end mills and face mills are
physically distinct tool types with different typical cutting-speed
factors and flute/insert counts in practice, and keeping them distinct
tables matches the "operation-specific reference data MAY remain distinct"
allowance in Constitution VI. Reusing the existing `[[tools]]` key for all
three registries — rejected for the regression reason above. Introducing a
second, milling-only configuration file — rejected because it would
duplicate the configuration-loading concern the constitution requires be
shared.

## 4. Feed-per-tooth input: direct entry, not a registry-derived factor

**Decision**: Unlike drilling's `feed_factor` (which multiplies a material
reference feed value the user never sees), feed per tooth (`fz`) is
**entered directly by the user** for both end milling and face milling
(spec.md Clarifications: "feed per tooth ... combined with the number of
flutes/teeth on the tool"). Number of flutes/teeth/inserts (`zn`) is also a
direct numeric input, not a registry field, since it varies per physical
tool the user owns, not per tool *type*.

**Rationale**: In real milling practice, feed-per-tooth (chip load) values
come from the specific tool manufacturer's cutting-data chart printed for
that exact tool, not from a generic material/tool-type lookup table the way
drilling's feed-per-revolution is commonly generalized; modeling it as a
direct input keeps the calculation accurate without requiring an
unrealistically large per-tool-model reference dataset. This was confirmed
with the user during `/speckit.clarify`.

**Alternatives considered**: Deriving `fz` from `material.reference_feed_*`
times a new tool `feed_factor`, mirroring drilling exactly — rejected per
the user's explicit clarification answer.

## 5. Reuse of `WorkpieceMaterial.specific_cutting_force_kc`

**Decision**: Milling torque/power reuses the *existing*
`WorkpieceMaterial.specific_cutting_force_kc` field (already defined in
`registry.py` and already used by drilling's own torque formula: `Mc = (Kc *
D^2 * fn) / 4000`). No new material field or second registry is needed.

**Rationale**: `kc` is already a canonical, shared, per-material property
(Constitution VI: cross-cutting workpiece-material data MUST be shared
across operations, not duplicated per operation); this feature is the
second consumer of a field that already exists for exactly this purpose,
validating the original drilling-era registry design rather than requiring
a schema change or a parallel "milling materials" registry.

**Alternatives considered**: A separate milling-specific specific-cutting-
force table — rejected as unnecessary duplication of data that already
exists and is unit-converted (imperial psi -> N/mm^2) in the shared
registry.

## 6. REPL operation-selection integration point

**Decision**: Refactor `cli.py`'s `run()` into a thin outer loop that first
prompts for a `MachiningOperation` (`DRILLING`, `MILLING`) via a new
`_prompt_operation()` (reusing the existing `_prompt_choice()` helper, same
re-prompt-on-invalid-input pattern as `_prompt_mode()`). Selecting
`DRILLING` calls the existing (unmodified) drilling REPL body, now extracted
into `_run_drilling_session()`. Selecting `MILLING` prompts for a
`MillingSubOperation` (`END_MILLING`, `FACE_MILLING`) via
`_prompt_milling_sub_operation()`, then dispatches to a new
`_run_end_milling_session()` or `_run_face_milling_session()`. The
run-again prompt returns control to the outer operation-selection loop
(FR-017), not directly back into the same sub-flow.

**Rationale**: Preserves drilling's existing prompt flow and test coverage
byte-for-byte (FR-002; the extracted `_run_drilling_session()` body is
moved, not rewritten) while adding the new top-level selection step
required by the spec, without needing to touch
`operations/drilling/__init__.py`'s calculation logic at all.

**Alternatives considered**: A single flat loop with an `if/elif` operation
branch inline — rejected in favor of extracted per-operation session
functions to keep `run()`'s cyclomatic complexity within the
`pyproject.toml` `max-complexity = 10` threshold (Constitution IX), mirroring
how `operations/drilling/__init__.py` already extracts helpers
(`_validate_and_prepare`, `_compute_metrics`, `_build_result`) for the same
reason.

## 7. `CalculationResult` extension for material removal rate

**Decision**: Add a new optional field `material_removal_rate: float | None
= None` to the shared, operation-agnostic `CalculationResult` dataclass
(`models.py`), following the same additive/backward-compatible pattern
already used to add `mode` in `002-constrained-calculation-modes`. Drilling
continues to leave this field `None` (drilling has no MRR concept); milling
populates it in cm^3/min (metric) or in^3/min (imperial).

**Rationale**: Keeps a single shared result type across all operations
(Constitution VI) rather than introducing a parallel `MillingCalculationResult`
type that CLI/library consumers would need to special-case; the field is
optional and defaults to `None`, so no existing drilling call site,
contract test, or serialization changes.

**Alternatives considered**: A milling-specific result dataclass — rejected
as it would break the "identical structured result contract across
operations" expectation established by `contracts/library-api.md` and
duplicate the `error`/`feasibility_warning`/`unit_system` machinery.

## 8. Validation bounds for new milling inputs

**Decision**: Extend the existing, shared `Configuration` dataclass
(`config.py`) with new optional milling bound fields — `max_mill_diameter_mm`,
`max_depth_of_cut_mm` (used for both axial and radial/width bounds), and
`max_length_of_cut_mm` — with sensible realistic defaults (mirroring
drilling's `max_diameter_mm=100.0`, `max_depth_mm=500.0` precedent), loaded
from the *same* optional TOML configuration file drilling already supports
(`config_path`), not a second config file. This decision is what FR-018
mandates; the defaults chosen below are engineering judgement, not values
carried over from any published reference.

The specific default values — `max_mill_diameter_mm = 200.0`,
`max_depth_of_cut_mm = 50.0`, `max_length_of_cut_mm = 1000.0` — are chosen as
generous sanity limits, not as machining recommendations: they are intended
only to catch typos and unit mistakes (e.g. entering a diameter in
micrometres), and comfortably exceed anything a small-to-mid-size milling
machine could run. They are configurable precisely because they are
judgement calls (FR-018); a user with a large gantry mill can raise them
without a code change.

**Rationale**: Reuses the single existing configuration-file mechanism
(Constitution VI: configuration loading is shared, cross-cutting
infrastructure) rather than introducing a second file format/loader;
keeps a consistent user experience (one optional config file overrides all
operations' bounds).

**Alternatives considered**: No upper bound validation for milling inputs —
rejected because it would be inconsistent with drilling's existing,
tested validation posture (Constitution III: all calculation inputs MUST be
validated against type/range).
