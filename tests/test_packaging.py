import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from textwrap import dedent
import zipfile

import pytest

from dominion.strategy.strategy_loader import StrategyLoader


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

    # Load the wheel's actual modules from outside the checkout, including a
    # generated strategy that imports another generated strategy.
    with TemporaryDirectory(prefix="dominion-wheel-test-") as directory:
        with zipfile.ZipFile(wheel_path) as wheel:
            wheel.extractall(directory)
        process = subprocess.run(
            [
                sys.executable, "-I", "-c",
                dedent("""\
                    import inspect
                    import json
                    from pathlib import Path
                    import sys

                    sys.path.insert(0, sys.argv[1])
                    from dominion.strategy.strategy_loader import StrategyLoader

                    assert Path(inspect.getfile(StrategyLoader)).is_relative_to(Path(sys.argv[1]))
                    loader = StrategyLoader()
                    assert loader.get_strategy('mine_guildhall') is not None
                    print(json.dumps(loader.list_strategies(include_retired=True)))
                """),
                directory,
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
    assert json.loads(process.stdout) == StrategyLoader().list_strategies(include_retired=True)
