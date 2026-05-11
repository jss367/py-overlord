import subprocess
import sys
import zipfile

import pytest


def test_wheel_packages_console_entrypoint_and_runtime_metadata(tmp_path):
    try:
        import setuptools.build_meta  # noqa: F401
    except ModuleNotFoundError:
        pytest.skip("setuptools.build_meta is required for no-isolation wheel build")

    wheel_dir = tmp_path / "dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
        ],
        check=True,
    )

    wheel_path = next(wheel_dir.glob("py_overlord-*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        dist_info_dir = next(
            name.rsplit("/", 1)[0] + "/" for name in names if name.endswith(".dist-info/METADATA")
        )
        entry_points = wheel.read(f"{dist_info_dir}entry_points.txt").decode()
        metadata = wheel.read(f"{dist_info_dir}METADATA").decode()

    assert "dominion/runner.py" in names
    assert "dominion-trainer = dominion.runner:main" in entry_points

    for dependency in ("coloredlogs", "matplotlib", "PyYAML", "scipy", "seaborn", "tqdm"):
        assert f"Requires-Dist: {dependency}" in metadata
