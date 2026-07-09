"""machine_calc: metal machining calculations library and interactive CLI.

Public surface (contracts/library-api.md)::

    from machine_calc import calculate, list_materials, list_tools, UnitSystem

Currently exposes drilling calculations (``operations.drilling``); future
operations (turning, milling, ...) will add their own
``machine_calc.operations.<operation>`` module per Constitution Principle VI
without changing this drilling contract.
"""

from __future__ import annotations

from machine_calc.models import CalculationResult, ErrorInfo, UnitSystem
from machine_calc.operations.drilling import calculate
from machine_calc.operations.drilling.tools import list_tools
from machine_calc.registry import list_materials

__all__ = [
    "calculate",
    "list_materials",
    "list_tools",
    "UnitSystem",
    "CalculationResult",
    "ErrorInfo",
]

__version__ = "0.1.0"
