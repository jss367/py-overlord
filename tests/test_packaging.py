import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile

import pytest

from dominion.strategy.strategy_loader import StrategyLoader
from tests.strategy_discovery_probe import catalog_snapshot, make_shadow_package, probe_discovery


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

    assert "generated_strategies/mine_guildhall.py" in names
    assert "generated_strategies/tea_house_kind_emperor.py" in names
    assert "generated_strategies/__init__.py" in names

    # Keep cwd ahead of the wheel on sys.path in fresh ordinary processes.
    expected = catalog_snapshot(StrategyLoader())
    with TemporaryDirectory(prefix="dominion-wheel-test-") as directory:
        with zipfile.ZipFile(wheel_path) as wheel:
            wheel.extractall(directory)
        for regular in (False, True):
            working_directory = tmp_path / ("regular" if regular else "namespace")
            make_shadow_package(working_directory, regular=regular)
            assert probe_discovery(directory, working_directory) == expected
