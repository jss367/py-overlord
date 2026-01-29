import random

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.simulation.strategy_battle import StrategyBattle

BOARDS = [
    "boards/wealthy_cities.txt",
    "boards/iron_barbarian.txt",
    "boards/bazaar_council.txt",
]


@pytest.mark.slow
@pytest.mark.parametrize("seed_rng", [24680], indirect=True)
@pytest.mark.parametrize("board_path", BOARDS)
def test_curated_boards_finish_reasonably(seed_rng, board_path):
    cfg = load_board(board_path)
    battle = StrategyBattle(board_config=cfg)
    s1 = battle.strategy_loader.get_strategy("Big Money")
    s2 = battle.strategy_loader.get_strategy("Big Money Smithy")

    assert s1 is not None
    assert s2 is not None

    for i in range(3):
        random.seed(seed_rng + i)
        ai1, ai2 = GeneticAI(s1), GeneticAI(s2)
        _winner, scores, _log, turns = battle.run_game(ai1, ai2, cfg.kingdom_cards)
        assert 6 <= turns <= 120
        assert isinstance(scores, dict)
