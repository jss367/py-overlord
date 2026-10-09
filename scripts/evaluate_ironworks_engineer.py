"""Screen, freeze and validate contextual Ironworks/Engineer gain policies.

The compatibility panel compares purchase-selector decisions with inherited
contextual decisions on registered strategies' boards, using the same current
rules in both arms. It does not recreate historical engine defects.
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform
import random

from dominion.ai import tactical_defaults
from dominion.ai.gain_context import FreeGainContext
from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.base_card import CardCost
from dominion.cards.gain_decisions import gain_menu, resolve_gain
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.prophecies.registry import get_prophecy
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader
from scripts.evaluate_card_tactics import summarize

SOURCES = ("Ironworks", "Engineer")
OPPONENTS = ("big_money_smithy", "village_smithy_lab", "chapel_witch")
POLICIES = ("default", "contextual")
TURN_LIMIT = 150
REGISTERED = (
    ("suzhou_groundskeeper_engine", "boards/suzhou.txt"),
    ("taskmaster_workforce_best", "boards/taskmaster_workforce.txt"),
    ("recruiter_kitsune_courtyard_engine", "boards/recruiter_kitsune.txt"),
    ("recruiter_kitsune_counterfeit_money", "boards/recruiter_kitsune.txt"),
    ("recruiter_kitsune_six_courtyards", "boards/recruiter_kitsune.txt"),
)


def cash_out_engineer(state, player):
    """Frozen diagnostic: late points or an excessive-copy conversion."""
    return FreeGainContext.build(state, player, "Engineer").endgame or player.count("Engineer") >= 3


class ContextualPolicy(EnhancedStrategy):
    """An opt-in diagnostic, with no mutation of production defaults."""

    def choose_free_gain(self, state, player, choices, context):
        if context.source != "Engineer" or not context.can_trash_source or not cash_out_engineer(state, player):
            return tactical_defaults.choose_free_gain(state, player, choices, context)
        # Project the extra gain to rank complete pairs. Physical execution
        # rebuilds the menu after reactions; this projection cannot model them.
        def pair_value(first):
            counts = dict(context.owned_counts)
            counts[first.name] = counts.get(first.name, 0) + 1
            counts["Engineer"] = max(0, counts.get("Engineer", 0) - 1)
            after = replace(context, owned_counts=counts, sacrificed=context.source_card,
                            can_trash_source=False, gain_number=2, previous_gain=first)
            remaining = [c for c in choices if c.name != first.name or state.supply.get(first.name, 0) > 1]
            second = tactical_defaults.choose_free_gain(state, player, remaining, after)
            return tactical_defaults.free_gain_value(state, player, first, context) + max(
                0, tactical_defaults.free_gain_value(state, player, second, after)
            )
        return max(choices, key=lambda c: (pair_value(c), c.cost.coins, c.name), default=None)

    def should_trash_engineer_for_extra_gains(self, state, player, engineer):
        if not cash_out_engineer(state, player):
            return False
        context = FreeGainContext.build(state, player, "Engineer", sacrificed=engineer)
        choices = gain_menu(state, player, CardCost(coins=4))
        best = tactical_defaults.choose_free_gain(state, player, choices, context)
        return best is not None and tactical_defaults.free_gain_value(state, player, best, context) > 0


def candidate(source, policy):
    strategy = ContextualPolicy() if policy == "contextual" else EnhancedStrategy()
    strategy.name = f"{source} fixed purchases: {policy}"
    strategy.gain_priority = [PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
        PriorityRule(source, PriorityRule.max_in_deck(source, 2)), PriorityRule("Gold"),
        PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)), PriorityRule("Silver"),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 2))]
    strategy.action_priority = [PriorityRule(source), PriorityRule("Village"), PriorityRule("Smithy")]
    if policy == "contextual":
        strategy.free_gain_priority = []
    return strategy


class ObservedAI(GeneticAI):
    def __init__(self, strategy):
        super().__init__(strategy)
        self.decisions = Counter()

    def choose_free_gain(self, state, player, choices, context):
        result = super().choose_free_gain(state, player, choices, context)
        self.decisions[f"{context.source} gain {context.gain_number}: {getattr(result, 'name', None)}"] += 1
        return result

    def should_trash_engineer_for_extra_gains(self, state, player, engineer):
        choice = super().should_trash_engineer_for_extra_gains(state, player, engineer)
        self.decisions[f"Engineer self-trash: {choice}"] += 1
        return choice


class PurchaseSelectorAI(ObservedAI):
    def choose_free_gain(self, state, player, choices, context):
        if context.source not in SOURCES:
            return super().choose_free_gain(state, player, choices, context)
        pick = resolve_gain(self.choose_buy(state, choices), choices)
        pick = pick or tactical_defaults.purchase_gain_fallback(choices, context.source)
        self.decisions[f"{context.source} gain {context.gain_number}: {getattr(pick, 'name', None)}"] += 1
        return pick


@lru_cache(maxsize=1)
def strategy_loader():
    return StrategyLoader()


def run_game(spec, policy, seed, seat):
    random.seed(seed)
    loader = strategy_loader()
    if spec.get("strategy"):
        board = load_board(spec["board"])
        strategy = loader.get_strategy(spec["strategy"])
        ours = (PurchaseSelectorAI if policy == "default" else ObservedAI)(strategy)
    else:
        source = spec["source"]
        board = BoardConfig([source, "Village", "Smithy", "Laboratory", "Market",
                             "Festival", "Witch", "Militia", "Moat", "Watchtower"])
        ours = ObservedAI(candidate(source, policy))
    theirs = GeneticAI(loader.get_strategy(spec["opponent"]))
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ours, theirs] if seat == 0 else [theirs, ours],
                          [get_card(n) for n in board.kingdom_cards],
                          prophecy=get_prophecy(board.prophecy) if board.prophecy else None)
    while not state.is_game_over() and state.turn_number < TURN_LIMIT:
        state.play_turn()
    us, them = state.players[seat], state.players[1-seat]
    ranks = [(p.get_victory_points(), -p.turns_taken) for p in (us, them)]
    return {"seed": seed, "seat": seat, "policy": policy,
            "win_share": 1 if ranks[0] > ranks[1] else 0 if ranks[0] < ranks[1] else .5,
            "score_margin": ranks[0][0]-ranks[1][0], "scores": [r[0] for r in ranks],
            "turns_taken": [us.turns_taken, them.turns_taken],
            "truncated": not state._normal_game_end_reached(), "decisions": dict(ours.decisions)}


def evaluate(task):
    spec, pairs, start = task
    records = [run_game(spec, policy, start+offset, seat) for offset in range(pairs)
               for policy in POLICIES for seat in (0, 1)]
    return {**spec, "seed_start": start, **summarize(records), "records": records}


def scenarios():
    rows = []
    fixtures = {
        "early building": (["Estate", "Copper", "Copper"], [], 8),
        "constrained hand": (["Smithy", "Smithy", "Copper"], [], 8),
        "excessive copies": (["Smithy", "Copper"], ["Smithy"]*4, 8),
        "endgame": (["Estate", "Silver", "Gold"], [], 2),
    }
    for source in SOURCES:
        for stage, (hand, deck_extra, provinces) in fixtures.items():
            for policy in POLICIES:
                player = PlayerState(ObservedAI(candidate(source, policy)))
                state = GameState([player], supply={"Province":provinces, "Smithy":10,
                    "Village":10, "Silver":40, "Estate":8, source:10})
                state.log_callback = lambda *_: None
                state.phase = "action"
                player.actions = 0
                player.hand = [get_card(n) for n in hand]
                player.deck = [get_card(n) for n in ["Copper"]*10+deck_extra]
                physical = get_card(source)
                player.in_play = [physical]
                if stage == "excessive copies":
                    player.deck.extend(get_card(source) for _ in range(3))
                physical.play_effect(state)
                rows.append({"source":source, "stage":stage, "policy":policy,
                    "initial_hand":hand, "provinces":provinces,
                    "gains":[c.name for c in player.discard], "trash":[c.name for c in state.trash],
                    "actions":player.actions, "coins":player.coins,
                    "hand":[c.name for c in player.hand], "decisions":dict(player.ai.decisions)})
    return rows


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "validate", "compatibility"), required=True)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Evidence exists; choose a fresh output path")
    if not 2 <= args.pairs <= 10000 or args.workers < 1 or args.seed < 0:
        parser.error("Require 2–10000 pairs, a positive worker count and a nonnegative seed")
    runner = Path(__file__)
    helper = Path(__file__).with_name("evaluate_card_tactics.py")
    fingerprint, runner_hash, helper_hash = tournament_fingerprint(), sha256(runner), sha256(helper)
    if args.phase == "compatibility":
        specs = [dict(strategy=name, board=board, opponent="big_money_smithy") for name, board in REGISTERED]
    else:
        specs = [dict(source=source, opponent=rival) for source in SOURCES for rival in OPPONENTS]
    tasks = [(spec, args.pairs, args.seed+i*10000) for i, spec in enumerate(specs)]
    selection_hash = None
    if args.phase == "validate":
        if not args.selection:
            parser.error("Validation requires a completed screen via --selection")
        selection = json.loads(args.selection.read_text())
        if (selection['phase'] != 'screen' or selection['runner_sha256'] != runner_hash
                or selection['summary_helper_sha256'] != helper_hash
                or selection['simulation_fingerprint'] != fingerprint):
            parser.error("Screen runner and simulation inputs must match validation")
        old_seeds = {r['seed'] for row in selection['comparisons'] for r in row['records']}
        new_seeds = {start+offset for _, pairs, start in tasks for offset in range(pairs)}
        if old_seeds & new_seeds:
            parser.error("Screen and validation seed ranges overlap")
        recommendations = selection['recommendations']
        selection_hash = sha256(args.selection)
    elif args.selection:
        parser.error("Only validation accepts --selection")
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = []
        for row in pool.map(evaluate, tasks):
            rows.append(row)
            print(f"{row.get('source', row.get('strategy'))} / {row['opponent']}: {row['win_share_delta']:+.3f}", flush=True)
    if args.phase == "screen":
        recommendations = {source:'contextual' if all(row['delta_95_interval'][0] > 0
            for row in rows if row['source'] == source) else 'default' for source in SOURCES}
    elif args.phase == "compatibility":
        recommendations = {spec['strategy']:'preserve inherited preferences' for spec in specs}
    if tournament_fingerprint() != fingerprint or sha256(runner) != runner_hash or sha256(helper) != helper_hash:
        raise RuntimeError("Inputs changed while evaluating; refuse mixed evidence")
    if args.selection and sha256(args.selection) != selection_hash:
        raise RuntimeError("Selection evidence changed during validation")
    payload = {"phase":args.phase, "simulation_fingerprint":fingerprint,
        "runner_sha256":runner_hash, "summary_helper_sha256":helper_hash,
        "python_version":platform.python_version(), "seed":args.seed, "turn_limit":TURN_LIMIT,
        "total_games":len(rows)*args.pairs*4, "selection_sha256":selection_hash,
        "recommendations":recommendations, "scenarios":scenarios(),
        "policy_labels":{'default':'purchase selector', 'contextual':'inherited contextual selector'} if args.phase == 'compatibility'
            else {'default':'inherited purchases; keep Engineer', 'contextual':'independent contextual gains; diagnostic Engineer cash-out'},
        "varied_parameters":[] if args.phase == 'compatibility' else ['free-gain policy', 'Engineer joint pair valuation and self-trash timing'],
        "selection_rule":"Contextual only if every opponent screen delta lower bound is positive; lock before validation.",
        "uncertainty":"95% Hoeffding bounds on independent seed means with both seats averaged; paired score intervals are normal approximations. Per comparison, not multiplicity adjusted.",
        "limitations":"Fixed purchases, no optimizer or default promotion. Same current card rules in both arms; compatibility isolates decision wiring, not historical engine bugs. Projected Engineer pairs ignore gain reactions; actual execution rebuilds the menu. Equal seeds need not produce equal later draws after decisions diverge. Registered policies may never acquire a referenced card; report decision counts.",
        "comparisons":rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(payload,indent=2)+'\n')


if __name__ == '__main__':
    main()
