import subprocess
import sys
import zipfile


def test_wheel_packages_console_entrypoint_and_runtime_metadata(tmp_path):
    wheel_dir = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", str(wheel_dir)],
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
