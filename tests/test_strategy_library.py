from pathlib import Path

import pytest

from dominion.analysis.strategy_library import (
    find_compatible_strategies,
    referenced_cards,
    score_strategy_for_board,
)
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _strategy(*cards: str) -> EnhancedStrategy:
    strategy = EnhancedStrategy()
    strategy.name = "test"
    strategy.gain_priority = [PriorityRule(card) for card in cards]
    strategy.action_priority = []
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    strategy.trash_priority = []
    return strategy


def test_referenced_cards_ignores_list_boundaries():
    strategy = _strategy("Village", "Smithy")
    strategy.action_priority = [PriorityRule("Festival")]
    strategy.trash_priority = [PriorityRule("Estate")]
    strategy.bounty_hunter_exile_priority = [PriorityRule("Market")]

    assert referenced_cards(strategy) == frozenset(
        {
            "Village",
            "Smithy",
            "Festival",
            "Estate",
            "Market",
            "Gold",
            "Silver",
            "Copper",
        }
    )


def test_score_strategy_for_board_rewards_non_base_overlap():
    strategy = _strategy("Province", "Gold", "Village", "Smithy", "Festival", "Laboratory")

    score, core, matched, missing = score_strategy_for_board(
        strategy,
        ["Village", "Smithy", "Festival", "Workshop"],
    )

    assert core == frozenset({"Village", "Smithy", "Festival", "Laboratory"})
    assert matched == frozenset({"Village", "Smithy", "Festival"})
    assert missing == frozenset({"Laboratory"})
    assert score > 0


@pytest.mark.parametrize("priorities", [None, []])
def test_free_gain_inheritance_or_empty_rules_add_no_references(priorities):
    strategy = _strategy("Village", "Workshop")
    before = referenced_cards(strategy)
    strategy.free_gain_priority = priorities
    assert referenced_cards(strategy) == before


def test_free_gain_only_target_changes_compatibility_and_seed_ranking(monkeypatch):
    from dominion.analysis import strategy_library

    plain = _strategy("Village", "Workshop")
    plain.name = "plain"
    gardens = _strategy("Village", "Workshop")
    gardens.name = "free-gain Gardens"
    gardens.free_gain_priority = [PriorityRule("Gardens"), PriorityRule("Silver")]
    monkeypatch.setattr(strategy_library, "_iter_strategy_factories", lambda locations: [
        ("plain:create", lambda: plain), ("gardens:create", lambda: gardens),
    ])

    without_target = find_compatible_strategies(["Village", "Workshop"], locations=[])
    assert [entry.name for entry in without_target] == ["plain", "free-gain Gardens"]
    assert without_target[1].missing_cards == frozenset({"Gardens"})
    assert "Gardens" in without_target[1].referenced_cards
    assert "Silver" not in without_target[1].core_cards
    with_target = find_compatible_strategies(["Village", "Workshop", "Gardens"], locations=[])
    assert with_target[0].name == "free-gain Gardens"
    assert with_target[0].missing_cards == frozenset()
    assert with_target[0].matched_cards == frozenset({"Village", "Workshop", "Gardens"})


def test_strategy_with_only_free_gain_target_requires_that_target_for_discovery(monkeypatch):
    from dominion.analysis import strategy_library
    strategy = _strategy("Silver")
    strategy.free_gain_priority = [PriorityRule("Gardens")]
    monkeypatch.setattr(strategy_library, "_iter_strategy_factories", lambda locations: [("gardens:create", lambda: strategy)])
    assert find_compatible_strategies(["Village"], min_overlap=1, locations=[]) == []
    entries = find_compatible_strategies(["Gardens"], min_overlap=1, locations=[])
    assert len(entries) == 1 and entries[0].core_cards == frozenset({"Gardens"})


def test_find_compatible_strategies_ranks_existing_modules(tmp_path, monkeypatch):
    package = tmp_path / "tmp_strats"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "engine.py").write_text(
        """
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Engine(EnhancedStrategy):
    def __init__(self):
        super().__init__()
        self.name = "Engine"
        self.gain_priority = [
            PriorityRule("Village"),
            PriorityRule("Smithy"),
            PriorityRule("Festival"),
            PriorityRule("Workshop"),
            PriorityRule("Province"),
        ]


def create_engine() -> EnhancedStrategy:
    return Engine()
""",
        encoding="utf-8",
    )
    (package / "single.py").write_text(
        """
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Single(EnhancedStrategy):
    def __init__(self):
        super().__init__()
        self.name = "Single"
        self.gain_priority = [PriorityRule("Village"), PriorityRule("Province")]


def create_single() -> EnhancedStrategy:
    return Single()
""",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    entries = find_compatible_strategies(
        ["Village", "Smithy", "Festival", "Workshop", "Market"],
        top_k=5,
        min_overlap=2,
        locations=[(Path(package), "tmp_strats")],
    )

    assert [entry.name for entry in entries] == ["Engine"]
    assert entries[0].spec == "tmp_strats.engine:create_engine"
    assert entries[0].matched_cards == frozenset(
        {"Village", "Smithy", "Festival", "Workshop"}
    )
