"""Compare shared storage/discard defaults with fixed seeds and both seats.

Both arms use the same corrected card rules. Only the AI defaults change.
This is a diagnostic policy study, not a strategy search or tournament refresh.
"""
import argparse
from functools import cache
import json
import math
import random
import statistics
from pathlib import Path

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader


class PreviousDefaultsAI(GeneticAI):
    """Pre-change storage/discard defaults; generic discard overrides retained."""

    def choose_gear_set_aside(self, state, player, choices):
        actions = [c for c in choices if c.is_action]
        if len(actions) >= 2 and player.actions <= 0:
            return actions[:2]
        return choices[:2]

    def choose_card_to_set_aside_for_haven(self, state, player, choices):
        actions = [c for c in choices if c.is_action]
        if actions:
            return max(actions, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        treasures = [c for c in choices if c.is_treasure and c.name != "Copper"]
        if treasures:
            return max(treasures, key=lambda c: (c.cost.coins, c.name))
        return None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        hook = getattr(self.strategy, "choose_cards_to_discard", None)
        if hook is not None:
            return hook(state, player, choices, count, reason=reason)

        def key(card):
            if card.name == "Curse":
                return (0, 0, card.name)
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return (1, card.cost.coins, card.name)
            if card.name == "Copper":
                return (2, 0, card.name)
            return (3, card.cost.coins, card.name)

        return sorted(choices, key=key)[:max(0, min(count, len(choices)))]


KINGDOM = ("Gear", "Haven", "Chapel", "Junk Dealer", "Anvil", "Village",
           "Smithy", "Laboratory", "Militia", "Market")


@cache
def loader():
    return StrategyLoader()


def candidate(kind):
    if kind.startswith("Registered "):
        return loader().get_strategy(kind.removeprefix("Registered "))
    strategy = EnhancedStrategy()
    strategy.name = kind
    targets = {
        "Smithy money": [("Smithy", 2)],
        "Militia money": [("Militia", 1)],
        "Gear money": [("Gear", 2)],
        "Haven money": [("Haven", 2)],
        "Supported storage engine": [("Junk Dealer", 1), ("Village", 3), ("Laboratory", 4),
                                     ("Gear", 2), ("Haven", 2), ("Smithy", 2)],
        "Trashing and discard money": [("Chapel", 1), ("Junk Dealer", 1), ("Anvil", 2)],
    }[kind]
    strategy.gain_priority = [PriorityRule("Province")]
    strategy.gain_priority += [PriorityRule(name, PriorityRule.max_in_deck(name, limit))
                              for name, limit in targets]
    strategy.gain_priority += [PriorityRule("Gold"), PriorityRule("Silver"),
                              PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
                              PriorityRule("Estate", PriorityRule.provinces_left("<=", 1))]
    strategy.action_priority = [PriorityRule(name) for name in
                               ("Village", "Haven", "Junk Dealer", "Laboratory", "Chapel", "Gear", "Smithy", "Militia")]
    strategy.trash_priority = [PriorityRule("Curse"), PriorityRule("Estate"), PriorityRule(
        "Copper", lambda s, p: sum(c.stats.coins for c in p.all_cards() if c.is_treasure) > 3,
    )]
    return strategy


def game(kind, opponent, seed, seat, old):
    loader()  # Discover factories once, before resetting the per-game RNG.
    random.seed(seed)
    subject = (PreviousDefaultsAI if old else GeneticAI)(candidate(kind))
    rival = GeneticAI(loader().get_strategy(opponent) if opponent == "Big Money" else candidate(opponent))
    ais = [subject, rival] if seat == 0 else [rival, subject]
    state = GameState([], supply={})
    state.log_callback = lambda *args: None
    state.initialize_game(ais, [get_card(name) for name in KINGDOM])
    while not state.is_game_over():
        state.play_turn()
    ours = state.players[seat]
    theirs = state.players[1 - seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (ours, theirs)]
    result = 1.0 if ranks[0] > ranks[1] else 0.0 if ranks[0] < ranks[1] else 0.5
    return result, ranks[0][0] - ranks[1][0], not state._normal_game_end_reached()


def evaluate(pairs, seed):
    rows = []
    for kind in ("Gear money", "Haven money", "Supported storage engine",
                 "Trashing and discard money", "Registered Big Money", "Registered Chapel Witch"):
        for opponent in ("Big Money", "Smithy money", "Militia money"):
            scores = {"previous": [], "current": []}
            margins = {"previous": [], "current": []}
            differences = []
            turn_limits = {"previous": 0, "current": 0}
            for offset in range(pairs):
                paired = {}
                for label, old in (("previous", True), ("current", False)):
                    results = [game(kind, opponent, seed + offset, seat, old) for seat in (0, 1)]
                    scores[label].extend(r[0] for r in results)
                    margins[label].extend(r[1] for r in results)
                    turn_limits[label] += sum(r[2] for r in results)
                    paired[label] = statistics.mean(r[0] for r in results)
                differences.append(paired["current"] - paired["previous"])
            delta = statistics.mean(differences)
            se = statistics.stdev(differences) / math.sqrt(pairs) if pairs > 1 else 0
            row = {"candidate": kind, "opponent": opponent, "games_per_policy": pairs * 2,
                   "previous_win_share": statistics.mean(scores["previous"]),
                   "current_win_share": statistics.mean(scores["current"]),
                   "difference": delta, "paired_95_interval": [delta - 1.96 * se, delta + 1.96 * se],
                   "turn_limit_games": turn_limits,
                   "previous_score_margin": statistics.mean(margins["previous"]),
                   "current_score_margin": statistics.mean(margins["current"])}
            rows.append(row)
            print(json.dumps(row), flush=True)
    return {"seed_start": seed, "seed_pairs": pairs, "kingdom": KINGDOM,
            "games": pairs * 2 * 2 * len(rows), "comparisons": rows,
            "interval": "Normal approximation, paired seed blocks; each block averages both seats; ties count half."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=392000)
    parser.add_argument("--output", type=Path, default=Path(".context/set-aside-comparison.json"))
    args = parser.parse_args()
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    result = evaluate(args.pairs, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
