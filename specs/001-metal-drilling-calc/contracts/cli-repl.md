# Contract: Interactive Text Interface (CLI/REPL)

**Feature**: [../spec.md](../spec.md) | **Library contract**: [./library-api.md](./library-api.md)

Defines the sequential prompt contract for the interactive text-based
interface (FR-002), built strictly on top of the library API's
`calculate()` — no independent calculation logic (see identical-results
contract).

## Prompt sequence (one calculation cycle)

1. **Unit system**: prompt to choose `metric` or `imperial` (default:
   `metric`).
2. **Material**: display the list from `list_materials()`; prompt for a
   selection; re-prompt on invalid/empty entry (FR-010).
3. **Drilling tool**: display the list from `list_tools()`; prompt for a
   selection; re-prompt on invalid/empty entry (FR-010).
4. **Drill diameter**: prompt for a numeric value in the chosen unit system;
   re-prompt with the validation message from `ErrorInfo.message` on
   rejection (FR-009).
5. **Hole depth**: prompt for a numeric value; same validation behavior as
   diameter.
6. **Available power (optional)**: prompt for a numeric value or blank/`skip`
   to leave unknown (FR-012).
7. Call `calculate(...)` with the collected inputs and display the
   `CalculationResult`:
   - On success: spindle speed, feed rate, machining time, torque, power,
     all labeled with units matching the selected unit system (FR-013), plus
     any `feasibility_warning`.
   - On error: display `error.message` and do not show numeric results
     (FR-009/FR-010).
8. **Loop**: prompt whether to run another calculation (changing any input)
   or exit (FR-014). Returning to step 1 preserves previously entered values
   as editable defaults so the user can change only what they need.

## Non-interactive invocation

Out of scope for this feature: no command-line flag/argument mode is
required (per clarification, the interface is REPL-only). A future feature
may add flag-based invocation without changing the underlying library
contract.

## Example session (illustrative, not literal output format)

```
Unit system [metric/imperial] (metric): metric
Material (Mild Steel, Stainless Steel, Aluminum, ...): Mild Steel
Drilling tool (HSS, Cobalt, Carbide): Carbide
Drill diameter (mm): 10
Hole depth (mm): 25
Available power (kW, blank if unknown):

Spindle speed:     1350.5 RPM
Feed rate:         54.2 mm/min
Machining time:    0.42 min
Torque:            3.1 N·m
Power required:    0.44 kW

Run another calculation? [y/N]:
```
