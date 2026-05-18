from pathlib import Path

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

    assert referenced_cards(strategy) == frozenset(
        {"Village", "Smithy", "Festival", "Estate", "Gold", "Silver", "Copper"}
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
