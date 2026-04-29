"""Evolve a strategy for the Wizards/Lich kingdom and battle it against the
hand-written WizardsLichEngine and Big Money."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import coloredlogs

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.strategy.strategies.wizards_lich_engine import (
    create_wizards_lich_engine,
)
from runner import save_strategy_as_python


logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=logger)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", default="boards/wizards_lich.txt")
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--games-per-eval", type=int, default=40)
    parser.add_argument("--mutation-rate", type=float, default=0.18)
    parser.add_argument("--validation-games", type=int, default=120)
    parser.add_argument("--output-dir", type=Path, default=Path("generated_strategies"))
    args = parser.parse_args()

    cfg = load_board(args.board)
    board_name = Path(args.board).stem

    loader = StrategyLoader()
    big_money = loader.get_strategy("Big Money")
    big_money_smithy = loader.get_strategy("Big Money Smithy")

    seed = create_wizards_lich_engine()

    panel = [seed, big_money, big_money_smithy]
    logger.info("Fitness panel: %s", ", ".join(p.name for p in panel))

    trainer = GeneticTrainer(
        kingdom_cards=cfg.kingdom_cards,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        games_per_eval=args.games_per_eval,
        board_config=cfg,
    )
    trainer.inject_strategy(seed)
    trainer.set_baseline_panel(panel)

    best, metrics = trainer.train()
    if best is None:
        logger.error("No best strategy evolved")
        return

    logger.info("Best evolved fitness: %.1f%%", metrics.get("win_rate", 0.0))
    logger.info("Panel breakdown: %s", trainer.last_eval_breakdown)

    args.output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = args.output_dir / f"{board_name}_evolved_{timestamp}.py"
    save_strategy_as_python(best, out_file, "WizardsLichEvolved")
    logger.info("Saved evolved strategy to %s", out_file)

    # Validation: head-to-head vs hand-written and BM
    battle = StrategyBattle(kingdom_cards=cfg.kingdom_cards, board_config=cfg, log_frequency=0)

    def head_to_head(opp_factory, name: str) -> None:
        wins = 0
        for i in range(args.validation_games):
            ai1 = GeneticAI(best)
            ai2 = GeneticAI(opp_factory())
            if i % 2 == 0:
                winner, _, _, _ = battle.run_game(ai1, ai2, cfg.kingdom_cards)
            else:
                winner, _, _, _ = battle.run_game(ai2, ai1, cfg.kingdom_cards)
            if winner == ai1:
                wins += 1
        rate = wins / args.validation_games * 100
        logger.info("Evolved vs %s: %d/%d (%.1f%%)", name, wins, args.validation_games, rate)

    head_to_head(create_wizards_lich_engine, "WizardsLichEngine (hand-written)")
    head_to_head(lambda: loader.get_strategy("Big Money"), "Big Money")
    head_to_head(lambda: loader.get_strategy("Big Money Smithy"), "Big Money Smithy")


if __name__ == "__main__":
    main()
