"""Unit tests for unit conversion helpers (T016)."""

import math

from machine_calc.units import (
    hp_to_kw,
    in_lb_to_nm,
    in_to_mm,
    kw_to_hp,
    mm_to_in,
    nm_to_in_lb,
)


def test_mm_in_round_trip():
    original = 25.0
    assert math.isclose(in_to_mm(mm_to_in(original)), original, rel_tol=1e-9)


def test_mm_to_in_known_value():
    assert math.isclose(mm_to_in(25.4), 1.0, rel_tol=1e-6)


def test_in_to_mm_known_value():
    assert math.isclose(in_to_mm(1.0), 25.4, rel_tol=1e-9)


def test_nm_in_lb_round_trip():
    original = 3.1
    assert math.isclose(in_lb_to_nm(nm_to_in_lb(original)), original, rel_tol=1e-6)


def test_kw_hp_round_trip():
    original = 0.44
    assert math.isclose(hp_to_kw(kw_to_hp(original)), original, rel_tol=1e-6)


def test_kw_to_hp_known_value():
    assert math.isclose(kw_to_hp(1.0), 1.34102, rel_tol=1e-3)
