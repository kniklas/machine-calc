"""Shared TOML configuration loading (FR-018; research.md #3, #5).

Configuration overrides the default validation bounds (max diameter/depth).
When the file or a given key is absent, built-in defaults are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+ ships tomllib in the standard library.
    import tomllib
except ModuleNotFoundError:  # Python 3.9 / 3.10 fall back to the tomli backport.
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_MAX_DIAMETER_MM = 100.0
DEFAULT_MAX_DEPTH_MM = 500.0


@dataclass(frozen=True)
class Configuration:
    """Effective validation bounds, in canonical metric units.

    Attributes:
        max_diameter_mm: Maximum allowed drill diameter, in mm.
        max_depth_mm: Maximum allowed hole depth, in mm.
    """

    max_diameter_mm: float = DEFAULT_MAX_DIAMETER_MM
    max_depth_mm: float = DEFAULT_MAX_DEPTH_MM


def load_configuration(config_path: str | None = None) -> Configuration:
    """Load a :class:`Configuration` from an optional TOML file.

    Args:
        config_path: Path to a TOML file with optional ``max_diameter_mm``
            and ``max_depth_mm`` keys. If ``None`` or the file does not
            exist, built-in defaults are used. If the file exists but a key
            is missing, that key's default is used.

    Returns:
        A :class:`Configuration` with the effective bounds.
    """

    if config_path is None:
        return Configuration()

    path = Path(config_path)
    if not path.is_file():
        return Configuration()

    with path.open("rb") as fh:
        data = tomllib.load(fh)

    return Configuration(
        max_diameter_mm=float(data.get("max_diameter_mm", DEFAULT_MAX_DIAMETER_MM)),
        max_depth_mm=float(data.get("max_depth_mm", DEFAULT_MAX_DEPTH_MM)),
    )
