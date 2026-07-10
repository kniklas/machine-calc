# Contract Delta: Interactive Text Interface (CLI/REPL)

**Feature**: [../spec.md](../spec.md) | **Library contract delta**: [./library-api-delta.md](./library-api-delta.md)

This document specifies only the *changes* to
`specs/001-metal-drilling-calc/contracts/cli-repl.md`'s prompt sequence.
Everything not mentioned here (loop behavior, editable-defaults on re-run,
non-interactive invocation being out of scope, all prompt text sourced from
the message catalog) is unchanged and still in effect.

## Updated prompt sequence (one calculation cycle)

1. **Unit system**: unchanged (`metric`/`imperial`, default `metric`).
2. **Calculation mode (NEW, FR-001a)**: prompt to choose `standard` /
   `power-constrained` / `fixed-rpm` (default: `standard`). This selection
   determines which of steps 3a/6a/6b below apply.
3. **Material**: unchanged — display `list_materials()`, prompt, re-prompt
   on invalid/empty entry.
4. **Drilling tool**: unchanged — display `list_tools()`, prompt, re-prompt
   on invalid/empty entry.
5. **Drill diameter**: unchanged.
6. **Hole depth**: unchanged.
7. **Mode-conditional prompt(s) (replaces the base spec's single "Available
   power (optional)" step)**:
   - If mode is `standard`: unchanged — optional available-power prompt,
     advisory-only (base spec FR-012).
   - If mode is `power-constrained`: a **required** available-power
     prompt (FR-002); blank/non-numeric input re-prompts using the
     `MODE_CONFLICT`/validation message rather than proceeding with no
     constraint.
   - If mode is `fixed-rpm`: a **required** target-RPM prompt (FR-005,
     FR-007), followed by the existing **optional** advisory available-power
     prompt (FR-008) — both may be answered independently of one another.
8. Call `calculate(...)` with the collected inputs (including `mode` and,
   if applicable, `target_rpm`) and display the `CalculationResult`:
   - On success: spindle speed, feed rate, machining time, torque, power,
     as today (FR-013), **plus** a clear label indicating the mode that
     produced the result (FR-012) — e.g. distinguishing "recommended" vs.
     "adjusted to fit available power" vs. "user-specified" spindle speed —
     plus any `feasibility_warning`.
   - On error: display `error.message` for any of the base spec's five
     codes or this feature's three new codes (`INVALID_TARGET_RPM`,
     `MODE_CONFLICT`, `INFEASIBLE_POWER_BUDGET`) and do not show numeric
     results, exactly as the base spec's existing error-display behavior.
9. **Loop**: unchanged, except the calculation-mode selection (step 2) is
   also preserved as an editable default on re-run, alongside the other
   inputs.

## Example session (illustrative, power-constrained mode)

```
Unit system [metric/imperial] (metric): metric
Calculation mode [standard/power-constrained/fixed-rpm] (standard): power-constrained
Material (Mild Steel, Stainless Steel, Aluminum, ...): Mild Steel
Drilling tool (HSS, Cobalt, Carbide): Carbide
Drill diameter (mm): 10
Hole depth (mm): 25
Available power (kW): 0.30

Spindle speed:     810.3 RPM   (adjusted to fit available power)
Feed rate:         32.5 mm/min
Machining time:    0.70 min
Torque:            3.1 N*m
Power required:    0.30 kW
```

## Example session (illustrative, fixed-RPM mode)

```
Unit system [metric/imperial] (metric): metric
Calculation mode [standard/power-constrained/fixed-rpm] (standard): fixed-rpm
Material (Mild Steel, Stainless Steel, Aluminum, ...): Mild Steel
Drilling tool (HSS, Cobalt, Carbide): Carbide
Drill diameter (mm): 10
Hole depth (mm): 25
Target spindle speed (RPM): 1200
Available power (kW, blank if unknown):

Spindle speed:     1200.0 RPM  (user-specified)
Feed rate:         48.0 mm/min
Machining time:    0.47 min
Torque:            3.1 N*m
Power required:    0.39 kW
```

## Identical-results guarantee (FR-016, unchanged contract)

As stated in library-api-delta.md: the CLI's mode-selection and
mode-conditional prompts are purely an input-gathering layer over the same
`calculate(mode=..., target_rpm=...)` call a library caller would make —
no calculation logic is duplicated in `cli.py`.
