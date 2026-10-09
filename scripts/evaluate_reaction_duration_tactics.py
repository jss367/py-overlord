"""Evaluate Barge, Sleigh and Torturer defaults with paired seeds and both seats.

Both arms use corrected card rules and identical purchase/play priorities.
Only the subject's three tactical defaults differ; opponents use current ones.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import random
from statistics import mean

from dominion.ai.genetic_ai import GeneticAI
from dominion.ai.tactical_defaults import discard_priority, torturer_should_discard_preserving_buy
from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.ways.registry import get_way
from scripts.evaluate_free_gain_tactics import interval, rate_interval

TURN_LIMIT = 150
KINGDOM = ["Barge", "Sleigh", "Torturer", "Village", "Workshop", "Smithy",
           "Militia", "Chapel", "Market", "Watchtower"]


class MeasuredAI(GeneticAI):
    def __init__(self, strategy):
        super().__init__(strategy)
        self.decisions = Counter()

    def should_resolve_barge_now(self, state, player):
        answer = self.barge(state, player)
        self.decisions["barge_now" if answer else "barge_next_turn"] += 1
        return answer

    def barge(self, state, player):
        return super().should_resolve_barge_now(state, player)

    def choose_sleigh_reaction(self, state, player, card):
        answer = self.sleigh(state, player, card)
        self.decisions[f"sleigh_{answer or 'decline'}"] += 1
        return answer

    def sleigh(self, state, player, card):
        return super().choose_sleigh_reaction(state, player, card)

    def choose_torturer_attack(self, state, player):
        answer = self.torturer(state, player)
        self.decisions["torturer_discard" if answer else "torturer_curse"] += 1
        return answer

    def torturer(self, state, player):
        return super().choose_torturer_attack(state, player)


class PurchasePreservingAI(MeasuredAI):
    def torturer(self, state, player):
        hook = getattr(self.strategy, "choose_torturer_response", None)
        return hook(state, player) if hook else torturer_should_discard_preserving_buy(state, player)


class PreviousDefaultsAI(MeasuredAI):
    """Pre-change policies on the same corrected engine, honoring old hooks."""

    def barge(self, state, player):
        return True

    def sleigh(self, state, player, card):
        return "hand" if card.is_action or card.is_treasure else None

    def torturer(self, state, player):
        hook = getattr(self.strategy, "choose_torturer_response", None)
        if hook is not None:
            return hook(state, player)
        return sum(c.name in {"Curse", "Copper"} or (
            c.is_victory and not c.is_action and c.cost.coins <= 2
        ) for c in player.hand) >= 2

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        hook = getattr(self.strategy, "choose_cards_to_discard", None)
        if hook is not None:
            return hook(state, player, choices, count, reason=reason)
        return sorted(choices, key=discard_priority)[:max(0, count)]


def candidate(kind):
    strategy = EnhancedStrategy()
    strategy.name = kind
    targets = {
        "Barge money": [("Barge", 2)],
        "Sleigh and Workshop": [("Sleigh", 2), ("Workshop", 1), ("Village", 2), ("Smithy", 2)],
        "Torturer money": [("Torturer", 2)],
        "Barge and Torturer engine": [("Village", 3), ("Torturer", 3), ("Barge", 2), ("Sleigh", 1)],
        "Torturer opponent": [("Torturer", 2)],
    }[kind]
    strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
    strategy.gain_priority += [PriorityRule(n, PriorityRule.max_in_deck(n, count)) for n, count in targets]
    strategy.gain_priority += [PriorityRule("Silver"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 1))]
    strategy.action_priority = [PriorityRule(n) for n in
                               ("Village", "Market", "Sleigh", "Workshop", "Barge", "Torturer", "Smithy")]
    return strategy


def evaluate(task):
    spec, pairs, seed = task
    loader = StrategyLoader()  # Factory discovery precedes resetting the RNG.
    board = load_board(spec["board"]) if spec.get("board") else BoardConfig(KINGDOM)
    records = []
    counts = [Counter(), Counter()]
    truncated = [0, 0]
    for offset in range(pairs):
        record = []
        for policy in range(2):
            seats = []
            for seat in range(2):
                strategy = loader.get_strategy(spec["strategy"]) if spec.get("strategy") else candidate(spec["candidate"])
                rival = (candidate("Torturer opponent") if spec["opponent"] == "Torturer opponent"
                         else loader.get_strategy(spec["opponent"]))
                random.seed(seed + offset)
                current_ai = PurchasePreservingAI if spec.get("preserve_buy") else MeasuredAI
                subject = (current_ai if policy else PreviousDefaultsAI)(strategy)
                opponent = (PurchasePreservingAI if spec.get("preserve_buy") else GeneticAI)(rival)
                ais = [subject, opponent] if seat == 0 else [opponent, subject]
                state = GameState([])
                state.log_callback = lambda *_: None
                state.initialize_game(ais, [get_card(n) for n in board.kingdom_cards],
                    events=[get_event(n) for n in board.events], ways=[get_way(n) for n in board.ways])
                while not state.is_game_over() and state.turn_number < TURN_LIMIT:
                    state.play_turn()
                ours, theirs = state.players[seat], state.players[1 - seat]
                ranks = [(p.get_victory_points(), -p.turns_taken) for p in (ours, theirs)]
                score = 1 if ranks[0] > ranks[1] else .5 if ranks[0] == ranks[1] else 0
                limited = not state._normal_game_end_reached()
                seats.append({"win_share": score, "score_margin": ranks[0][0] - ranks[1][0],
                              "turn_limit": limited})
                counts[policy].update(subject.decisions)
                truncated[policy] += limited
            record.append(seats)
        records.append(record)
    previous, current = [[mean(s["win_share"] for s in r[policy]) for r in records] for policy in range(2)]
    deltas = [b - a for a, b in zip(previous, current)]
    margins = [[mean(s["score_margin"] for s in r[policy]) for r in records] for policy in range(2)]
    margin_deltas = [b - a for a, b in zip(*margins)]
    return {**spec, "seed_start": seed, "seed_pairs": pairs, "games_per_policy": pairs * 2,
            "kingdom": board.kingdom_cards, "events": board.events, "ways": board.ways,
            "previous_win_share": mean(previous), "current_win_share": mean(current),
            "previous_95_interval": rate_interval(previous), "current_95_interval": rate_interval(current),
            "difference": mean(deltas), "paired_95_interval": interval(deltas),
            "score_margins": [mean(v) for v in margins],
            "score_margin_difference": mean(margin_deltas), "score_margin_95_interval": interval(margin_deltas),
            "turn_limit_games": truncated, "decision_counts": [dict(c) for c in counts],
            "per_seed_outcomes": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=393000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(".context/reaction-duration-evaluation.json"))
    parser.add_argument("--preserve-buy", action="store_true", help="Reproduce the exploratory response study, including its opponent defaults")
    args = parser.parse_args()
    if args.pairs < 2 or args.workers < 1:
        parser.error("Require at least two seed pairs and one worker")
    if args.output.exists():
        parser.error("Choose a new output path to preserve earlier evidence")
    fingerprint = tournament_fingerprint()
    tasks = []
    for kind in ("Barge money", "Sleigh and Workshop", "Torturer money", "Barge and Torturer engine"):
        for opponent in ("big_money", "big_money_smithy", "Torturer opponent"):
            tasks.append(({"candidate": kind, "opponent": opponent}, args.pairs, args.seed))
    for strategy in ("black_cat_and_livery_board_ox_engine", "black_cat_and_livery_board_fisherman_infirmary",
                     "black_cat_and_livery_board_cavalry_horses", "collection_swindler_rush",
                     "selective_envoy_collection", "village_envoy_collection_engine"):
        board = "boards/black_cat_and_livery.txt" if strategy.startswith("black_cat") else "boards/collection_imperial_envoy.txt"
        for opponent in ("big_money", "big_money_smithy"):
            tasks.append(({"strategy": strategy, "board": board, "opponent": opponent}, args.pairs, args.seed + 10000))
    if args.preserve_buy:
        tasks = [({**spec, "preserve_buy": True}, pairs, seed) for spec, pairs, seed in tasks]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(evaluate, tasks):
            results.append(result)
            print(json.dumps({k: v for k, v in result.items() if k != "per_seed_outcomes"}), flush=True)
    if tournament_fingerprint() != fingerprint:
        raise RuntimeError("Simulation sources changed during evaluation; rerun")
    result = {"seed_start": args.seed, "seed_pairs": args.pairs,
              "games": len(results) * args.pairs * 4, "turn_limit": TURN_LIMIT,
              "source_fingerprint": fingerprint,
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python_version": platform.python_version(),
              "common_rules": "Corrected Barge replay queues, Torturer choices/ordering/discards, gain destinations and Sleigh tracking in both arms; current opponent policies.",
              "uncertainty": "95% approximate Wilson seed-block rate intervals; paired normal intervals for changes; both seats averaged within a seed; exploratory, no multiple-comparison adjustment.",
              "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
