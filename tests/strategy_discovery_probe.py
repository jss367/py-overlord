"""Fresh-process discovery checks shared by source and wheel regressions."""

import json
import os
import subprocess
import sys
from textwrap import dedent


def catalog_snapshot(loader):
    return {
        "active": loader.list_strategies(),
        "retired": loader.list_retired_strategies(),
        "aliases": {
            alias: f"{factory.__module__}.{factory.__qualname__}"
            for alias, factory in loader.strategies.items()
        },
    }


def make_shadow_package(directory, *, regular):
    package = directory / "generated_strategies"
    package.mkdir(parents=True)
    (package / "tea_house_kind_emperor.py").write_text(
        "raise AssertionError('working-directory sibling was imported')\n",
        encoding="utf-8",
    )
    if regular:
        (package / "__init__.py").write_text(
            "raise AssertionError('working-directory package was imported')\n",
            encoding="utf-8",
        )


def probe_discovery(package_root, working_directory):
    # Ordinary -c deliberately leaves cwd first on sys.path. PYTHONPATH locates
    # only the source/wheel under test; no installed editable package is needed.
    program = dedent("""\
        import importlib
        import inspect
        import json
        from pathlib import Path
        import pickle
        import sys

        assert sys.path[0] == ''
        root = Path(sys.argv[1]).resolve()
        from dominion.strategy.strategy_loader import StrategyLoader
        assert Path(inspect.getfile(StrategyLoader)).resolve().is_relative_to(root)
        loader = StrategyLoader()
        mine = importlib.import_module('generated_strategies.mine_guildhall')
        tea = importlib.import_module('generated_strategies.tea_house_kind_emperor')
        for module in (mine, tea):
            assert Path(module.__file__).resolve().is_relative_to(root)
        factory = loader.get_strategy_factory('mine_guildhall')
        assert factory is mine.create_mine_and_guildhall_engine
        assert type(factory()) is mine.MineGuildhall
        assert isinstance(factory(), tea.TeaHouseEmperor)
        assert pickle.loads(pickle.dumps(factory)) is factory
        assert pickle.loads(pickle.dumps(type(factory()))) is mine.MineGuildhall
        assert StrategyLoader().get_strategy_factory('mine_guildhall') is factory
        print(json.dumps({
            'active': loader.list_strategies(),
            'retired': loader.list_retired_strategies(),
            'aliases': {
                alias: f'{factory.__module__}.{factory.__qualname__}'
                for alias, factory in loader.strategies.items()
            },
        }))
    """)
    process = subprocess.run(
        [sys.executable, "-c", program, str(package_root)],
        cwd=working_directory,
        env={**os.environ, "PYTHONPATH": str(package_root)},
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    return json.loads(process.stdout)
