# Contract: CLI REPL Operation Selection & Milling Flows

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

Extends `specs/001-metal-drilling-calc/contracts/cli-repl.md` with the new
operation-selection entry point (FR-001) and the two new milling
sub-flows (FR-003, FR-004, FR-006). All prompts/labels/messages are sourced
from the message catalog (Constitution VIII), consistent with the existing
drilling prompts.

## Startup / loop sequence

```text
loop:
    operation = prompt_operation()              # "drilling" | "milling" (FR-001)
    if operation == DRILLING:
        run_drilling_session()                  # existing, unmodified flow (FR-002)
    else:
        sub_operation = prompt_milling_sub_operation()  # "end milling" | "face milling" (FR-003)
        if sub_operation == END_MILLING:
            run_end_milling_session()           # FR-004, FR-005
        else:
            run_face_milling_session()          # FR-006, FR-007
    again = prompt_run_again()
    if again is not yes: break
    # loop returns to prompt_operation() again -- FR-017, does not force
    # repeating the previously selected operation/sub-operation.
```

- An unrecognized operation or sub-operation choice re-prompts with a clear
  validation message (FR-001 Acceptance Scenario 4), reusing the existing
  `_prompt_choice()` re-prompt-on-invalid-input behavior already used for
  material/tool/mode selection.
- `run_drilling_session()` is the existing `run()` loop body, extracted
  unchanged (research.md #6) — no behavioral change to drilling (FR-002).

## End milling session prompts (new)

In order, each reusing existing prompt helpers/patterns
(`_prompt_material_type_choice`, `_prompt_material_choice`,
`_prompt_choice`, `_prompt_number`):

1. Unit system (reuses `_prompt_unit_system`).
2. Material type, then material (reuses the existing two-step 008 flow).
3. End-mill tool (new `_prompt_end_mill_tool_choice`, mirrors
   `_prompt_tool_choice`).
4. Tool/cutter diameter (reuses `_prompt_number`-style validation).
5. Axial depth of cut.
6. Radial depth of cut (validated `<=` diameter at submission time --
   FR-009; a violation re-prompts with a clear message, it does not silently
   clamp).
7. Feed per tooth.
8. Number of teeth/flutes.
9. Length of cut.
10. Optional known tool/machine power rating (reuses
    `_prompt_optional_power`).

### Prompt-count budget (SC-001)

A full end-milling run issues exactly **13** prompts, counted end to end:
operation, milling sub-operation, unit system, material type, material,
end-mill tool, diameter, axial depth of cut, radial depth of cut, feed per
tooth, number of teeth, length of cut, optional power rating. The last one
is dismissible with a bare Enter, so at most **12** require typing a value.
SC-001's budget of 14 prompts / 12 typed values is set from this contract;
any change that adds a prompt to this flow MUST update SC-001 in the same
change, and the automated check backing SC-001 asserts the exact count so
that drift is caught rather than silently absorbed.

Milling offers no calculation-mode prompt: only the standard mode is
supported (`spec.md` Assumptions), which is what keeps the milling flow to
one prompt more than drilling's despite its four extra numeric inputs.

Then calls `machine_calc.calculate_end_milling(...)` and displays the result
via an extended `_display_result()` that additionally prints
`material_removal_rate` when the field is not `None` (drilling's own display
path is unaffected, since drilling results always have `material_removal_rate
= None`).

## Face milling session prompts (new)

Identical shape to end milling, substituting:
- Face-mill tool selection (`_prompt_face_mill_tool_choice`).
- "Width of cut" prompt/label in place of "radial depth of cut" (still
  validated `<=` cutter diameter, FR-009 / User Story 3 Acceptance Scenario
  3).

Then calls `machine_calc.calculate_face_milling(...)`.

## Re-selection semantics (FR-017)

When the user answers "yes" to run another calculation, control returns to
`prompt_operation()` at the top of the outer loop, not directly back into
whichever session just ran. If the user re-selects the same operation/
sub-operation, all previously entered values for that specific flow are
retained as editable defaults exactly as drilling already does today
(`_prompt_*` functions' existing "reuse the previous answer as the default"
behavior) — only the operation/sub-operation choice itself is never
silently repeated without being asked again.

## Display contract addition

`_display_result()` gains one new conditional output line (metric example):

```text
Material removal rate: 24.00 cm^3/min
```

Localized via a new message-catalog key (e.g.
`cli.result.material_removal_rate`), following the existing pattern for
`cli.result.torque` / `cli.result.power`. Omitted entirely when
`material_removal_rate is None` (i.e., for every drilling result).
