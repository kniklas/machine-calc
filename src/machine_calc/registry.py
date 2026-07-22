"""Shared workpiece material registry (FR-004).

Reference cutting-speed/feed values are canonical-metric, HSS-baseline
figures drawn from widely published machining data (Machinery's Handbook /
Sandvik Coromant general-purpose reference ranges for twist drilling); see
``specs/001-metal-drilling-calc/research.md`` #4. Drilling-tool factors
(``operations/drilling/tools.py``) multiply these baseline values.

Since ``specs/005-configurable-materials-tools``, the registry is built by
merging the bundled ``data/materials.toml`` package-data file with an
optional user-supplied override/addition file (``registry_config.py``),
rather than from a hard-coded Python list. Zero-config (``config_path=None``)
behavior is byte-for-byte identical to the pre-feature hard-coded registry
(FR-014, SC-002).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from machine_calc.registry_config import RawRegistryEntry, load_and_merge
from machine_calc.units import ft_min_to_m_min, in_to_mm, psi_to_n_per_mm2

_BUNDLED_PACKAGE = "machine_calc.data"
_BUNDLED_RESOURCE = "materials.toml"
_TABLE_KEY = "materials"

# TOML key -> dataclass field mapping (data-model.md "TOML key -> dataclass
# field mapping"). Dataclass field names are never renamed; only this
# parse-time mapping is new.
_FIELD_MAP = {
    "reference_cutting_speed": "reference_cutting_speed_m_min",
    "reference_feed_per_rev": "reference_feed_per_rev_mm",
    "specific_cutting_force": "specific_cutting_force_kc",
}


@dataclass(frozen=True)
class WorkpieceMaterial:
    """Reference machining data for a selectable workpiece material.

    Attributes:
        name: Unique display name, e.g. ``"Mild Steel"``.
        reference_cutting_speed_m_min: HSS-baseline cutting speed (vc) in
            m/min.
        reference_feed_per_rev_mm: HSS-baseline feed per revolution (fn) in
            mm/rev.
        specific_cutting_force_kc: Specific cutting force (Kc) in N/mm^2,
            used in torque/power calculations.
        unit_system: The unit system the entry was *authored*/declared in
            (``"metric"`` or ``"imperial"``); retained purely for
            display/audit after conversion (FR-011, FR-013) — calculation
            always uses the canonical-metric fields above.
        translations: Locale code -> translated display name (FR-009);
            empty by default.
    """

    name: str
    reference_cutting_speed_m_min: float
    reference_feed_per_rev_mm: float
    specific_cutting_force_kc: float
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)

    def display_name(self, locale: str) -> str:
        """Return the translated display name for ``locale``, or English fallback.

        Mirrors ``machine_calc.i18n.translate``'s English-fallback rule
        (research.md #7), but operates on data rather than the message
        catalog.
        """

        return self.translations.get(locale, self.name)


def _validate(material: WorkpieceMaterial) -> None:
    if material.reference_cutting_speed_m_min <= 0:
        raise ValueError(f"{material.name}: reference_cutting_speed_m_min must be positive")
    if material.reference_feed_per_rev_mm <= 0:
        raise ValueError(f"{material.name}: reference_feed_per_rev_mm must be positive")
    if material.specific_cutting_force_kc <= 0:
        raise ValueError(f"{material.name}: specific_cutting_force_kc must be positive")


def _to_material(entry: RawRegistryEntry) -> WorkpieceMaterial:
    """Convert a merged :class:`RawRegistryEntry` into a `WorkpieceMaterial`.

    Applies imperial->metric conversion of the three numeric fields when
    ``entry.unit_system == "imperial"`` (FR-012), via ``units.py`` helpers,
    before validation.
    """

    values: dict[str, float] = {}
    for toml_key, dataclass_field in _FIELD_MAP.items():
        try:
            raw_value = float(entry.fields[toml_key])
        except KeyError as exc:
            from machine_calc.registry_config import RegistryConfigError

            raise RegistryConfigError(
                "error.materials_config.invalid_entry",
                path=_BUNDLED_RESOURCE,
                kind="material",
                name=entry.name,
                details=f"missing required field {toml_key!r}",
            ) from exc
        values[dataclass_field] = raw_value

    if entry.unit_system == "imperial":
        values["reference_cutting_speed_m_min"] = ft_min_to_m_min(
            values["reference_cutting_speed_m_min"]
        )
        values["reference_feed_per_rev_mm"] = in_to_mm(values["reference_feed_per_rev_mm"])
        values["specific_cutting_force_kc"] = psi_to_n_per_mm2(values["specific_cutting_force_kc"])

    material = WorkpieceMaterial(
        name=entry.name,
        reference_cutting_speed_m_min=values["reference_cutting_speed_m_min"],
        reference_feed_per_rev_mm=values["reference_feed_per_rev_mm"],
        specific_cutting_force_kc=values["specific_cutting_force_kc"],
        unit_system=entry.unit_system,
        translations=dict(entry.translations),
    )
    _validate(material)
    return material


def _build_registry(config_path: str | None) -> dict[str, WorkpieceMaterial]:
    result = load_and_merge(_BUNDLED_PACKAGE, _BUNDLED_RESOURCE, config_path, _TABLE_KEY)
    registry: dict[str, WorkpieceMaterial] = {}
    for entry in result.entries:
        material = _to_material(entry)
        registry[material.name] = material
    return registry


# Bundled-only registry, built at import time (zero-config default, FR-014).
MATERIAL_REGISTRY: dict[str, WorkpieceMaterial] = _build_registry(None)


def list_materials(config_path: str | None = None) -> list[str]:
    """Return the currently registered workpiece material names (FR-004).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file (``contracts/materials-config-schema.md``).
            Defaults to ``None``, which reproduces the bundled-only,
            pre-``005-configurable-materials-tools`` behavior exactly
            (FR-014).
    """

    if config_path is None:
        return list(MATERIAL_REGISTRY.keys())
    return list(_build_registry(config_path).keys())


def get_material(name: str, config_path: str | None = None) -> WorkpieceMaterial | None:
    """Look up a registered material by name, or ``None`` if unknown.

    Args:
        name: The material's canonical English ``name``.
        config_path: Optional path to a user-supplied materials/tools
            configuration file; see :func:`list_materials`.
    """

    if config_path is None:
        return MATERIAL_REGISTRY.get(name)
    return _build_registry(config_path).get(name)
