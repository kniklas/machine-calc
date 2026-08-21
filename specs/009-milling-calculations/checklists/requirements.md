# Specification Quality Checklist: Milling Calculations Module

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Five clarification questions were resolved with the user across the `/speckit.specify` and `/speckit.clarify` sessions: (1) milling scope — end + face milling as distinct sub-operations; (2) feed input style — feed-per-tooth + flute count; (3) added a required "length of cut" input for machining-time calculation; (4) milling torque/power based on per-material specific cutting force (kc) and chip cross-sectional area; (5) face milling assumes full/symmetric cutter engagement, no chip-thinning/entry-exit-angle modeling. No [NEEDS CLARIFICATION] markers remain.
- All items pass validation.
- `/speckit.analyze` (post-`/speckit.tasks`) raised 15 findings; the top ones were remediated directly in the artifacts:
  - **F1 (CRITICAL)** registry key collision — each tool registry now has a distinct `table_key` (`tools` / `end_mill_tools` / `face_mill_tools`), documented normatively in data-model.md and the new `contracts/milling-tools-config-schema.md`, reflected in FR-015, and enforced by the new isolation regression task T011c.
  - **C1 (CRITICAL)** unachievable prompt budget — SC-001 restated as "at most 14 prompts / 12 typed values", derived from the new "Prompt-count budget" section in the CLI contract and asserted by new task T023a.
  - **F2 (HIGH)** FR-007 reworded: face milling is separately selectable with its own tools/labels/validation, while explicitly permitting a shared internal formula core under the full-engagement assumption.
  - **F3 (HIGH)** Key Entities "Milling Tool" corrected: the tool carries only a cutting-speed factor; tooth count and feed per tooth are per-calculation inputs.
  - **G1 (HIGH)** FR-010 redefined around unusable material reference data (missing/non-positive kc); the unreachable `MISSING_MATERIAL_TOOL_COMBINATION` error code was removed from data-model.md.
  - Also addressed: G2 (published-reference accuracy fixtures, T011a), G3 (imperial round-trip test, T023b), U1 (new FR-018 for configurable bounds + rationale for the default values), U2 (whole-number tooth count in FR-008, T011b), U3 (pre-refactor drilling baseline capture, T013a), I1 (version-source consolidation folded into T052), A1 (net-vs-motor power documented in spec Assumptions, research.md #1 and the library contract), I2/I3 (contract field-order and calculation-mode notes).
- Task count is now 59 (T001–T052 plus T011a/b/c/d, T013a, T023a/b).
- A second `/speckit.analyze` pass after remediation reported **0 CRITICAL issues** and cleared all previously flagged findings. Its residual findings were also applied: US3 narrative and Assumptions no longer claim face milling has "its own formulas" (they now say its own tools/inputs/labelling/validation); the Edge Cases material bullet was rewritten around FR-010's unusable-reference-data failure; FR-018 is now cited by T006/T008 and verified by new task T011d (bound-override test); FR-010/SC-003 are now cited explicitly by T022/T032 with a missing/non-positive-`kc` case; FR-014's module boundary is asserted by T039; and T023a documents that its exact prompt count is a tripwire for SC-001's ceiling.
