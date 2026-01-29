import random

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.simulation.strategy_battle import DEFAULT_KINGDOM_CARDS, StrategyBattle


@pytest.mark.slow
@pytest.mark.parametrize("seed_rng", [12345], indirect=True)
@pytest.mark.parametrize(
    "pair",
    [
        ("Big Money", "Big Money Smithy"),
        ("Big Money", "Torturer Engine"),
    ],
)
def test_seeded_battle_winrates_and_reproducibility(seed_rng, pair):
    games = 200
    base_seed = seed_rng
    battle = StrategyBattle()
    s1 = battle.strategy_loader.get_strategy(pair[0])
    s2 = battle.strategy_loader.get_strategy(pair[1])

    assert s1 is not None, f"Strategy not found: {pair[0]}"
    assert s2 is not None, f"Strategy not found: {pair[1]}"

    kingdom = DEFAULT_KINGDOM_CARDS

    def run_once():
        wins1 = 0
        for i in range(games):
            random.seed(base_seed + i)
            ai1, ai2 = GeneticAI(s1), GeneticAI(s2)
            if i % 2 == 0:
                winner, *_ = battle.run_game(ai1, ai2, kingdom)
                wins1 += int(winner == ai1)
            else:
                winner, *_ = battle.run_game(ai2, ai1, kingdom)
                wins1 += int(winner == ai1)
        return wins1

    first = run_once()
    second = run_once()
    assert first == second

    winrate = first / games
    if pair == ("Big Money", "Big Money Smithy"):
        assert winrate < 0.5
