"""Compare free-gain policies under shared, corrected rules and paired seeds.

PYTHONPATH=. python scripts/evaluate_free_gain_tactics.py --pairs 100
Each seed runs both seats for both policies; confidence intervals use the seed
pair as the sampling unit. Opponents always use the current engine/defaults.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import hashlib
import platform
from pathlib import Path
import random
from statistics import mean, stdev

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import BoardConfig, load_board
from dominion.cards.registry import get_card
from dominion.cards.base_set.workshop import Workshop
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.landmarks.registry import get_landmark
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.reporting.tournament_state import tournament_fingerprint

TURN_LIMIT = 150
CURRENT_WORKSHOP_EFFECT = Workshop.play_effect


def legacy_gain(choices):
    return max(choices, key=lambda c: (
        c.name not in {"Curse", "Copper"} and not c.is_ruins,
        not c.is_victory, c.cost.coins, c.stats.cards, c.stats.actions,
        c.stats.coins, c.name,
    ), default=None)


class PreviousPolicyAI(GeneticAI):
    """Freeze pre-change choices, leaving legality and reactions identical."""

    def choose_free_gain(self, state, player, choices, context):
        choice = self.strategy.choose_gain(state, player, choices)
        if context.source == "Workshop":
            # Previously declined if the purchase list selected nothing.
            return choice
        return choice

    def choose_remodel_option(self, state, player, options):
        trash = self.choose_card_to_trash(state, [c for c, _ in options])
        if trash not in [c for c, _ in options]:
            trash = min((c for c, _ in options), key=lambda c: (
                0 if c.name == "Curse" else 1 if c.is_victory and not c.is_action
                else 2 if c.name == "Copper" else 3, c.cost.coins, c.name
            ), default=None)
        if trash is None:
            return None, None
        choices = next(gains for c, gains in options if c is trash)
        gain = self.strategy.choose_gain(state, player, choices + [None])
        if gain not in choices:
            gain = max(choices, key=lambda c: (
                c.cost.coins, c.cost.potions, c.stats.cards, c.name
            ), default=None)
        return trash, gain

    def choose_anvil_option(self, state, player, treasures, choices):
        gain_hook = getattr(self.strategy, "choose_anvil_gain", None)
        gain = gain_hook(state, player, choices) if gain_hook else self.strategy.choose_gain(state, player, choices)
        discard = self.choose_anvil_treasure_to_discard(state, player, treasures)
        return discard, gain

    def choose_quartermaster_option(self, state, player, mat, candidates):
        hook = getattr(self.strategy, "choose_quartermaster_option", None)
        if hook:
            return hook(state, player, mat, candidates)
        timing = self.strategy.quartermaster_take_all
        take = timing(state, player, mat) if type(self.strategy).quartermaster_take_all is not EnhancedStrategy.quartermaster_take_all else len(mat) >= 2
        if mat and (take or not candidates):
            return "take", max(mat, key=lambda c: (c.cost.coins, c.name))
        hook = self.strategy.choose_quartermaster_gain
        if type(self.strategy).choose_quartermaster_gain is not EnhancedStrategy.choose_quartermaster_gain:
            gain = hook(state, player, candidates)
        else:
            gain = self.strategy.choose_gain(state, player, candidates)
            if gain is None:
                rules = self.strategy._tactical_rules(state, player, "gain")
                covered = {r.card_name for r in rules}
                gain = legacy_gain([c for c in candidates if c.name not in covered] or candidates)
        return "gain", gain


def workshop_effect(card, state):
    """Reproduce the old optional decline only for the control AI."""
    if not isinstance(state.current_player.ai, PreviousPolicyAI):
        return CURRENT_WORKSHOP_EFFECT(card, state)
    from dominion.cards.gain_decisions import gain_menu, gain_selected, resolve_gain
    from dominion.cards.base_card import CardCost
    player = state.current_player
    choices = gain_menu(state, player, CardCost(4))
    gain = player.ai.choose_buy(state, choices)
    gain_selected(state, player, resolve_gain(gain, choices))


def candidate(source, independent):
    strategy = EnhancedStrategy()
    strategy.name = f"{source} money"
    strategy.gain_priority = [
        PriorityRule("Province"), PriorityRule("Gold"),
        PriorityRule(source, PriorityRule.max_in_deck(source, 2)),
        PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
        PriorityRule("Silver"),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
    ]
    strategy.action_priority = [PriorityRule(source), PriorityRule("Village"), PriorityRule("Smithy")]
    strategy.treasure_priority = [PriorityRule("Anvil"), PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
    if independent:
        strategy.free_gain_priority = []
    return strategy


def interval(values):
    estimate = mean(values)
    margin = 1.96 * stdev(values) / len(values) ** .5 if len(values) > 1 else 0
    return [round(estimate - margin, 4), round(estimate + margin, 4)]


def rate_interval(values):
    """Approximate Wilson bound using independent seeds, not correlated seats.

    A seed-pair's fractional score has at most Bernoulli variance. This uses
    that conservative variance bound and stays nondegenerate at 0 and 1.
    """
    p, n, z = mean(values), len(values), 1.96
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** .5 / denom
    return [round(max(0, center - margin), 4), round(min(1, center + margin), 4)]


def evaluate(task):
    spec, pairs, seed = task
    Workshop.play_effect = workshop_effect
    loader = StrategyLoader()
    board = load_board("boards/port_moresby.txt") if spec.get("strategy") else BoardConfig([
        spec["source"], "Village", "Smithy", "Laboratory", "Market", "Festival",
        "Militia", "Moat", "Watchtower", "Throne Room",
    ])
    records = []
    truncated = [0, 0]
    scores = [[], []]
    for pair in range(pairs):
        outcomes = [[], []]
        for policy in range(2):
            for seat in range(2):
                random.seed(seed + pair)
                strategy = loader.get_strategy(spec["strategy"]) if spec.get("strategy") else candidate(spec["source"], spec["independent"])
                ai = GeneticAI(strategy) if policy else PreviousPolicyAI(strategy)
                opponent = GeneticAI(loader.get_strategy(spec["opponent"]))
                ais = [ai, opponent] if seat == 0 else [opponent, ai]
                state = GameState([])
                state.log_callback = lambda *_: None
                state.initialize_game(ais, [get_card(n) for n in board.kingdom_cards],
                    events=[get_event(n) for n in board.events],
                    landmarks=[get_landmark(n) for n in board.landmarks])
                while not state.is_game_over() and state.turn_number < TURN_LIMIT:
                    state.play_turn()
                truncated[policy] += not state._normal_game_end_reached()
                players = [state.players[seat], state.players[1 - seat]]
                keys = [(p.get_victory_points(), -p.turns_taken) for p in players]
                outcomes[policy].append(1 if keys[0] > keys[1] else .5 if keys[0] == keys[1] else 0)
                scores[policy].append(keys[0][0])
        records.append([mean(outcomes[0]), mean(outcomes[1])])
    previous = [r[0] for r in records]
    current = [r[1] for r in records]
    delta = [r[1] - r[0] for r in records]
    return dict(**spec, seed=seed, pairs=pairs, games_per_policy=pairs * 2,
        previous_rate=mean(previous), current_rate=mean(current),
        previous_ci=rate_interval(previous), current_ci=rate_interval(current),
        delta=mean(delta), delta_ci=interval(delta),
        mean_vp=[mean(s) for s in scores], truncated=truncated, paired_outcomes=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=391000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(".context/free_gain_tactics_reproduction.json"))
    args = parser.parse_args()
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    if args.output.exists():
        parser.error("Output already exists; choose a fresh --output path to preserve prior outcomes")
    fingerprint = tournament_fingerprint()
    tasks = []
    opponents = ["big_money", "big_money_smithy", "village_smithy_lab"]
    for source in ("Workshop", "Remodel", "Anvil", "Quartermaster"):
        for independent in (False, True):
            for opponent in opponents:
                tasks.append((dict(source=source, independent=independent, opponent=opponent), args.pairs, args.seed))
    for strategy in ("port_moresby_quartermaster_money", "port_moresby_double_quartermaster_money", "port_moresby_copper_mat_money"):
        for opponent in ("port_moresby_barbarian_money", "port_moresby_falconer_trail_engine", "port_moresby_copper_mat_money"):
            tasks.append((dict(strategy=strategy, opponent=opponent), args.pairs, args.seed + 10000))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = []
        for result in pool.map(evaluate, tasks):
            results.append(result)
            print(json.dumps({k: v for k, v in result.items() if k != "paired_outcomes"}), flush=True)
    if tournament_fingerprint() != fingerprint:
        raise RuntimeError("Simulation sources changed during evaluation; rerun before saving results")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(seed=args.seed, pairs=args.pairs,
        turn_limit=TURN_LIMIT, source_fingerprint=fingerprint,
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python_version=platform.python_version(), confidence="95% approximate Wilson intervals with seed-pair variance bound for rates; paired normal intervals for differences; unadjusted exploratory comparisons",
        common_rules="Both policies use corrected componentwise costs, replay queues, and current opponents.",
        results=results), indent=2) + "\n"
    # Exclusive creation also protects an output created during the run.
    with args.output.open("x") as output:
        output.write(payload)


if __name__ == "__main__":
    main()
