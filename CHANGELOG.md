# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-11

### Added

- Built-in wood workpiece materials (specs/007-wood-materials-support):
  hardwoods **Oak, Maple**; softwoods **Pine, Spruce, Fir**; engineered
  woods **Plywood, MDF** (one generic entry per type). Reference values are
  derived as the median of multiple authoritative sources (Machinery's
  Handbook, CNC machining guides, ISO/industry standards); see
  `specs/007-wood-materials-support/research.md` §7 for citations.
- `WorkpieceMaterial.is_usable` property and
  `machine_calc.registry.get_material_validation()` to inspect load-time
  validation status of a registered material before using its numeric
  fields.
- New translated error code `UNUSABLE_MATERIAL` returned by `calculate()`
  when a selected material was registered with invalid parameters.

### Changed

- **Behavior change (FR-008, warn-and-continue):** invalid material entries
  in a user-supplied `--materials-config` file (missing, non-numeric,
  non-finite, or non-positive cutting speed / feed / specific cutting
  force) no longer abort CLI startup with a fatal `RegistryConfigError`.
  The entry is registered, a warning is logged identifying the source file
  and issue, and startup/listing continues; calculations that select such
  an entry fail safely with the `UNUSABLE_MATERIAL` error instead of
  computing a wrong number. Malformed TOML and duplicate names within one
  file remain fatal errors.
- Registry snapshots for user-supplied config paths are now cached per
  path for the lifetime of the process (previously re-read on each
  lookup); edit-and-reload of a config file requires restarting the CLI.

## [0.1.0]

- Initial release: metric/imperial drilling calculations, constrained
  calculation modes, configurable materials/tools via TOML, i18n message
  catalog, CI quality/security gates.
