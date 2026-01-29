import random

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.simulation.strategy_battle import DEFAULT_KINGDOM_CARDS, StrategyBattle


@pytest.mark.parametrize("seed_rng", [777], indirect=True)
def test_reproducible_small_run(seed_rng):
    battle = StrategyBattle()
    s1 = battle.strategy_loader.get_strategy("Big Money")
    s2 = battle.strategy_loader.get_strategy("Big Money Smithy")

    assert s1 is not None
    assert s2 is not None

    kingdom = DEFAULT_KINGDOM_CARDS

    def tally():
        wins = 0
        for i in range(10):
            random.seed(seed_rng + i)
            ai1, ai2 = GeneticAI(s1), GeneticAI(s2)
            winner, *_ = battle.run_game(ai1, ai2, kingdom)
            wins += int(winner == ai1)
        return wins

    assert tally() == tally()
