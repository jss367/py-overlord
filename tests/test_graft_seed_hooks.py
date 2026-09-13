"""``scripts/graft_seed_hooks.py`` re-bases old champion exports onto their
seed class without letting the seed's ``__init__`` change the strategy."""

import importlib.util

import pytest

from dominion.strategy.strategies.albuquerque_seeds import (
    AlbuquerqueChapelBridgeEngine,
    AlbuquerqueStrategy,
)
from dominion.strategy.strategy_loader import StrategyLoader
from scripts.graft_seed_hooks import STANDARD_LISTS, graft

SEED_IMPORT = (
    "from dominion.strategy.strategies.albuquerque_seeds import "
    "AlbuquerqueChapelBridgeEngine as _SeedBase"
)

OLD_CHAMPION = (
    "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule\n"
    "\n\n"
    "class Old(EnhancedStrategy):\n"
    "    def __init__(self) -> None:\n"
    "        super().__init__()\n"
    "        self.name = 'Old'\n"
    "        self.gain_priority = [PriorityRule('Province')]\n"
    "        self.action_priority = [PriorityRule('Bridge')]\n"
    "        self.way_policy = []\n"
    "\n\n"
    "def create_old() -> EnhancedStrategy:\n"
    "    return Old()\n"
)


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def loader():
    return StrategyLoader()


@pytest.fixture
def dirs(tmp_path):
    run_dir = tmp_path / "run"
    out_dir = tmp_path / "out"
    run_dir.mkdir()
    out_dir.mkdir()
    return run_dir, out_dir


def _write_old(run_dir, text=OLD_CHAMPION):
    champion = run_dir / "albuquerque_chapel_bridge_engine_champion.py"
    champion.write_text(text)
    return champion


def test_lists_absent_from_the_old_export_are_pinned_to_empty(dirs, loader):
    """The seed's ``__init__`` fills trash/treasure/exile lists; an old export
    that omitted them (because evolution emptied them) must not get them back."""
    run_dir, out_dir = dirs
    champion = _write_old(run_dir)
    seed = AlbuquerqueChapelBridgeEngine()
    assert seed.trash_priority and seed.treasure_priority

    assert graft(champion, out_dir, loader).startswith("grafted onto")
    text = (out_dir / champion.name).read_text()
    lines = text.splitlines()
    init_at = lines.index("        super().__init__()")
    pinned = lines[init_at + 1 : init_at + 4]
    assert pinned == [
        "        self.treasure_priority = []",
        "        self.trash_priority = []",
        "        self.bounty_hunter_exile_priority = []",
    ]

    grafted = _load(out_dir / champion.name).create_old()
    assert isinstance(grafted, AlbuquerqueStrategy)
    assert grafted.trash_priority == []
    assert grafted.treasure_priority == []
    assert grafted.bounty_hunter_exile_priority == []


def test_lists_present_in_the_old_export_are_left_untouched(dirs, loader):
    run_dir, out_dir = dirs
    champion = _write_old(run_dir)

    graft(champion, out_dir, loader)
    text = (out_dir / champion.name).read_text()
    for name in ("gain_priority", "action_priority", "way_policy"):
        assert text.count(f"self.{name} = ") == 1, name
    assert "        self.gain_priority = [PriorityRule('Province')]" in text
    assert "        self.action_priority = [PriorityRule('Bridge')]" in text
    assert "        self.way_policy = []" in text

    grafted = _load(out_dir / champion.name).create_old()
    assert [r.card for r in grafted.gain_priority] == ["Province"]
    assert [r.card for r in grafted.action_priority] == ["Bridge"]
    assert grafted.way_policy == []
    # multiplier_priority is intentionally the seed's: the trainer never
    # mutates it, so this is what the champion used during evaluation.
    assert [r.card for r in grafted.multiplier_priority][:2] == ["King's Court", "Bridge"]


def test_graft_keeps_way_rule_on_the_original_import(dirs, loader):
    run_dir, out_dir = dirs
    champion = _write_old(run_dir)

    graft(champion, out_dir, loader)
    lines = (out_dir / champion.name).read_text().splitlines()
    assert lines[0] == (
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule"
    )
    assert lines[1] == SEED_IMPORT
    assert "class Old(_SeedBase):" in lines


def test_already_grafted_file_is_copied_unchanged(dirs, loader):
    run_dir, out_dir = dirs
    already = (
        "from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule\n"
        f"{SEED_IMPORT}\n"
        "\n\n"
        "class Done(_SeedBase):\n"
        "    def __init__(self) -> None:\n"
        "        super().__init__()\n"
        "        self.name = 'Done'\n"
        "        self.gain_priority = [PriorityRule('Province')]\n"
        "\n\n"
        "def create_done() -> EnhancedStrategy:\n"
        "    return Done()\n"
    )
    champion = _write_old(run_dir, already)

    assert graft(champion, out_dir, loader) == "kept"
    assert (out_dir / champion.name).read_text() == already


def test_standard_lists_match_the_enhanced_strategy_attributes():
    from dominion.strategy.enhanced_strategy import EnhancedStrategy

    plain = EnhancedStrategy()
    for name in STANDARD_LISTS:
        assert getattr(plain, name) == [], name
