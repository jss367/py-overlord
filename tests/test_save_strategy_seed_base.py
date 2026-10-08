"""Exported champions evolved from a hand-written seed keep the seed's hooks."""

import copy
import importlib.util

import pytest

from dominion.runner import save_strategy_as_python
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategies.albuquerque_seeds import (
    AlbuquerqueChapelBridgeEngine,
    AlbuquerqueStrategy,
)


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_subclass_is_preserved_as_base(tmp_path):
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.name = "Evolved"
    strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Silver")]
    strategy.multiplier_priority = [PriorityRule("Bridge")]

    out = tmp_path / "champion.py"
    save_strategy_as_python(strategy, out, "Champion", clean_for_publication=False)
    text = out.read_text()
    assert "import AlbuquerqueChapelBridgeEngine as _SeedBase" in text
    assert "class Champion(_SeedBase):" in text

    module = _load(out)
    champion = module.create_champion()
    assert isinstance(champion, AlbuquerqueStrategy)
    assert [r.card for r in champion.gain_priority] == ["Province", "Silver"]
    assert [r.card for r in champion.multiplier_priority] == ["Bridge"]


def test_plain_strategy_still_exports_enhanced_strategy(tmp_path):
    strategy = EnhancedStrategy()
    strategy.name = "Plain"
    strategy.gain_priority = [PriorityRule("Province")]
    out = tmp_path / "plain.py"
    save_strategy_as_python(strategy, out, "Plain", clean_for_publication=False)
    text = out.read_text()
    assert "class Plain(EnhancedStrategy):" in text
    assert "_SeedBase" not in text
    assert _load(out).create_plain().name == "Plain"


def test_loader_instantiated_seed_is_recognised(tmp_path):
    from dominion.strategy.strategy_loader import StrategyLoader

    strategy = StrategyLoader().get_strategy("Albuquerque Masquerade Bridge Engine")
    out = tmp_path / "loader_champion.py"
    save_strategy_as_python(strategy, out, "LoaderChampion", clean_for_publication=False)
    assert "AlbuquerqueMasqueradeBridgeEngine as _SeedBase" in out.read_text()
    assert isinstance(_load(out).create_loaderchampion(), AlbuquerqueStrategy)


def test_seed_export_serializes_lists_emptied_by_evolution(tmp_path):
    """A list that evolved (or was cleaned) to empty must be written out, or
    the seed's ``__init__`` would restore its own list when the module loads."""
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.name = "Thin"
    assert strategy.trash_priority and strategy.action_priority
    strategy.trash_priority = []
    strategy.action_priority = []
    strategy.multiplier_priority = []

    out = tmp_path / "thin.py"
    save_strategy_as_python(strategy, out, "Thin", clean_for_publication=False)
    text = out.read_text()
    assert "self.trash_priority = []" in text
    assert "self.action_priority = []" in text
    assert "self.multiplier_priority = []" in text

    champion = _load(out).create_thin()
    assert champion.trash_priority == []
    assert champion.action_priority == []
    assert champion.multiplier_priority == []
    assert [r.card for r in champion.gain_priority] == [
        r.card for r in strategy.gain_priority
    ]


def test_island_champion_subclass_keeps_seed_ancestor_as_base(tmp_path):
    """``island_merge`` loads champions under a throwaway ``champion_<stem>``
    module and the trainer deep-copies that class, so the concrete class is
    not importable; the export must fall back to the nearest seed ancestor."""
    from scripts.island_merge import _load_strategy_from_path

    first = AlbuquerqueChapelBridgeEngine()
    first.name = "Island Champion"
    first.gain_priority = [PriorityRule("Province")]
    island_file = tmp_path / "albuquerque_chapel_bridge_engine_champion.py"
    save_strategy_as_python(first, island_file, "IslandChampion", clean_for_publication=False)

    loaded = _load_strategy_from_path(island_file)
    assert type(loaded).__module__.startswith("champion_")
    merged = copy.deepcopy(loaded)
    merged.name = "Merged"
    merged.gain_priority = [PriorityRule("Province"), PriorityRule("Bridge")]

    out = tmp_path / "merged.py"
    save_strategy_as_python(merged, out, "Merged", clean_for_publication=False)
    text = out.read_text()
    assert (
        "from dominion.strategy.strategies.albuquerque_seeds import "
        "AlbuquerqueChapelBridgeEngine as _SeedBase"
    ) in text
    assert "class Merged(_SeedBase):" in text

    champion = _load(out).create_merged()
    assert isinstance(champion, AlbuquerqueStrategy)
    assert [r.card for r in champion.gain_priority] == ["Province", "Bridge"]
    assert [r.card for r in champion.multiplier_priority] == [
        r.card for r in merged.multiplier_priority
    ]


