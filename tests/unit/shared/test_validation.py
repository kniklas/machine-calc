"""Unit tests for shared input validation (T015)."""

from machine_calc.config import Configuration
from machine_calc.validation import (
    validate_depth_mm,
    validate_diameter_mm,
    validate_material_present,
    validate_tool_present,
)

CONFIG = Configuration()


def test_diameter_zero_is_invalid():
    error = validate_diameter_mm(0, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_negative_is_invalid():
    error = validate_diameter_mm(-5, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_within_bounds_is_valid():
    assert validate_diameter_mm(10, CONFIG) is None


def test_diameter_exceeding_default_max_is_invalid():
    error = validate_diameter_mm(150, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_at_exact_max_is_valid():
    assert validate_diameter_mm(CONFIG.max_diameter_mm, CONFIG) is None


def test_depth_zero_is_invalid():
    error = validate_depth_mm(0, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_negative_is_invalid():
    error = validate_depth_mm(-1, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_exceeding_default_max_is_invalid():
    error = validate_depth_mm(600, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_within_bounds_is_valid():
    assert validate_depth_mm(25, CONFIG) is None


def test_missing_material_is_invalid():
    error = validate_material_present(None)
    assert error is not None
    assert error.code == "MISSING_MATERIAL"

    error = validate_material_present("")
    assert error is not None
    assert error.code == "MISSING_MATERIAL"


def test_present_material_is_valid():
    assert validate_material_present("Mild Steel") is None


def test_missing_tool_is_invalid():
    error = validate_tool_present(None)
    assert error is not None
    assert error.code == "MISSING_TOOL"


def test_present_tool_is_valid():
    assert validate_tool_present("Carbide") is None


def test_custom_configuration_bounds_are_respected():
    config = Configuration(max_diameter_mm=150.0, max_depth_mm=600.0)
    assert validate_diameter_mm(120, config) is None
    assert validate_depth_mm(550, config) is None
