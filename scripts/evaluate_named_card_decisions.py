"""Screen and independently validate the remaining named decision families.

Policies are diagnostic opt-ins, with fixed purchases and both seats. Historical
studies and registered strategies are neither overwritten nor regraded here.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import platform
import random
from types import MethodType

from dominion.ai.base_ai import AI
from dominion.ai.gain_context import FreeGainContext
from dominion.ai.genetic_ai import GeneticAI
from dominion.ai import tactical_defaults
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from scripts import evaluate_card_tactics as common

CARDS = ("Courtier", "Courier", "Knights", "Rogue", "Stables", "Spice Merchant",
         "Armory", "Artificer", "Scheme", "Chapel", "Junk Dealer", "Counterfeit",
         "Moneylender", "Minion")
OPPONENTS = ("Smithy money", "Village and Laboratory engine", "Witch and kingdom attack")
POLICIES = common.POLICIES
TURN_LIMIT = 150
HOOKS = {
    "Courtier": ("choose_courtier_reveal", "choose_courtier_options"),
    "Courier": ("choose_courier_target",),
    "Knights": ("choose_card_to_trash_for_knight_attack",),
    "Rogue": ("choose_card_to_trash_for_rogue_attack", "should_gain_from_trash_with_rogue"),
    "Stables": ("choose_treasure_to_discard_for_stables",),
    "Spice Merchant": ("choose_treasure_to_trash_for_spice_merchant", "choose_spice_merchant_mode"),
    "Armory": ("choose_armory_gain",),
    "Artificer": ("choose_artificer_gain", "choose_artificer_discards", "choose_artificer_gain_after_discard"),
    "Scheme": ("choose_card_to_topdeck_for_scheme",),
    "Chapel": ("choose_trash",),
    "Junk Dealer": ("choose_card_to_trash_with_junk_dealer",),
    "Counterfeit": ("should_replay_treasure_with_counterfeit",),
    "Moneylender": ("should_trash_copper_for_moneylender",),
    "Minion": ("choose_minion_mode",),
}


def kingdom(card):
    return (card, "Village", "Smithy", "Laboratory", "Market", "Witch", "Militia", "Moat", "Merchant", "Festival")


def income(cards):
    return sum(c.stats.coins for c in cards if c.is_treasure)


def value(state, player, card, source="Rogue", destination="discard"):
    return tactical_defaults.free_gain_value(
        state, player, card, FreeGainContext.build(state, player, source, destination)
    )


def courtier_options(self, state, player, options, count):
    order = ["coins", "gold", "action", "buy"]
    if player.actions == 0 and any(state.is_action(c) for c in player.hand):
        order = ["action", "coins", "gold", "buy"]
    elif state.supply.get("Province", 8) <= 2:
        order = ["coins", "buy", "action", "gold"]
    return [o for o in order if o in options][:count]


def courier(self, state, player, choices):
    return max(choices, key=lambda c: (c.stats.cards * 2 + c.stats.coins * 2
        + c.stats.actions, c.cost.coins, c.name), default=None)


def victim(self, state, player, choices):
    return min(choices, key=lambda c: (value(state, player, c)
        - (6 if c.is_knight and self.subject == "Knights" else 0), c.name), default=None)


def gain(self, state, player, choices):
    return max(choices, key=lambda c: (value(state, player, c, self.subject,
        "deck" if self.subject in {"Armory", "Artificer"} else "discard"), c.name), default=None)


def stables(self, state, player, choices):
    pick = AI.choose_treasure_to_discard_for_stables(player.ai, state, player, choices)
    if pick and len(player.deck) + len(player.discard) <= 3:
        now = player.coins + income(player.hand)
        if now >= 8 > now - income([pick]):
            return None
    return pick


def spice_mode(self, state, player):
    # Prefer a cash breakpoint once draw is unlikely to be needed for Actions.
    now = player.coins + income(player.hand)
    if not any(c.is_action for c in player.hand) and any(now < n <= now + 2 for n in (5, 6, 8)):
        return "coins"
    return "cards"


def artificer(self, state, player, choices):
    from dominion.cards.adventures.artificer import is_artificer_junk
    budget = sum(is_artificer_junk(c) for c in player.hand)
    choices = [c for c in choices if 0 < state.get_card_cost(player, c) <= budget]
    return gain(self, state, player, choices)


def artificer_after(self, state, player, choices, planned):
    pick = gain(self, state, player, choices)
    return pick if pick and value(state, player, pick, "Artificer", "deck") > 0 else None


def scheme(self, state, player, choices):
    return max(choices, key=lambda c: (c.stats.actions * 2 + c.stats.cards * 2 + c.stats.coins,
        c.cost.coins, c.name), default=None)


def trash(self, state, player, choices):
    # Preserve current points late and at least $6 printed deck income early.
    for name in ("Curse", "Estate", "Copper"):
        if name == "Estate" and state.supply.get("Province", 8) <= 2:
            continue
        if name == "Copper" and income(player.all_cards()) <= 6:
            continue
        pick = next((c for c in choices if c is not None and c.name == name), None)
        if pick:
            return pick
    return None


def junk_dealer(self, state, player, choices):
    return trash(self, state, player, choices) or victim(self, state, player, choices)


def counterfeit(self, state, player, choices):
    # Avoid compulsory conversion of useful long-term income into a one-turn boost.
    return next((c for c in choices if c.name in {"Copper", "Spoils"}), None)


def moneylender(self, state, player):
    return income(player.all_cards()) > 4 or state.supply.get("Province", 8) <= 2


def minion(self, state, player):
    now = player.coins + income(player.hand)
    if now < 8 <= now + 2:
        return "coins"
    return "discard" if income(player.hand) < 4 else "coins"


ALTERNATIVES = {
    "Courtier": {"choose_courtier_options": courtier_options},
    "Courier": {"choose_courier_target": courier},
    "Knights": {"choose_card_to_trash_for_knight_attack": victim},
    "Rogue": {"choose_card_to_trash_for_rogue_attack": victim, "should_gain_from_trash_with_rogue": gain},
    "Stables": {"choose_treasure_to_discard_for_stables": stables},
    "Spice Merchant": {"choose_spice_merchant_mode": spice_mode},
    "Armory": {"choose_armory_gain": gain},
    "Artificer": {"choose_artificer_gain": artificer, "choose_artificer_gain_after_discard": artificer_after},
    "Scheme": {"choose_card_to_topdeck_for_scheme": scheme},
    "Chapel": {"choose_trash": trash},
    "Junk Dealer": {"choose_card_to_trash_with_junk_dealer": junk_dealer},
    "Counterfeit": {"should_replay_treasure_with_counterfeit": counterfeit},
    "Moneylender": {"should_trash_copper_for_moneylender": moneylender},
    "Minion": {"choose_minion_mode": minion},
}


def label(value):
    if isinstance(value, (list, tuple)):
        return [label(v) for v in value]
    return value.name if hasattr(value, "name") else value


def candidate(card, policy, counts=None):
    strategy = EnhancedStrategy()
    strategy.subject = card
    strategy.name = f"{card} fixed money: {policy}"
    # Cheap subjects are bought before Silver; expensive ones before Gold.
    strategy.gain_priority = [PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
        PriorityRule(card, PriorityRule.max_in_deck(card, 2)), PriorityRule("Gold"),
        PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)), PriorityRule("Silver"),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 1))]
    strategy.action_priority = [PriorityRule(card), PriorityRule("Smithy")]
    strategy.treasure_priority = [PriorityRule("Counterfeit"), PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
    strategy.trash_priority = [PriorityRule("Curse"),
        PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
        PriorityRule("Copper", lambda _s, p: income(p.all_cards()) > 4)]
    if policy == "contextual":
        for hook, function in ALTERNATIVES[card].items():
            setattr(strategy, hook, MethodType(function, strategy))
    if counts is not None:
        for hook in HOOKS[card]:
            # Observe inside the strategy adapter when available, otherwise
            # install an equivalent BaseAI policy. Counterfeit dispatches here.
            baseline = getattr(strategy, hook, None)
            if baseline is None:
                def baseline(state, player, *args, _hook=hook):
                    return getattr(AI, _hook)(player.ai, state, player, *args)
            def observed(*args, _hook=hook, _base=baseline):
                result = _base(*args)
                counts[f"{_hook}: {json.dumps(label(result), sort_keys=True)}"] += 1
                return result
            setattr(strategy, hook, observed)
    return strategy


def opponent(card, name):
    if name != OPPONENTS[2]:
        return common.opponent(name)
    strategy = EnhancedStrategy()
    strategy.name = name
    target = card if card in {"Knights", "Rogue", "Minion"} else "Militia"
    strategy.gain_priority = [PriorityRule("Province"),
        PriorityRule(target, PriorityRule.max_in_deck(target, 2)),
        PriorityRule("Witch", PriorityRule.max_in_deck("Witch", 1)), PriorityRule("Gold"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)), PriorityRule("Silver")]
    strategy.action_priority = [PriorityRule("Witch"), PriorityRule(target)]
    return strategy


def run_game(card, rival, policy, seed, seat, *, observe=True):
    random.seed(seed)
    counts = Counter()
    subject = GeneticAI(candidate(card, policy, counts if observe else None))
    other = GeneticAI(opponent(card, rival))
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([subject, other] if seat == 0 else [other, subject], [get_card(n) for n in kingdom(card)])
    while not state.is_game_over() and state.turn_number < TURN_LIMIT:
        state.play_turn()
    ours, theirs = state.players[seat], state.players[1 - seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (ours, theirs)]
    return {"seed": seed, "seat": seat, "policy": policy,
        "win_share": 1 if ranks[0] > ranks[1] else 0 if ranks[0] < ranks[1] else .5,
        "score_margin": ranks[0][0] - ranks[1][0], "scores": [r[0] for r in ranks],
        "turns_taken": [ours.turns_taken, theirs.turns_taken],
        "truncated": not state._normal_game_end_reached(), "decisions": dict(counts)}


def summarize(records):
    result = common.summarize(records)
    # Worst-case sensitivity: each capped outcome may be anywhere in [0,1].
    total = result["games_per_policy"]
    caps = {p: result["policies"][p]["truncated_games"] / total for p in POLICIES}
    result["cap_sensitivity_delta"] = [max(-1, result["win_share_delta"] - sum(caps.values())),
                                        min(1, result["win_share_delta"] + sum(caps.values()))]
    result["cap_sensitivity_95_interval"] = [max(-1, result["delta_95_interval"][0] - sum(caps.values())),
                                             min(1, result["delta_95_interval"][1] + sum(caps.values()))]
    return result


def evaluate(task):
    card, rival, pairs, start = task
    records = [run_game(card, rival, policy, start + offset, seat)
        for offset in range(pairs) for policy in POLICIES for seat in (0, 1)]
    return {"card": card, "opponent": rival, "kingdom": kingdom(card),
            "seed_start": start, **summarize(records), "records": records}


def scenarios():
    from dominion.game.cleanup import _resolve_cleanup_triggers
    from dominion.game.player_state import PlayerState
    rows = []
    fixtures = {
        "early building": (["Estate", "Copper", "Copper"], 8),
        "constrained hand": (["Silver", "Gold"], 8),
        "excessive copies": (["Smithy", "Smithy", "Smithy", "Copper", "Province"], 8),
        "endgame": (["Estate", "Copper", "Silver", "Gold"], 2),
    }
    for card in CARDS:
        for stage, (hand, provinces) in fixtures.items():
            for policy in POLICIES:
                random.seed(4321)
                counts = Counter()
                player = PlayerState(GeneticAI(candidate(card, policy, counts)))
                other = PlayerState(GeneticAI(EnhancedStrategy()))
                state = GameState([player, other], supply={n: 10 for n in kingdom(card) if n != "Knights"})
                state.supply.update({"Province": provinces, "Copper": 40, "Silver": 40, "Gold": 30, "Estate": 8, "Curse": 10})
                state.log_callback = lambda *_: None
                initial_hand = list(hand)
                if stage == "excessive copies":
                    initial_hand[:3] = ["Sir Bailey" if card == "Knights" else card] * 3
                player.hand = [get_card(n) for n in initial_hand]
                player.deck = [get_card("Silver") for _ in range(4)]
                player.actions = 0
                physical = get_card("Sir Bailey" if card == "Knights" else card)
                player.in_play = [physical]
                if card == "Courier":
                    player.discard = [get_card("Smithy"), get_card("Gold")]
                if card in {"Rogue", "Knights"} and not (card == "Rogue" and stage == "endgame"):
                    # The subject is the victim; force a genuine two-card menu.
                    other.in_play = [physical]
                    player.in_play = []
                    player.deck = [get_card("Dame Anna"), get_card("Gold")]
                    state.current_player_index = 1
                elif card == "Rogue":
                    state.trash = [get_card("Duchy"), get_card("Gold")]
                if card == "Scheme":
                    player.in_play += [get_card("Smithy"), get_card("Village")]
                    _resolve_cleanup_triggers(state, player)
                else:
                    physical.on_play(state)
                rows.append({"card": card, "stage": stage, "policy": policy,
                    "initial_hand": initial_hand, "provinces": provinces,
                    "hand": [c.name for c in player.hand], "deck": [c.name for c in player.deck],
                    "discard": [c.name for c in player.discard], "trash": [c.name for c in state.trash],
                    "actions": player.actions, "coins": player.coins, "decisions": dict(counts)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "validate"), required=True)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence exists; choose a fresh --output path")
    if not 2 <= args.pairs <= 10000 or args.workers < 1 or args.seed < 0:
        parser.error("Require 2–10000 seed pairs, positive workers, nonnegative seed")
    fingerprint = tournament_fingerprint()
    hashes = {p: common.sha256(Path(p)) for p in (
        "scripts/evaluate_named_card_decisions.py", "scripts/evaluate_card_tactics.py")}
    tasks = [(card, rival, args.pairs, args.seed + i * 10000)
             for i, (card, rival) in enumerate((c, r) for c in CARDS for r in OPPONENTS)]
    selection_hash = None
    if args.phase == "validate":
        if not args.selection:
            parser.error("Validation requires --selection pointing to a completed screen")
        selection = json.loads(args.selection.read_text())
        if (selection["phase"] != "screen" or selection["runner_hashes"] != hashes
                or selection["simulation_fingerprint"] != fingerprint):
            parser.error("Screen must match runner, helper and simulation inputs")
        old = {r["seed"] for row in selection["comparisons"] for r in row["records"]}
        new = {start + n for _, _, pairs, start in tasks for n in range(pairs)}
        if old & new:
            parser.error("Validation seeds overlap the screen")
        recommendations = selection["recommendations"]
        selection_hash = common.sha256(args.selection)
    elif args.selection:
        parser.error("--selection is only used for validation")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = []
        for row in pool.map(evaluate, tasks):
            rows.append(row)
            print(f"{row['card']} / {row['opponent']}: delta {row['win_share_delta']:+.3f}", flush=True)
    if args.phase == "screen":
        recommendations = {card: "contextual" if all(
            r["cap_sensitivity_95_interval"][0] > 0
            for r in rows if r["card"] == card) else "default" for card in CARDS}
    if (tournament_fingerprint() != fingerprint or
            any(common.sha256(Path(p)) != digest for p, digest in hashes.items())):
        raise RuntimeError("Inputs changed during evaluation")
    payload = {"phase": args.phase, "simulation_fingerprint": fingerprint,
        "runner_hashes": hashes, "python_version": platform.python_version(),
        "turn_limit": TURN_LIMIT, "seed": args.seed, "pairs": args.pairs,
        "total_games": len(rows) * args.pairs * 4, "selection_sha256": selection_hash,
        "recommendations": recommendations, "scenarios": scenarios(),
        "selection_rule": "Opt in only when every opponent's screen delta lower bound and capped-outcome sensitivity lower bound exceed zero; freeze before validation.",
        "uncertainty": "95% Hoeffding bounds by independent seed blocks averaging both seats; per-comparison, no multiplicity adjustment. Score intervals are paired normal approximations. Caps also have worst-case outcome sensitivity.",
        "limitations": "Fixed purchase/action/trash/treasure priorities, one ten-card board per subject, three representative opponents; no genetic search or universal optimality claim. Knight/Rogue victim decisions only fire against opponents that actually attack with those cards. Courtier reveal, Spice Merchant trash and Artificer discard-selection hooks are tested but held at baseline in this contrast. RNG streams diverge after decisions. Production tactical preferences remain unchanged except live-type/rules corrections.",
        "comparisons": rows}
    if args.selection and common.sha256(args.selection) != selection_hash:
        raise RuntimeError("Screen evidence changed during validation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
