from types import SimpleNamespace

import pytest

from compare_all_strategies import _run_full_battle
from dominion.reporting.catalog_pages import render_catalog_pages
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategy_loader import StrategyLoader


@pytest.fixture
def retirement_loader(tmp_path):
    source = tmp_path / "retirement_fixture.py"
    source.write_text('''
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.retirement import retired_strategy

@retired_strategy(replacement="Replacement", reason="Lost the confirmation matches.", display_name="Original Province Strategy")
def create_old_strategy() -> EnhancedStrategy:
    result = EnhancedStrategy()
    result.name = "OldInternalName"
    return result

def create_replacement() -> EnhancedStrategy:
    return EnhancedStrategy()

def create_benchmark() -> EnhancedStrategy:
    return EnhancedStrategy()
''')
    loader = StrategyLoader.__new__(StrategyLoader)
    loader.strategies = {}
    loader._display_names = set()
    loader._load_from_directory(tmp_path, "retirement_fixture")
    return loader


def test_retired_aliases_and_factories_remain_explicitly_runnable(retirement_loader):
    loader = retirement_loader
    assert loader.list_strategies() == ["Benchmark", "Replacement"]
    assert loader.list_retired_strategies() == ["Old Strategy"]
    assert loader.list_strategies(include_retired=True) == ["Benchmark", "Old Strategy", "Replacement"]
    for alias in ["Old Strategy", "old-strategy", "old_strategy", "OldInternalName"]:
        assert loader.get_strategy(alias).name == "OldInternalName"
        assert loader.get_display_name(alias) == "Old Strategy"
    factory = loader.get_strategy_factory("Old Strategy")
    assert factory.retirement.replacement == "Replacement"
    assert factory().name == "OldInternalName"
    del factory.retirement
    assert "Old Strategy" in loader.list_strategies()
    assert loader.list_retired_strategies() == []


def test_default_tournament_excludes_archived_entrants(retirement_loader):
    with StrategyBattle(log_frequency=0) as battle:
        battle.strategy_loader = retirement_loader
        calls = []

        def run(first, second, games):
            calls.append((first, second))
            return {"strategy1_wins": 1, "strategy2_wins": 1}

        battle.run_battle = run
        results = _run_full_battle(battle, 2, None)
    assert set(results) == {"Benchmark", "Replacement"}
    assert calls == [("Benchmark", "Replacement")]


def test_catalog_preserves_archived_urls_without_active_board_links(tmp_path, retirement_loader):
    boards = tmp_path / "boards"
    boards.mkdir()
    (boards / "simple.txt").write_text("Village\nSmithy\n")
    output = tmp_path / "reports"
    render_catalog_pages(output, boards_root=boards, loader=retirement_loader)
    strategies = output / "strategies"
    archive = strategies / "old-strategy.html"
    html = archive.read_text()
    assert "Archived strategy." in html
    assert "<h1>Original Province Strategy</h1>" in html
    assert 'href="replacement.html"' in html
    assert "Lost the confirmation matches." in html
    assert 'href="old-strategy.html"' in (strategies / "archived-strategies.html").read_text()
    assert 'href="old-strategy.html"' not in (strategies / "index.html").read_text()
    assert "old-strategy.html" not in (output / "boards" / "simple.html").read_text()
    archive.write_text("stale")
    render_catalog_pages(output, boards_root=boards, loader=retirement_loader)
    assert archive.read_text() == html
    del retirement_loader.get_strategy_factory("Old Strategy").retirement
    render_catalog_pages(output, boards_root=boards, loader=retirement_loader)
    assert "Archived strategy." not in archive.read_text()
    assert not (strategies / "archived-strategies.html").exists()
    assert 'href="old-strategy.html"' in (strategies / "index.html").read_text()


def test_alternative_discovery_paths_skip_retired_factories(retirement_loader, tmp_path, monkeypatch):
    from dominion.analysis.strategy_library import _iter_strategy_factories
    from leaderboard import _find_factory

    module = SimpleNamespace(
        create_old=retirement_loader.get_strategy_factory("Old Strategy"),
        create_replacement=retirement_loader.get_strategy_factory("Replacement"),
    )
    assert _find_factory(module)[0] == "create_replacement"
    (tmp_path / "sample.py").write_text("")
    monkeypatch.setattr("dominion.analysis.strategy_library.importlib.import_module", lambda _: module)
    factories = list(_iter_strategy_factories([(tmp_path, "fixture")]))
    assert factories
    assert all(factory is module.create_replacement for _, factory in factories)
