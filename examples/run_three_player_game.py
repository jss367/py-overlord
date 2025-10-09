import argparse

from dominion.strategy.strategy_loader import StrategyLoader
from dominion.simulation.game_logger import GameLogger
from dominion.ai.genetic_ai import GeneticAI
from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.simulation.strategy_battle import DEFAULT_KINGDOM_CARDS


def run_game(strat_names):
    loader = StrategyLoader()
    strategies = []
    for name in strat_names:
        strat = loader.get_strategy(name)
        if not strat:
            raise ValueError(f"Strategy not found: {name}")
        strategies.append(strat)

    ais = [GeneticAI(s) for s in strategies]
    logger = GameLogger(log_folder="battle_logs", log_frequency=1)
    logger.start_game(ais)

    state = GameState(players=[], supply={})
    state.set_logger(logger)
    kingdom = [get_card(n) for n in DEFAULT_KINGDOM_CARDS]
    state.initialize_game(ais, kingdom)

    while not state.is_game_over():
        state.play_turn()

    scores = {p.ai.name: p.get_victory_points() for p in state.players}
    winner = max(state.players, key=lambda p: p.get_victory_points()).ai
    log_path = logger.end_game(winner.name, scores, state.supply, state.players)
    print("Winner:", winner.name)
    print("Log file:", log_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("strategies", nargs=3, help="Three strategy names")
    args = parser.parse_args()
    run_game(args.strategies)
