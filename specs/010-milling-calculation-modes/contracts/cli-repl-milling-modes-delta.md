# Contract Delta: CLI REPL (Milling Calculation Modes)

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

This document specifies only the *changes* to
`specs/009-milling-calculations/contracts/cli-repl-milling.md`'s "End
milling session prompts" and "Face milling session prompts" sections, which
are otherwise unchanged (operation/sub-operation selection, tool/material
prompts, geometry prompts, re-prompt-on-invalid behavior). It mirrors
`specs/002-constrained-calculation-modes/contracts/cli-repl-delta.md`'s
structure, applied to both milling sessions via the single shared
`_prompt_milling_inputs()` helper (research.md #5).

## Updated end milling / face milling session prompts

In order (steps 3-4 are new; existing steps renumbered but unchanged in
content):

1. Unit system (reuses `_prompt_unit_system`, unchanged).
2. **Calculation mode** (new — reuses `_prompt_mode`, identical widget to
   drilling's): *standard* / *power-constrained* / *fixed-RPM*. An
   invalid/empty entry re-prompts (never silently defaults).
3. Material type, then material (reuses the existing two-step 008 flow,
   unchanged).
4. End-mill or face-mill tool (unchanged).
5. Tool/cutter diameter through length of cut — the six geometry inputs
   (unchanged from `009-milling-calculations`).
6. **Mode-conditional power/RPM prompt(s)** (new placement of an existing
   idea): standard mode keeps the existing optional advisory
   `_prompt_optional_power`; power-constrained mode instead prompts for a
   **required** available power (blank re-prompts as a validation failure,
   never `MODE_CONFLICT`); fixed-RPM mode prompts for a **required** target
   RPM (reuses `_prompt_target_rpm`) followed by the existing optional
   advisory available-power prompt.

```text
loop:
    state.unit_system = prompt_unit_system(state.unit_system)
    state.mode = prompt_mode(state.mode)                      # NEW
    if state.mode != state.previous_mode:                     # NEW (FR-013)
        state.target_rpm = None
        state.available_power = None
    state.material_type, state.material = ...                 # unchanged
    state.tool = ...                                            # unchanged
    prompt_milling_geometry(state)                              # unchanged (6 prompts)
    if state.mode == POWER_CONSTRAINED:                        # NEW
        state.available_power = prompt_required_power(state.available_power)
    elif state.mode == FIXED_RPM:                               # NEW
        state.target_rpm = prompt_target_rpm(state.target_rpm)
        state.available_power = prompt_optional_power(state.available_power)
    else:
        state.available_power = prompt_optional_power(state.available_power)  # unchanged
    state.previous_mode = state.mode                            # NEW
    result = calculate_end_milling(..., mode=state.mode, target_rpm=state.target_rpm)
    display(result)
    again = prompt_run_again()
    if again is not yes: break
```

## Prompt-count budget (supersedes `009-milling-calculations` SC-001 for the two new modes)

`009-milling-calculations`' SC-001 (14 prompts / 12 typed values) was set
assuming milling never prompts for a calculation mode. This feature adds
exactly one mode-selection prompt to every milling run, plus mode-specific
follow-ups:

| Mode | Total prompts | Typed values (non-dismissible) |
|---|---|---|
| Standard | 14 (was 13 pre-this-feature) | 13 (the new mode-selection prompt is itself non-dismissible per FR-001a, so only the optional power prompt remains dismissible) |
| Power-constrained | 14 | 14 (available power becomes required, not dismissible, and mode selection is always typed) |
| Fixed-RPM | 15 | 14 (target RPM is required; available power stays optional/dismissible) |

Standard mode's *typed*-value count increases by exactly one from
`009-milling-calculations` (12 -> 13), matching its *total* prompt count
increase of exactly one (the new mode prompt itself) — both changes are
the intended, spec.md FR-001a-required consequence of the mode prompt
having no blank/default option, not a regression. The existing
`tests/integration/test_cli_prompt_budget.py` MUST be updated to assert a
per-mode count rather than one fixed total.

## Loop re-run mode-change clearing (FR-013)

Identical semantics to drilling's existing behavior
(`002-constrained-calculation-modes/contracts/cli-repl-delta.md`): when the
user changes `mode` between loop iterations, `target_rpm` and any
`available_power` entered as a power-constrained hard constraint are reset
to `None` rather than offered as editable defaults; unit system, material
type, material, tool, and all six geometry inputs continue to be retained
as editable defaults exactly as `009-milling-calculations` FR-017 already
requires. This clearing is tracked per milling sub-operation session state
(`_MillingSessionState`), so switching from end-milling to face-milling and
back does not leak one sub-operation's mode-specific values into the other
(consistent with the existing per-sub-operation state isolation).
