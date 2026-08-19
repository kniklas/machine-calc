"""Shared milling tool-registry machinery for both milling sub-operations.

End-mill and face-mill tools have the same shape — a name, a
cutting-speed multiplier applied to the workpiece material's baseline
cutting speed, a declared unit system, and optional translations — and are
built from a bundled TOML file merged with an optional user override by the
existing shared :func:`machine_calc.registry_config.load_and_merge` helper.

Only the bundled resource package and the TOML table key differ between the
two sub-operations, so the parsing/validation/merging logic lives here once
(Constitution Principle VI: cross-cutting concerns are shared, not
duplicated) while each sub-operation keeps its own distinct dataclass type,
its own bundled data file, and — critically — its own ``table_key``.

The distinct table keys (``end_mill_tools``/``face_mill_tools`` versus
drilling's ``tools``) are load-bearing, not cosmetic: users supply a single
configuration file for the whole application, and drilling's tool entries
require a ``feed_factor`` field that milling entries do not have. Sharing a
key would inject milling entries into the drilling registry and break the
already-shipped drilling flow (see
``specs/009-milling-calculations/contracts/milling-tools-config-schema.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from machine_calc.registry_config import RawRegistryEntry, RegistryConfigError, load_and_merge


@dataclass(frozen=True)
class MillingTool:
    """Reference data for a selectable milling cutter type.

    Subclassed (without adding fields) by
    :class:`~machine_calc.operations.milling.end_milling.tools.EndMillTool`
    and
    :class:`~machine_calc.operations.milling.face_milling.tools.FaceMillTool`
    so the two registries stay distinct, independently evolvable types.

    Attributes:
        name: Unique display name, e.g. ``"Carbide"``.
        cutting_speed_factor: Multiplier applied to the material's baseline
            reference cutting speed; must be ``> 0``.
        unit_system: The unit system declared for this entry (``"metric"``
            or ``"imperial"``); accepted, stored, and displayed, but
            performs no numeric conversion — the factor is a dimensionless
            ratio relative to the material's own reference value, so it
            carries no independent physical unit to convert. This mirrors
            ``DrillingTool.unit_system``'s documented no-op.
        translations: Locale code -> translated display name; empty by
            default.

    There is deliberately no ``feed_factor``: for milling, feed per tooth is
    a direct per-calculation input rather than a registry-derived multiplier
    (research.md #4).
    """

    name: str
    cutting_speed_factor: float
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)

    def display_name(self, locale: str) -> str:
        """Return the translated display name for ``locale``, or English fallback.

        Mirrors ``WorkpieceMaterial.display_name`` and
        ``DrillingTool.display_name``.
        """

        return self.translations.get(locale, self.name)


ToolT = TypeVar("ToolT", bound=MillingTool)


def _to_tool(
    tool_cls: type[ToolT], entry: RawRegistryEntry, bundled_resource: str, kind: str
) -> ToolT:
    """Convert a merged :class:`RawRegistryEntry` into a ``tool_cls`` instance.

    No unit conversion is performed regardless of ``entry.unit_system`` —
    ``cutting_speed_factor`` is dimensionless — the declared unit system is
    stored/displayed only.

    Raises:
        RegistryConfigError: If the required ``cutting_speed_factor`` field
            is missing, non-numeric, or not positive. The reported path is
            the entry's own ``source_path`` so a user-supplied file is
            blamed accurately rather than the bundled file.
    """

    source_path = entry.source_path or bundled_resource
    try:
        cutting_speed_factor = float(entry.fields["cutting_speed_factor"])
    except KeyError as exc:
        raise RegistryConfigError(
            "error.materials_config.invalid_entry",
            path=source_path,
            kind=kind,
            name=entry.name,
            details="missing required field 'cutting_speed_factor'",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise RegistryConfigError(
            "error.materials_config.invalid_entry",
            path=source_path,
            kind=kind,
            name=entry.name,
            details=(
                "field 'cutting_speed_factor' must be a number, got "
                f"{entry.fields['cutting_speed_factor']!r}"
            ),
        ) from exc

    if cutting_speed_factor <= 0:
        raise RegistryConfigError(
            "error.materials_config.invalid_entry",
            path=source_path,
            kind=kind,
            name=entry.name,
            details="cutting_speed_factor must be positive",
        )

    return tool_cls(
        name=entry.name,
        cutting_speed_factor=cutting_speed_factor,
        unit_system=entry.unit_system,
        translations=dict(entry.translations),
    )


def build_registry(
    tool_cls: type[ToolT],
    bundled_package: str,
    bundled_resource: str,
    table_key: str,
    config_path: str | None,
) -> dict[str, ToolT]:
    """Build a milling tool registry from bundled data plus an optional override.

    Args:
        tool_cls: The concrete :class:`MillingTool` subclass to construct.
        bundled_package: Package holding the bundled TOML resource.
        bundled_resource: Bundled TOML filename within that package.
        table_key: The TOML array-of-tables key this registry owns — e.g.
            ``"end_mill_tools"``. MUST be unique across every registry in
            the application (see this module's docstring).
        config_path: Optional path to a user-supplied configuration file.

    Returns:
        A name -> tool mapping in bundled-then-appended order.
    """

    result = load_and_merge(bundled_package, bundled_resource, config_path, table_key)
    kind = table_key[:-1]
    return {
        entry.name: _to_tool(tool_cls, entry, bundled_resource, kind) for entry in result.entries
    }
