"""Packaging test: bundled TOML files ship inside a built wheel (T017;
quickstart.md Scenario 2).

Invokes ``python -m build`` and inspects the resulting wheel's namelist.
Skipped if the ``build`` package is not installed (dev-only tooling).
"""

from __future__ import annotations

import glob
import subprocess
import sys
import zipfile

import pytest


def test_wheel_contains_bundled_materials_and_tools_toml(tmp_path):
    pytest.importorskip("build")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert (
        result.returncode == 0
    ), f"python -m build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    wheels = glob.glob(str(tmp_path / "*.whl"))
    assert wheels, "expected python -m build to produce a wheel"

    names = zipfile.ZipFile(wheels[0]).namelist()
    assert any(n.endswith("data/materials.toml") for n in names), names
    assert any(n.endswith("drilling/data/tools.toml") for n in names), names
