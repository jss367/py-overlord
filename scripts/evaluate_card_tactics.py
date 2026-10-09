"""Measure four connected card decisions without changing production defaults.

Screen on one seed range, lock recommendations, then validate on fresh seeds.
Both seats and both policies use identical purchases, hand order and card rules.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import platform
import random
from statistics import mean, stdev

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategies.big_money_smithy import create_big_money_smithy
from dominion.strategy.strategies.village_smithy_lab import create_village_smithy_lab

CARDS = ("Watchtower", "Clerk", "Investment", "Bounty Hunter")
KINGDOM = (*CARDS, "Village", "Smithy", "Laboratory", "Witch", "Militia", "Moat")
OPPONENTS = ("Smithy money", "Village and Laboratory engine", "Clerk and Witch attack")
POLICIES = ("default", "contextual")
TURN_LIMIT = 150


def late(state):
    return state.supply.get("Province", 8) <= 2


def money(cards):
    return sum(c.stats.coins for c in cards if c.is_treasure)


class ContextualStrategy(EnhancedStrategy):
    """Frozen diagnostic alternatives; these are not installed as defaults."""

    def choose_watchtower_reaction(self, state, player, gained_card):
        if gained_card.name == "Copper" and money(player.all_cards()) <= 4:
            return None
        if (gained_card.is_action and not gained_card.stats.actions
                and sum(c.is_action and not c.stats.actions for c in player.all_cards()) >= 3):
            return None
        return super().choose_watchtower_reaction(state, player, gained_card)

    def choose_card_to_topdeck_for_clerk(self, state, player, choices):
        # Pure scoring cards consume neither Actions nor money in this hand.
        dead = [c for c in choices if c.is_victory and not c.is_action and not c.is_treasure]
        if dead:
            return min(dead, key=lambda c: (c.cost.coins, c.name))
        return super().choose_card_to_topdeck_for_clerk(state, player, choices)

    def choose_investment_mode(self, state, player, can_trash_treasure):
        # The engine trashes Investment itself here. All remaining Treasures
        # score; the legacy treasure-selection helper is not an engine decision.
        variety = len({c.name for c in player.hand if state.is_treasure(c)})
        return "trash" if can_trash_treasure and late(state) and variety else "coin"

    def choose_bounty_hunter_exile(self, state, player, choices):
        from dominion.ai.base_ai import AI
        baseline = AI.choose_card_to_exile_for_bounty_hunter(player.ai, state, player, choices)
        already = {c.name for c in player.exile}
        if baseline is None or baseline.name not in already or not late(state):
            return baseline
        current_income = player.coins + money(player.hand) - money([baseline])
        fresh = [c for c in choices if c.name not in already
                 and current_income < 8 <= player.coins + money(player.hand) - money([c]) + 3]
        return min(fresh, key=lambda c: (c.cost.coins, c.name), default=baseline)


def candidate(card, policy):
    strategy = ContextualStrategy() if policy == "contextual" else EnhancedStrategy()
    # Only the specified hook varies: other contextual methods are rebound to
    # the production implementation, so this is a per-card comparison.
    hooks = {
        "Watchtower": "choose_watchtower_reaction",
        "Clerk": "choose_card_to_topdeck_for_clerk",
        "Investment": "choose_investment_mode",
        "Bounty Hunter": "choose_bounty_hunter_exile",
    }
    for name, hook in hooks.items():
        if name != card:
            setattr(strategy, hook, getattr(EnhancedStrategy, hook).__get__(strategy))
    strategy.name = f"{card} money: {policy}"
    strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold"),
        PriorityRule(card, PriorityRule.max_in_deck(card, 2)),
        PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)), PriorityRule("Silver"),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 1))]
    strategy.action_priority = [PriorityRule(card), PriorityRule("Smithy")]
    # Investment must precede other Treasures to expose its remaining-hand choice.
    strategy.treasure_priority = [PriorityRule("Investment"), PriorityRule("Gold"),
                                  PriorityRule("Silver"), PriorityRule("Copper")]
    strategy.trash_priority = [PriorityRule("Curse"),
        PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
        PriorityRule("Copper", lambda _s, p: money(p.all_cards()) > 4)]
    return strategy


def opponent(name):
    if name == OPPONENTS[0]:
        return create_big_money_smithy()
    if name == OPPONENTS[1]:
        return create_village_smithy_lab()
    strategy = EnhancedStrategy()
    strategy.name = name
    strategy.gain_priority = [PriorityRule("Province"),
        PriorityRule("Witch", PriorityRule.max_in_deck("Witch", 1)),
        PriorityRule("Clerk", PriorityRule.max_in_deck("Clerk", 2)), PriorityRule("Gold"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)), PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Witch"), PriorityRule("Clerk")]
    return strategy


class ObservedAI(GeneticAI):
    def __init__(self, strategy):
        super().__init__(strategy)
        self.decisions = Counter()

    def record(self, hook, value):
        label = value.name if hasattr(value, "name") else str(value)
        self.decisions[f"{hook}: {label}"] += 1
        return value

    def choose_watchtower_reaction(self, state, player, gained_card):
        return self.record("Watchtower", super().choose_watchtower_reaction(state, player, gained_card))

    def choose_card_to_topdeck_for_clerk(self, state, player, choices):
        return self.record("Clerk response", super().choose_card_to_topdeck_for_clerk(state, player, choices))

    def should_play_clerk_reaction(self, state, player, clerk=None):
        return self.record("Clerk reaction", super().should_play_clerk_reaction(state, player, clerk))

    def choose_investment_mode(self, state, player, can_trash_treasure):
        return self.record("Investment", super().choose_investment_mode(state, player, can_trash_treasure))

    def choose_card_to_exile_for_bounty_hunter(self, state, player, choices):
        return self.record("Bounty Hunter", super().choose_card_to_exile_for_bounty_hunter(state, player, choices))


def run_game(card, rival, policy, seed, seat):
    random.seed(seed)
    subject = ObservedAI(candidate(card, policy))
    other = GeneticAI(opponent(rival))
    ais = [subject, other] if seat == 0 else [other, subject]
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game(ais, [get_card(name) for name in KINGDOM])
    while not state.is_game_over() and state.turn_number < TURN_LIMIT:
        state.play_turn()
    ours, theirs = state.players[seat], state.players[1 - seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (ours, theirs)]
    return {"seed": seed, "seat": seat, "policy": policy,
            "win_share": 1 if ranks[0] > ranks[1] else 0 if ranks[0] < ranks[1] else .5,
            "score_margin": ranks[0][0] - ranks[1][0], "scores": [r[0] for r in ranks],
            "turns_taken": [ours.turns_taken, theirs.turns_taken],
            "truncated": not state._normal_game_end_reached(), "decisions": dict(subject.decisions)}


def bounded_interval(values, width):
    # Independent seed blocks, bounded outcomes. Nondegenerate at zero variance.
    radius = width * math.sqrt(math.log(40) / (2 * len(values)))
    return [max(-1 if width == 2 else 0, mean(values) - radius), min(1, mean(values) + radius)]


def summarize(records):
    seeds = sorted({r["seed"] for r in records})
    blocks = {p: [] for p in POLICIES}
    margins = {p: [] for p in POLICIES}
    for seed in seeds:
        for policy in POLICIES:
            games = [r for r in records if r["seed"] == seed and r["policy"] == policy]
            if {r["seat"] for r in games} != {0, 1} or len(games) != 2:
                raise ValueError("Every seed/policy must contain exactly both seats")
            blocks[policy].append(mean(r["win_share"] for r in games))
            margins[policy].append(mean(r["score_margin"] for r in games))
    deltas = [b - a for a, b in zip(blocks["default"], blocks["contextual"])]
    score_deltas = [b - a for a, b in zip(margins["default"], margins["contextual"])]
    score_radius = 1.96 * stdev(score_deltas) / len(seeds) ** .5 if len(seeds) > 1 else 0
    policies = {}
    for policy in POLICIES:
        counts = Counter()
        for r in records:
            if r["policy"] == policy:
                counts.update(r["decisions"])
        policies[policy] = {"win_share": mean(blocks[policy]),
            "win_share_95_interval": bounded_interval(blocks[policy], 1),
            "score_margin": mean(margins[policy]), "decisions": dict(counts),
            "truncated_games": sum(r["truncated"] for r in records if r["policy"] == policy)}
    return {"seed_pairs": len(seeds), "games_per_policy": len(seeds) * 2,
            "policies": policies, "win_share_delta": mean(deltas),
            "delta_95_interval": bounded_interval(deltas, 2),
            "score_margin_delta": mean(score_deltas),
            "score_delta_approximate_95_interval": [mean(score_deltas) - score_radius, mean(score_deltas) + score_radius]}


def evaluate(task):
    card, rival, pairs, seed_start = task
    records = [run_game(card, rival, policy, seed_start + offset, seat)
               for offset in range(pairs) for policy in POLICIES for seat in (0, 1)]
    return {"card": card, "opponent": rival, "seed_start": seed_start,
            **summarize(records), "records": records}


def scenarios():
    """Deterministic physical card plays, at four declared game stages."""
    rows = []
    fixtures = {
        "early building": (["Estate", "Copper", "Copper"], [], 8),
        "constrained hand": (["Copper", "Silver", "Gold"], [], 8),
        "excessive copies": (["Smithy", "Smithy", "Smithy", "Copper", "Province"], ["Estate"], 8),
        "endgame": (["Estate", "Copper", "Silver", "Gold"], ["Estate"], 2),
    }
    for card in CARDS:
        for stage, (hand, exile, provinces) in fixtures.items():
            if card == "Investment" and stage == "excessive copies":
                hand = ["Estate", "Investment", "Investment", "Copper", "Silver", "Gold"]
            for policy in POLICIES:
                player = PlayerState(ObservedAI(candidate(card, policy)))
                player.hand = [get_card(n) for n in hand]
                player.exile = [get_card(n) for n in exile]
                state = GameState([player], supply={"Province": provinces, "Copper": 40, "Smithy": 10})
                state.log_callback = lambda *_: None
                initial = {"hand": hand, "exile": exile, "provinces": provinces, "coins": player.coins}
                if card == "Watchtower":
                    player.hand.append(get_card("Watchtower"))
                    initial["hand"] = [c.name for c in player.hand]
                    gain = "Smithy" if stage == "excessive copies" else "Copper"
                    initial["gain"] = gain
                    state.gain_card(player, get_card(gain))
                elif card == "Clerk":
                    attacker = PlayerState(GeneticAI(EnhancedStrategy()))
                    state.players.insert(0, attacker)
                    # The attack only reaches a hand with at least five cards.
                    player.hand.extend(get_card("Copper") for _ in range(5 - len(player.hand)))
                    initial["hand"] = [c.name for c in player.hand]
                    get_card("Clerk").on_play(state)
                else:
                    physical = get_card(card)
                    player.in_play = [physical]
                    physical.on_play(state)
                rows.append({"card": card, "stage": stage, "policy": policy, "initial": initial,
                    "hand": [c.name for c in player.hand], "deck": [c.name for c in player.deck],
                    "discard": [c.name for c in player.discard], "exile": [c.name for c in player.exile],
                    "trash": [c.name for c in state.trash], "coins": player.coins,
                    "vp_tokens": player.vp_tokens, "decisions": dict(player.ai.decisions)})
    return rows


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "validate"), required=True)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--selection", type=Path, help="Required validation input: saved screen result")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence exists; choose a fresh --output path")
    if not 2 <= args.pairs <= 10000 or args.workers < 1 or args.seed < 0:
        parser.error("Require 2–10000 seed pairs, one worker, and a nonnegative seed")
    fingerprint, runner_hash = tournament_fingerprint(), sha256(Path(__file__))
    tasks = [(card, rival, args.pairs, args.seed + i * 10000)
             for i, (card, rival) in enumerate((c, r) for c in CARDS for r in OPPONENTS)]
    selection_hash = None
    if args.phase == "validate":
        if not args.selection:
            parser.error("Validation requires --selection pointing to a completed screen")
        selection = json.loads(args.selection.read_text())
        if (selection["phase"] != "screen" or selection["runner_sha256"] != runner_hash
                or selection["simulation_fingerprint"] != fingerprint):
            parser.error("Selection must come from a screen with matching runner and simulation inputs")
        previous_seeds = {r["seed"] for row in selection["comparisons"] for r in row["records"]}
        new_seeds = {start + offset for _, _, pairs, start in tasks for offset in range(pairs)}
        if previous_seeds & new_seeds:
            parser.error("Validation seeds overlap the screen")
        recommendations = selection["recommendations"]
        selection_hash = sha256(args.selection)
    elif args.selection:
        parser.error("--selection is only used for validation")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = []
        for row in pool.map(evaluate, tasks):
            rows.append(row)
            print(f"{row['card']} / {row['opponent']}: delta {row['win_share_delta']:+.3f}", flush=True)
    if args.phase == "screen":
        # Predetermined selection rule: opt in only if every opponent has a
        # positive lower bound. Validation cannot change this recommendation.
        recommendations = {card: "contextual" if all(r["delta_95_interval"][0] > 0
            for r in rows if r["card"] == card) else "default" for card in CARDS}
    if tournament_fingerprint() != fingerprint or sha256(Path(__file__)) != runner_hash:
        raise RuntimeError("Inputs changed during evaluation; do not publish mixed results")
    if args.selection and sha256(args.selection) != selection_hash:
        raise RuntimeError("Selection evidence changed during validation")
    payload = {"phase": args.phase, "simulation_fingerprint": fingerprint,
        "runner_sha256": runner_hash, "python_version": platform.python_version(),
        "kingdom": KINGDOM, "turn_limit": TURN_LIMIT, "seed": args.seed,
        "total_games": len(rows) * args.pairs * 4, "selection_sha256": selection_hash,
        "recommendations": recommendations, "scenarios": scenarios(),
        "selection_rule": "Use contextual only if all three screen delta lower bounds exceed zero; lock before validation.",
        "uncertainty": "95% Hoeffding bounds clustered by independent seed (both seats averaged); rate range [0,1], delta range [-1,1]. Score-delta intervals are paired normal approximations. Per-comparison, not multiplicity adjusted.",
        "limitations": "Fixed diagnostic purchase policies and one kingdom; no genetic optimization. Clerk reaction timing is unchanged in both arms. Game RNG streams can diverge after different decisions; equal initial seeds do not imply identical subsequent draws. No production baseline changes.",
        "comparisons": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
