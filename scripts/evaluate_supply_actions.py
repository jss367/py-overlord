"""Reproduce the supply-target comparison; keep purchases and opponents fixed.

Legacy policies reproduce the old decisions on the current rules engine. This
isolates target policy changes, not cost/menu changes or full rules fidelity.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

from dominion.ai.genetic_ai import GeneticAI
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategies.big_money_smithy import create_big_money_smithy
from dominion.strategy.strategies.chapel_witch import create_chapel_witch
from dominion.strategy.strategies.village_smithy_lab import create_village_smithy_lab


COMMANDS = ("Captain", "Band of Misfits", "Overlord")
OPPONENTS = {
    "Smithy money": create_big_money_smithy,
    "Village and Laboratory engine": create_village_smithy_lab,
    "Chapel and Witch attack": create_chapel_witch,
}


def legacy_resources(player, choices):
    needs_actions = sum(c.is_action and c.stats.actions == 0 for c in player.hand) > player.actions
    return max(choices, key=lambda c: (
        needs_actions and c.stats.actions >= 2,
        c.stats.cards * 2 + c.stats.coins,
        c.stats.actions, c.stats.buys, c.cost.coins, c.name,
    ), default=None)


class ProbeStrategy(EnhancedStrategy):
    """Identical purchases and hand order across the two target policies."""

    def __init__(self, command, legacy):
        super().__init__()
        self.name = f"{command}: {'legacy' if legacy else 'shared'} supply targets"
        self.command = command
        self.legacy = legacy
        self.targets = Counter()
        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule(command, PriorityRule.max_in_deck(command, 2)),
            PriorityRule("Gold"),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        # Supply payloads intentionally have no hand rule, so Overlord reaches
        # its baseline. Unexpected bought Smithy still uses normal hand fallback.
        self.action_priority = [PriorityRule(command)]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", lambda _s, p: sum(
                c.stats.coins for c in p.all_cards() if c.is_treasure and c.name != "Copper"
            ) >= 3),
        ]

    def _target(self, state, player, choices, kind):
        if self.legacy:
            if kind == "captain":
                choice = self.choose_action(state, player, choices + [None])
                choice = choice or next(iter(choices), None)
            elif kind == "band_of_misfits":
                choice = max(choices, key=lambda c: (
                    c.stats.cards * 2 + c.stats.actions + c.cost.coins, c.name
                ), default=None)
            else:
                choice = self.choose_action(state, player, choices + [None]) or legacy_resources(player, choices)
        else:
            choice = getattr(super(), f"choose_{kind}_target")(state, player, choices)
        if choice:
            self.targets[choice.name] += 1
        return choice

    def choose_captain_target(self, state, player, choices):
        return self._target(state, player, choices, "captain")

    def choose_band_of_misfits_target(self, state, player, choices):
        return self._target(state, player, choices, "band_of_misfits")

    def choose_overlord_target(self, state, player, choices):
        return self._target(state, player, choices, "overlord")


def evaluate(pairs, seed):
    fingerprint = tournament_fingerprint()
    runner_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows = []
    for command_index, command in enumerate(COMMANDS):
        # Keep the original non-Duration panel for policy comparability.
        # Duration scheduling/ownership is covered separately by rules tests;
        # this study does not establish the strength of Duration selections.
        kingdom = ["Chapel", "Village", "Smithy", "Militia", "Witch",
                   "Laboratory", "Market", "Festival", "Moat", command]
        battle = StrategyBattle(kingdom_cards=kingdom, log_frequency=0)
        try:
            for opponent_index, (opponent_name, factory) in enumerate(OPPONENTS.items()):
                seed_start = seed + command_index * 100_000 + opponent_index * 10_000
                results = {label: {"wins": 0, "games": 0, "targets": Counter(), "seat_wins": [0, 0]}
                           for label in ("legacy", "shared")}
                pair_deltas = []
                for pair in range(pairs):
                    seat_deltas = []
                    for seat in (0, 1):
                        outcomes = {}
                        for label in results:
                            strategy = ProbeStrategy(command, legacy=label == "legacy")
                            probe, opponent = GeneticAI(strategy), GeneticAI(factory())
                            ais = [probe, opponent] if seat == 0 else [opponent, probe]
                            random.seed(seed_start + pair)
                            winner, _, _, _ = battle.run_game(*ais, kingdom)
                            won = int(winner is probe)
                            outcomes[label] = won
                            result = results[label]
                            result["wins"] += won
                            result["games"] += 1
                            result["seat_wins"][seat] += won
                            result["targets"].update(strategy.targets)
                        seat_deltas.append(outcomes["shared"] - outcomes["legacy"])
                    pair_deltas.append(statistics.mean(seat_deltas))
                delta = statistics.mean(pair_deltas)
                # Cluster both seat swaps of each seed; outcomes are correlated.
                # Hoeffding's bound for independent seed-pair means in [-1, 1].
                # Conservative, including when no discordant outcomes occur.
                half_width = math.sqrt(2 * math.log(40) / pairs)
                row = {"command": command, "opponent": opponent_name, "kingdom": kingdom,
                       "seed_start": seed_start, "seed_pairs": pairs, "policies": results,
                       "win_rate_delta": delta,
                       "paired_95_percent_hoeffding_interval": [max(-1, delta - half_width), min(1, delta + half_width)],
                       "paired_seed_deltas": pair_deltas}
                rows.append(row)
                print(f"{command} / {opponent_name}: "
                      f"{results['legacy']['wins']}/{2 * pairs} -> {results['shared']['wins']}/{2 * pairs}", flush=True)
        finally:
            battle.close()
    if tournament_fingerprint() != fingerprint:
        raise RuntimeError("Simulation inputs changed during evaluation")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != runner_hash:
        raise RuntimeError("Evaluation runner changed during evaluation")
    return {"simulation_fingerprint": fingerprint,
            "runner_sha256": runner_hash,
            "python_version": sys.version, "seed": seed, "seed_pairs_per_row": pairs,
            "total_games": len(rows) * pairs * 4, "comparisons": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=39000)
    parser.add_argument("--output", type=Path, default=Path("scripts/data/supply_action_evaluation.json"))
    args = parser.parse_args()
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    results = evaluate(args.pairs, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
