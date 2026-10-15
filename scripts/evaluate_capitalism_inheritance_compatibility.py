"""Measure fixed named policies on deliberately preconfigured type modifiers.

Run the identical runner in each engine checkout. This is a compatibility panel,
not a purchase recommendation, search, or replacement for historical standings.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.projects.capitalism import Capitalism
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import PriorityRule
from scripts.evaluate_named_card_decisions import candidate, opponent, OPPONENTS

SUBJECTS = ("Courtier", "Stables", "Spice Merchant", "Counterfeit", "Moneylender", "Minion")
KINGDOM = ("Courtier", "Stables", "Spice Merchant", "Counterfeit", "Moneylender", "Minion", "Smithy", "Village", "Merchant", "Militia")
MODIFIERS = ("Capitalism", "Capitalism and Inheritance (Merchant)")
TURN_LIMIT = 150


def hashes():
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path, (
        "scripts/evaluate_capitalism_inheritance_compatibility.py",
        "scripts/evaluate_named_card_decisions.py", "scripts/evaluate_card_tactics.py"))}


def run_game(subject, modifier, rival, seed, seat):
    random.seed(seed)
    decisions = Counter()
    ours = GeneticAI(candidate(subject, "default", decisions))
    theirs = GeneticAI(opponent(subject, rival))
    choose_action = ours.choose_action
    def observe_estates(state, choices):
        chosen = choose_action(state, choices)
        if getattr(chosen, "name", None) == "Estate":
            decisions["choose_action: Estate"] += 1
        return chosen
    ours.choose_action = observe_estates
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ours, theirs] if seat == 0 else [theirs, ours], [get_card(n) for n in KINGDOM])
    # Both players receive the same declared modifier before turn one. No
    # purchase-policy comparison or inference about when to buy it is made.
    for player in state.players:
        player.projects.append(Capitalism())
        if "Inheritance" in modifier:
            player.ai.strategy.action_priority.insert(0, PriorityRule("Estate"))
            player.ai.strategy.trash_priority = [r for r in player.ai.strategy.trash_priority if r.card != "Estate"]
            original = player.ai.choose_card_to_inherit
            player.ai.choose_card_to_inherit = lambda *_: get_card("Merchant")
            try:
                get_event("Inheritance").on_buy(state, player)
            finally:
                player.ai.choose_card_to_inherit = original
    while not state.is_game_over() and state.turn_number < TURN_LIMIT:
        state.play_turn()
    us, them = state.players[seat], state.players[1 - seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (us, them)]
    return {"seed": seed, "seat": seat,
            "win_share": 1 if ranks[0] > ranks[1] else 0 if ranks[0] < ranks[1] else .5,
            "score_margin": ranks[0][0] - ranks[1][0],
            "scores": [r[0] for r in ranks], "turns_taken": [us.turns_taken, them.turns_taken],
            "truncated": not state._normal_game_end_reached(), "decisions": dict(decisions)}


def evaluate(task):
    subject, modifier, rival, pairs, start = task
    records = [run_game(subject, modifier, rival, start + offset, seat)
               for offset in range(pairs) for seat in (0, 1)]
    return {"subject": subject, "modifier": modifier, "opponent": rival, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=10)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--engine-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.pairs < 2 or args.workers < 1 or args.seed < 0:
        parser.error("Use a fresh output, at least two pairs, positive workers and a nonnegative seed")
    fingerprint, runner_hashes = tournament_fingerprint(), hashes()
    panels = [(s, m, r) for s in SUBJECTS for m in MODIFIERS for r in OPPONENTS]
    tasks = [(s, m, r, args.pairs, args.seed + i * 10000) for i, (s, m, r) in enumerate(panels)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(evaluate, tasks))
    if tournament_fingerprint() != fingerprint or hashes() != runner_hashes:
        raise RuntimeError("Simulation inputs changed during measurement")
    result = {"engine_label": args.engine_label, "simulation_fingerprint": fingerprint,
              "runner_hashes": runner_hashes, "python_version": platform.python_version(),
              "seed": args.seed, "pairs": args.pairs, "turn_limit": TURN_LIMIT,
              "kingdom": KINGDOM, "total_games": len(rows) * args.pairs * 2,
              "limitations": "Fixed baseline policies (Estates prioritized and removed from explicit trash priorities with Inheritance), artificial symmetric starting modifiers, one mixed board, three fixed opponents, no policy selection or purchase-timing claim. Match seeds and seats across engines; RNG streams can diverge after rule differences. Capped games are reported, not silently treated as completed.",
              "comparisons": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(f"Saved {result['total_games']} games to {args.output}")


if __name__ == "__main__":
    main()
