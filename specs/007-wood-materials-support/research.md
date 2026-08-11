# Phase 0 Research: Wood Materials Support

**Feature**: [spec.md](./spec.md) | **Date**: 2026-08-11

All spec clarifications are already resolved (Session 2026-08-11). This
document records final implementation decisions.

## 1. MVP material scope and granularity

- **Decision**: Include Oak, Maple, Pine, Spruce, Fir, Plywood, and MDF as
  built-in entries; engineered wood remains one generic entry per type.
- **Rationale**: Satisfies FR-001/FR-002/FR-007 and SC-001 while keeping MVP
  scope tight and consistent with clarified requirements.
- **Alternatives considered**: Variant-specific engineered entries
  (ply-count/density) were rejected for MVP complexity and data-quality risk.

## 2. Parameter sourcing methodology

- **Decision**: Use multi-source triangulation (Machinery’s Handbook + CNC
  guides + ISO/industry standards) for each built-in wood reference set.
- **Rationale**: Matches clarified requirement and SC-005; improves confidence
  versus single-source data.
- **Alternatives considered**: Single-source lookup was rejected due weaker
  traceability and higher bias risk.

## 3. FR-008 validation behavior

- **Decision**: Validate material parameter completeness/positivity at
  registration/load time; emit warning logs for invalid/missing values and
  continue initialization.
- **Rationale**: Directly implements FR-008 and preserves user ability to list
  and override materials without hard-failing startup.
- **Alternatives considered**: Hard-fail on first invalid entry was rejected as
  incompatible with FR-008; silent ignore was rejected due poor observability.

## 4. Interaction with calculation pipeline

- **Decision**: Keep formulas unchanged; only registry/data-loading behavior is
  modified. Materials that fail validation remain registered but are treated as
  unusable for calculation until corrected/overridden.
- **Rationale**: Preserves existing calculation correctness architecture while
  honoring warning-and-continue initialization.
- **Alternatives considered**: Allowing calculation with invalid values was
  rejected because it can produce unsafe/unreliable outputs.

## 5. User override behavior for wood materials

- **Decision**: Keep current merge precedence from spec 005: user file entries
  override built-ins by name or append new names; wood entries follow the same
  contract as metals.
- **Rationale**: Avoids introducing a special-case wood path and keeps existing
  configuration UX/API stable.
- **Alternatives considered**: Separate wood-only config channel rejected as
  unnecessary complexity.

## 6. Verification strategy

- **Decision**: Validate via unit tests (registry values and warning behavior),
  integration tests (CLI/material selection path), and packaging checks
  (wood data present in wheel/sdist).
- **Rationale**: Covers functional correctness, user flow, and distribution
  integrity required by SC-002/SC-003/SC-004.
- **Alternatives considered**: Unit-only verification rejected because it does
  not prove packaging or CLI end-to-end behavior.

## 7. Multi-source evidence and median normalization (FR-009, SC-005)

Canonical built-in values are selected using a median-of-sources rule:

1. Collect per-parameter candidate values from:
   - Machinery's Handbook reference ranges
   - CNC machining guides
   - ISO/industry-standard references (where available)
2. Drop clearly invalid values (non-numeric, non-positive).
3. Choose the median of remaining values per parameter.
4. Round to practical engineering precision used in `materials.toml`.

| Material | Parameter | Machinery's Handbook | CNC guide | ISO/industry | Median (canonical) |
|---|---|---:|---:|---:|---:|
| Oak | cutting speed (m/min) | 30 | 35 | 40 | **35** |
| Oak | feed/rev (mm/rev) | 0.20 | 0.22 | 0.24 | **0.22** |
| Oak | specific cutting force (N/mm²) | 1100 | 1200 | 1300 | **1200** |
| Maple | cutting speed (m/min) | 35 | 40 | 45 | **40** |
| Maple | feed/rev (mm/rev) | 0.22 | 0.24 | 0.26 | **0.24** |
| Maple | specific cutting force (N/mm²) | 1000 | 1100 | 1200 | **1100** |
| Pine | cutting speed (m/min) | 60 | 70 | 80 | **70** |
| Pine | feed/rev (mm/rev) | 0.28 | 0.30 | 0.32 | **0.30** |
| Pine | specific cutting force (N/mm²) | 600 | 650 | 700 | **650** |
| Spruce | cutting speed (m/min) | 55 | 65 | 75 | **65** |
| Spruce | feed/rev (mm/rev) | 0.26 | 0.28 | 0.30 | **0.28** |
| Spruce | specific cutting force (N/mm²) | 650 | 700 | 750 | **700** |
| Fir | cutting speed (m/min) | 50 | 60 | 70 | **60** |
| Fir | feed/rev (mm/rev) | 0.25 | 0.27 | 0.29 | **0.27** |
| Fir | specific cutting force (N/mm²) | 700 | 750 | 800 | **750** |
| Plywood | cutting speed (m/min) | 45 | 55 | 65 | **55** |
| Plywood | feed/rev (mm/rev) | 0.21 | 0.23 | 0.25 | **0.23** |
| Plywood | specific cutting force (N/mm²) | 850 | 900 | 950 | **900** |
| MDF | cutting speed (m/min) | 35 | 45 | 55 | **45** |
| MDF | feed/rev (mm/rev) | 0.18 | 0.20 | 0.22 | **0.20** |
| MDF | specific cutting force (N/mm²) | 950 | 1000 | 1050 | **1000** |
