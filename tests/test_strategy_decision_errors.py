"""Broken rules invalidate evaluations instead of quietly changing the policy."""

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    StrategyDecisionError,
    WayRule,
)
from dominion.ways.registry import get_way


def _broken(*args):
    raise ValueError("missing strategy parameter")


def _state(strategy):
    player = PlayerState(GeneticAI(strategy))
    return GameState([player]), player


@pytest.mark.parametrize(
    "kind, card_name",
    [
        ("gain", "Province"),
        ("action", "Village"),
        ("treasure", "Gold"),
        ("trash", "Estate"),
    ],
)
def test_broken_priority_condition_keeps_context_and_original_cause(kind, card_name):
    strategy = EnhancedStrategy()
    strategy.name = "Broken policy"
    setattr(strategy, f"{kind}_priority", [PriorityRule(card_name, _broken)])
    state, player = _state(strategy)
    with pytest.raises(
        StrategyDecisionError, match=f"Broken policy.*{kind}.*{card_name}"
    ) as error:
        getattr(strategy, f"choose_{kind}")(state, player, [get_card(card_name)])
    assert isinstance(error.value.__cause__, ValueError)
    assert str(error.value.__cause__) == "missing strategy parameter"


def test_false_condition_still_allows_next_rule():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [
        PriorityRule("Province", lambda *_: False),
        PriorityRule("Gold"),
    ]
    state, player = _state(strategy)
    assert (
        strategy.choose_gain(
            state, player, [get_card("Province"), get_card("Gold")]
        ).name
        == "Gold"
    )


def test_broken_way_condition_is_an_error():
    strategy = EnhancedStrategy()
    strategy.way_policy = [WayRule("Village", "Way of the Otter", _broken)]
    state, player = _state(strategy)
    with pytest.raises(StrategyDecisionError, match="Way.*Village.*Way of the Otter"):
        strategy.choose_way(
            state, player, get_card("Village"), [get_way("Way of the Otter")]
        )


def test_broken_decision_observer_cannot_produce_incomplete_statistics():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Province")]
    strategy._decision_trace_callback = _broken
    state, player = _state(strategy)
    with pytest.raises(StrategyDecisionError, match="observer.*Province"):
        strategy.choose_gain(state, player, [get_card("Province")])


@pytest.mark.parametrize("workers", [1, 2])
def test_trainer_rejects_broken_policy_and_preserves_other_evaluations(
    tmp_path, workers
):
    broken = EnhancedStrategy()
    broken.name = "Broken policy"
    broken.gain_priority = [PriorityRule("Copper", _broken)]
    valid = EnhancedStrategy()
    valid.name = "Valid policy"
    valid.gain_priority = [
        PriorityRule("Province"),
        PriorityRule("Gold"),
        PriorityRule("Silver"),
    ]
    trainer = GeneticTrainer(
        population_size=2,
        generations=1,
        games_per_eval=2,
        kingdom_cards=["Village", "Smithy"],
        workers=workers,
        log_folder=str(tmp_path / "logs"),
    )
    try:
        fitness = trainer.evaluate_population([broken, valid])
    finally:
        trainer.close()
    assert fitness[0] == float("-inf")
    assert fitness[1] != float("-inf")
