# Contract: Wood Materials Registry & Validation Behavior

**Feature**: [../spec.md](../spec.md) | **Data model**: [../data-model.md](../data-model.md)

## 1) Built-in wood entries (MVP)

The built-in registry MUST include these material names:

- Hardwood: `Oak`, `Maple`
- Soft wood: `Pine`, `Spruce`, `Fir`
- Engineered wood: `Plywood`, `MDF`

These entries MUST exist in bundled package data and be available with zero
configuration in both library and CLI flows.

## 2) Parameter schema requirements

Each wood entry MUST follow the existing material schema:

- `name` (string)
- `reference_cutting_speed` (numeric, expected > 0)
- `reference_feed_per_rev` (numeric, expected > 0)
- `specific_cutting_force` (numeric, expected > 0)
- optional `unit_system` (`metric`/`imperial`)
- optional `translations`

## 3) Load-time validation contract (FR-008)

During registry load/merge:

1. Validate required numeric fields for presence, type, and `> 0`.
2. On any invalid/missing parameter, log a **warning** with:
   - material name
   - source path (bundled/user file)
   - problematic field(s)
3. Continue initialization (no fatal abort from these validation issues).
4. Keep material registered/listable to support partial use and user overrides.

## 4) Calculation-time behavior

- Formula logic remains unchanged.
- If a user attempts calculation with a materially invalid entry (still in
  warning state), the operation must fail safely with a clear user-facing
  error instead of producing unreliable numeric output.

## 5) Packaging/distribution contract

- Wood entries MUST be present in bundled `materials.toml` and included in
  wheel/sdist package artifacts.
- Post-install listing behavior must match source-tree behavior.

## 6) Source traceability contract

Wood parameter values MUST be documented as sourced via multi-source
methodology:

- Machinery’s Handbook
- CNC machining guides
- ISO/industry standards

This traceability requirement applies to feature docs/release notes for the
wood entries.