@pytest.mark.parametrize("derived", [False, True])
@pytest.mark.parametrize("clean", [False, True])
@pytest.mark.parametrize("mode", ["inherit", "baseline", "rules"])
def test_new_priority_fields_roundtrip_without_restoring_seed_defaults(tmp_path, monkeypatch, derived, clean, mode):
    original_init = AlbuquerqueChapelBridgeEngine.__init__
    def seeded_init(self):
        original_init(self)
        self.free_gain_priority = [PriorityRule("Village")]
        self.captain_target_priority = [PriorityRule("Village")]
        self.band_of_misfits_target_priority = [PriorityRule("Militia")]
    monkeypatch.setattr(AlbuquerqueChapelBridgeEngine, "__init__", seeded_init)
    strategy = AlbuquerqueChapelBridgeEngine() if derived else EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver")]
    strategy.free_gain_priority = {
        "inherit": None,
        "baseline": [],
        "rules": [PriorityRule("Smithy", PriorityRule.resources("coins", ">=", 4))],
    }[mode]
    strategy.captain_target_priority = []
    strategy.band_of_misfits_target_priority = [PriorityRule("Smithy", PriorityRule.resources("actions", ">=", 1))]
    path = tmp_path / "roundtrip.py"
    save_strategy_as_python(strategy, path, "RoundTrip", clean_for_publication=clean)
    restored = _load(path).create_roundtrip()
    assert (restored.free_gain_priority is None) == (mode == "inherit")
    assert [r.card_name for r in restored.free_gain_priority or []] == (["Smithy"] if mode == "rules" else [])
    assert restored.captain_target_priority == []
    assert [r.card_name for r in restored.band_of_misfits_target_priority] == ["Smithy"]
    from tests.test_shared_card_tactics import make_state
    from dominion.ai.gain_context import FreeGainContext
    from dominion.cards.registry import get_card
    state, player = make_state(names=("Silver", "Smithy"))
    choices = [get_card("Silver"), get_card("Smithy")]
    for coins in (0, 4):
        player.coins = coins
        context = FreeGainContext.build(state, player, "Workshop")
        assert restored.choose_free_gain(state, player, choices, context).name == strategy.choose_free_gain(state, player, choices, context).name
    for actions in (0, 1):
        player.actions = actions
        assert restored.choose_band_of_misfits_target(state, player, choices).name == strategy.choose_band_of_misfits_target(state, player, choices).name


def test_optimal_export_uses_shared_serializer_without_training(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import dominion.optimal_strategy_runner as optimal
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.free_gain_priority = []
    strategy.captain_target_priority = [PriorityRule("Smithy")]
    strategy.band_of_misfits_target_priority = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(optimal, "GeneticTrainer", lambda **kwargs: SimpleNamespace(
        train=lambda: (strategy, {"win_rate": 50}),
    ))
    returned, _ = optimal.train_optimal_strategy()
    restored = _load(tmp_path / "strategies/optimal_strategy.py").create_optimal_strategy()
    assert returned is strategy
    assert isinstance(restored, AlbuquerqueStrategy)
    assert restored.free_gain_priority == []
    assert [r.card_name for r in restored.captain_target_priority] == ["Smithy"]
    assert restored.band_of_misfits_target_priority == []


@pytest.mark.parametrize("free_gain", [None, [], [PriorityRule("Smithy")]])
def test_parallel_worker_serialization_keeps_new_configuration(free_gain):
    import cloudpickle
    strategy = AlbuquerqueChapelBridgeEngine()
    strategy.free_gain_priority = free_gain
    strategy.captain_target_priority = []
    strategy.band_of_misfits_target_priority = [PriorityRule("Militia")]
    restored = cloudpickle.loads(cloudpickle.dumps(strategy))
    assert (restored.free_gain_priority is None) == (free_gain is None)
    assert [r.card_name for r in restored.free_gain_priority or []] == [r.card_name for r in free_gain or []]
    assert restored.captain_target_priority == []
    assert [r.card_name for r in restored.band_of_misfits_target_priority] == ["Militia"]
