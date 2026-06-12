import logging
import random
from copy import deepcopy
from typing import Callable, Optional, Tuple

import coloredlogs

from dominion.boards.loader import BoardConfig
from dominion.simulation.game_logger import GameLogger
from dominion.simulation.strategy_battle import StrategyBattle, canonical_way_name
from dominion.strategy.enhanced_strategy import PriorityRule, WayRule
from dominion.strategy.strategies.base_strategy import BaseStrategy

log = logging.getLogger(__name__)
coloredlogs.install(level="INFO", logger=log)


# Seed-context phase tags. Each evaluation phase draws its game seeds from a
# distinct block so screening, refinement, and confirmation never reuse the
# same shuffles (which would let a candidate overfit one set of deck orders),
# while every candidate evaluated *within* a phase shares the same seeds
# (common random numbers — deck luck cancels out of comparisons).
_SEED_PHASE_SCREEN = 0
_SEED_PHASE_REFINE = 1
_SEED_PHASE_CONFIRM = 2
_SEED_PHASE_REBASE = 3


def _distribute_games(total_budget: int, n_opponents: int) -> list[int]:
    """Distribute ``total_budget`` games across ``n_opponents``, preserving the
    budget exactly when feasible. Each opponent gets ``base`` games and the
    first ``remainder`` opponents get one extra. If the budget is smaller than
    the panel (degenerate case), every opponent still gets at least 1 game so
    no opponent is silently skipped — this overruns the budget but preserves
    the panel semantic."""
    if n_opponents <= 0:
        return []
    if total_budget < n_opponents:
        return [1] * n_opponents
    base, remainder = divmod(total_budget, n_opponents)
    return [base + (1 if i < remainder else 0) for i in range(n_opponents)]


class GeneticTrainer:
    """Trains Dominion strategies using a genetic algorithm"""

    def __init__(
        self,
        kingdom_cards: list[str],
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        games_per_eval: int = 10,
        log_folder: str = "training_logs",
        board_config: Optional[BoardConfig] = None,
        immigrant_fraction: float = 0.15,
        sharing_threshold: float = 0.8,
        shape_rewards: bool = True,
        simplify_genomes: bool = True,
        rule_pruning: bool = True,
        prune_warmup_generations: int = 3,
        prune_min_rules: int = 3,
        default_baseline_panel: bool = False,
        racing: bool = True,
        refine_games: Optional[int] = None,
        confirm_games: Optional[int] = None,
        race_top_fraction: float = 0.2,
        confirm_slack: float = 5.0,
        common_random_numbers: bool = True,
        eval_seed: Optional[int] = None,
        hall_of_fame_size: int = 3,
        hall_of_fame_interval: int = 10,
        structured_genome: bool = True,
    ):
        if kingdom_cards is None:
            if board_config is None:
                kingdom_cards = []
            else:
                kingdom_cards = board_config.kingdom_cards

        self.kingdom_cards = kingdom_cards
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.games_per_eval = games_per_eval
        self.board_config = board_config
        self.immigrant_fraction = immigrant_fraction
        self.sharing_threshold = sharing_threshold
        self.shape_rewards = shape_rewards
        self.simplify_genomes = simplify_genomes
        self.rule_pruning = rule_pruning
        self.prune_warmup_generations = prune_warmup_generations
        self.prune_min_rules = prune_min_rules
        self.default_baseline_panel = default_baseline_panel

        # --- Evaluation-integrity knobs (racing + variance reduction) ---
        # ``games_per_eval`` is the cheap *screening* budget every individual
        # gets. With ``racing`` on, the top ``race_top_fraction`` of each
        # generation is re-evaluated with ``refine_games`` extra games, and a
        # would-be champion only replaces the incumbent after both are scored
        # on the same ``confirm_games`` seeded games. This prevents the
        # winner's-curse failure mode where the returned champion is whichever
        # mediocre candidate got the luckiest single evaluation.
        self.racing = racing
        self.refine_games = refine_games if refine_games is not None else 2 * games_per_eval
        self.confirm_games = confirm_games if confirm_games is not None else 4 * games_per_eval
        self.race_top_fraction = race_top_fraction
        self.confirm_slack = confirm_slack
        # Common random numbers: every candidate in the same evaluation phase
        # plays the same seeded shuffles, so candidate-vs-candidate comparisons
        # cancel deck luck instead of compounding it.
        self.common_random_numbers = common_random_numbers
        self._eval_seed_base = eval_seed if eval_seed is not None else random.randrange(2**31)
        # When not None, evaluate_strategy seeds each game from this
        # (phase, generation) context. None = legacy unseeded behavior.
        self._eval_seed_context: Optional[tuple] = None

        # Hall of fame: past champions appended to the opponent panel so the
        # fitness gradient doesn't saturate once the population beats the
        # static baselines. Size 0 disables.
        self.hall_of_fame_size = hall_of_fame_size
        self.hall_of_fame_interval = hall_of_fame_interval
        self.hall_of_fame: list[BaseStrategy] = []

        # Structured "buy menu" genome: random init builds coherent menus
        # (greening block + capped kingdom picks) and mutation applies menu
        # edits from a curated gate vocabulary, instead of free-form condition
        # rewrites where almost every edit is noise. structured_genome=False
        # restores the legacy free-form operators for comparison.
        self.structured_genome = structured_genome
        from dominion.simulation.structured_genome import KingdomInfo
        self._kingdom_info = KingdomInfo.from_kingdom(kingdom_cards or [])

        self.battle_system = StrategyBattle(kingdom_cards, log_folder, board_config=board_config)
        if not self.kingdom_cards:
            raise ValueError("kingdom_cards cannot be empty")
        self.current_generation = 0
        self.logger = GameLogger(log_folder)
        self._strategies_to_inject: list[BaseStrategy] = []
        self._baseline_strategy = None
        self._baseline_panel: list[BaseStrategy] = []
        self._default_baseline_panel_cache: list[BaseStrategy] | None = None
        # List of per-opponent breakdown tuples. With ``shape_rewards=False``
        # each entry is ``(name, win_rate)``; with shaping on each entry is
        # ``(name, win_rate, avg_margin, shaped_fitness)``. Stored as a list
        # (not a dict) so multiple panel members sharing a name (e.g. two
        # BigMoneySmithy variants) each contribute independently.
        self.last_eval_breakdown: list[tuple] = []
        # Champion bookkeeping. ``_best_confirmed`` is the champion's fitness
        # from its most recent confirmation eval (racing mode) or its single
        # screening eval (legacy mode).
        self._best_strategy: Optional[BaseStrategy] = None
        self._best_confirmed: float = float("-inf")
        self._best_win_rate: float = 0.0
        # Breakdown captured at the moment the best individual was found.
        # ``last_eval_breakdown`` is overwritten by every evaluation, so by the
        # time ``train()`` returns it reflects whichever candidate was scored
        # last in the final generation -- not the saved champion. Callers that
        # need the champion's per-opponent breakdown (e.g. island manifests)
        # should read this attribute instead.
        self.best_eval_breakdown: list[tuple] = []

        # Cache card type lookups for filtering
        from dominion.cards.registry import get_card
        self._kingdom_action_cards = []
        self._kingdom_treasure_cards = []
        for card_name in self.kingdom_cards:
            try:
                card = get_card(card_name)
                if card.is_action:
                    self._kingdom_action_cards.append(card_name)
                if card.is_treasure:
                    self._kingdom_treasure_cards.append(card_name)
            except ValueError:
                pass

        # Cache way names available on the board (for way_policy mutations).
        # Only populated when the board declares any Ways; otherwise way_policy
        # mutators are no-ops since there's nothing to bind a rule to.
        # Parametric variants like "Way of the Mouse (Native Village)" are
        # stripped to their base name ("Way of the Mouse") so WayRule.way_name
        # matches the runtime ``Way.name`` (the ways/registry constructs the
        # mouse instance with the unparameterised name).
        self._kingdom_ways: list[str] = []
        if board_config is not None and board_config.ways:
            self._kingdom_ways = [canonical_way_name(w) for w in board_config.ways]

    _DEFAULT_BASELINE_NAMES = (
        "Big Money",
        "Big Money Smithy",
        "Chapel Witch",
        "Village Smithy Lab",
    )

    def build_default_baseline_panel(self) -> list[BaseStrategy]:
        """Return built-in baseline opponents compatible with this kingdom."""

        kingdom_set = set(self.kingdom_cards)
        panel: list[BaseStrategy] = []
        seen_names: set[str] = set()

        for name in self._DEFAULT_BASELINE_NAMES:
            strategy = self.battle_system.strategy_loader.get_strategy(name)
            if strategy is None:
                continue
            refs = self.battle_system._split_board_references(
                self.battle_system._extract_cards_from_strategy(strategy)
            )
            if not set(refs.kingdom_cards).issubset(kingdom_set):
                continue
            if refs.events or refs.projects or refs.ways or refs.landmarks or refs.allies:
                continue
            if strategy.name in seen_names:
                continue
            seen_names.add(strategy.name)
            panel.append(strategy)

        if not panel:
            big_money = self.battle_system.strategy_loader.get_strategy("Big Money")
            if big_money is not None:
                panel.append(big_money)
        return panel

    # Probability that ``_random_condition_with_compound`` wraps a normally
    # sampled inner condition in ``and_(card_in_play(X), inner)``. Tunable.
    _COMPOUND_CONDITION_PROB = 0.15

    def _random_condition_with_compound(self) -> "Callable | None":
        """Return a random callable condition, with ~15% probability returning
        a compound ``and_(card_in_play(X), inner)`` where ``X`` is drawn from
        the kingdom's action cards and ``inner`` is a normally-sampled
        condition.

        If the kingdom has no action cards, falls back to a non-compound
        condition (since ``card_in_play`` with no kingdom action is not
        meaningful).
        """
        if (
            self._kingdom_action_cards
            and random.random() < self._COMPOUND_CONDITION_PROB
        ):
            inner = self._random_condition()
            card = random.choice(self._kingdom_action_cards)
            if inner is None:
                # A degenerate ``and_(card_in_play(X))`` collapses to just the
                # card_in_play check; emit it directly so the _source string
                # stays clean.
                return PriorityRule.card_in_play(card)
            return PriorityRule.and_(PriorityRule.card_in_play(card), inner)
        return self._random_condition()

    def _random_condition(self) -> "Callable | None":
        """Return a random callable condition from a diverse vocabulary.

        card_in_play requires a real kingdom action card name, so this is
        an instance method (not a staticmethod) — it pulls the candidate set
        from self._kingdom_action_cards computed in __init__."""
        choices = [
            "provinces_left", "turn_number", "resources", "has_cards",
            "empty_piles", "deck_size", "action_density", "score_diff",
            "actions_in_play", "max_in_deck",
            "actions_gained_this_turn", "cards_gained_this_turn",
            "actions_in_hand", "terminals_in_hand", "treasures_in_hand",
            "excess_actions",
            "none",
        ]
        # card_in_play / card_in_hand only make sense if we have at least
        # one kingdom action card name to reference.
        if self._kingdom_action_cards:
            choices.append("card_in_play")
            choices.append("card_in_hand")
        kind = random.choice(choices)
        if kind == "provinces_left":
            op = random.choice(["<=", ">", ">=", "<"])
            amount = random.randint(2, 8)
            return PriorityRule.provinces_left(op, amount)
        if kind == "turn_number":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(3, 18)
            return PriorityRule.turn_number(op, amount)
        if kind == "resources":
            res = random.choice(["coins", "actions", "buys"])
            op = random.choice([">=", "<", "<=", ">"])
            amount = random.randint(1, 8)
            return PriorityRule.resources(res, op, amount)
        if kind == "has_cards":
            cards = random.sample(
                ["Silver", "Gold", "Copper", "Province", "Duchy", "Estate"],
                k=random.randint(1, 3),
            )
            amount = random.randint(0, 4)
            return PriorityRule.has_cards(cards, amount)
        if kind == "empty_piles":
            op = random.choice([">=", ">", "<="])
            amount = random.randint(1, 4)
            return PriorityRule.empty_piles(op, amount)
        if kind == "deck_size":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(8, 35)
            return PriorityRule.deck_size(op, amount)
        if kind == "action_density":
            op = random.choice([">=", "<="])
            percent = random.choice([20, 30, 40, 50, 60])
            return PriorityRule.action_density(op, percent)
        if kind == "score_diff":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.choice([-12, -6, -3, 0, 3, 6, 12])
            return PriorityRule.score_diff(op, amount)
        if kind == "actions_in_play":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.randint(0, 4)
            return PriorityRule.actions_in_play(op, amount)
        if kind == "max_in_deck":
            card = random.choice(["Silver", "Gold", "Copper", "Estate", "Curse"])
            amount = random.randint(1, 6)
            return PriorityRule.max_in_deck(card, amount)
        if kind == "actions_gained_this_turn":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(1, 4)
            return PriorityRule.actions_gained_this_turn(op, amount)
        if kind == "cards_gained_this_turn":
            op = random.choice(["<=", ">=", "<", ">"])
            amount = random.randint(1, 5)
            return PriorityRule.cards_gained_this_turn(op, amount)
        if kind == "card_in_play":
            card = random.choice(self._kingdom_action_cards)
            return PriorityRule.card_in_play(card)
        if kind == "card_in_hand":
            card = random.choice(self._kingdom_action_cards)
            return PriorityRule.card_in_hand(card)
        if kind == "actions_in_hand":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.randint(1, 4)
            return PriorityRule.actions_in_hand(op, amount)
        if kind == "terminals_in_hand":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.randint(1, 3)
            return PriorityRule.terminals_in_hand(op, amount)
        if kind == "treasures_in_hand":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.randint(1, 4)
            return PriorityRule.treasures_in_hand(op, amount)
        if kind == "excess_actions":
            op = random.choice([">=", "<=", ">", "<"])
            amount = random.choice([-1, 0, 1])
            return PriorityRule.excess_actions(op, amount)
        return None

    def _random_way_rule(self) -> Optional[WayRule]:
        """Build a random :class:`WayRule` over this kingdom's actions and ways.

        Returns ``None`` when the board has no ways (so callers can skip the
        rule cleanly without growing way_policy with stub entries).
        """
        if not self._kingdom_ways or not self._kingdom_action_cards:
            return None
        card = random.choice(self._kingdom_action_cards)
        way = random.choice(self._kingdom_ways)
        condition = None
        if random.random() < 0.5:
            condition = self._random_condition_with_compound()
        return WayRule(card, way, condition)

    def create_random_strategy(self) -> BaseStrategy:
        """Create a random strategy.

        With ``structured_genome`` (the default) this builds a coherent buy
        menu via :mod:`dominion.simulation.structured_genome`; the legacy
        free-form path shuffles all cards into an arbitrary gain order."""
        if self.structured_genome:
            from dominion.simulation.structured_genome import random_menu_strategy
            strategy = random_menu_strategy(self._kingdom_info)
            strategy.name = f"gen{self.current_generation}-{id(strategy)}"
            self._seed_way_policy(strategy)
            return self._normalize(strategy)

        strategy = BaseStrategy()
        strategy.name = f"gen{self.current_generation}-{id(strategy)}"

        # All possible cards
        all_cards = (
            self.kingdom_cards
            + ["Copper", "Silver", "Gold"]  # Treasures
            + ["Estate", "Duchy", "Province"]  # Victory cards
        )

        # Generate gain priorities (random subset in random order)
        gain_cards = list(all_cards)
        random.shuffle(gain_cards)
        strategy.gain_priority = []
        for card in gain_cards:
            condition = None
            if random.random() < 0.3:
                if card in ["Silver", "Gold", "Province"]:
                    cost = {"Silver": 3, "Gold": 6, "Province": 8}[card]
                    condition = PriorityRule.resources("coins", ">=", cost)
                elif card in self.kingdom_cards:
                    condition = PriorityRule.turn_number("<=", random.randint(5, 15))
                else:
                    condition = self._random_condition_with_compound()
            strategy.gain_priority.append(PriorityRule(card, condition))

        # Generate action priorities (only actual action cards)
        strategy.action_priority = []
        action_cards = list(self._kingdom_action_cards)
        random.shuffle(action_cards)
        for card in action_cards:
            if random.random() < 0.7:  # 70% chance to include each action
                condition = None
                if random.random() < 0.3:
                    if card in ["Village", "Festival"]:
                        condition = PriorityRule.resources("actions", "<", 2)
                    elif card in ["Smithy", "Laboratory"]:
                        condition = PriorityRule.resources("actions", ">=", 1)
                    else:
                        condition = self._random_condition_with_compound()
                strategy.action_priority.append(PriorityRule(card, condition))

        # Generate treasure priorities — include kingdom treasures
        treasure_list = list(self._kingdom_treasure_cards) + ["Gold", "Silver", "Copper"]
        random.shuffle(treasure_list)
        strategy.treasure_priority = [PriorityRule(t) for t in treasure_list]

        # Generate trash priorities
        strategy.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]

        self._seed_way_policy(strategy)

        return self._normalize(strategy)

    def _seed_way_policy(self, strategy: BaseStrategy) -> None:
        """Seed a small number of way_policy rules when the board has ways.

        Without seeding, no individual would ever try a non-default Way and
        the mutation-only path would discover them only by chance."""
        strategy.way_policy = []
        if self._kingdom_ways:
            for _ in range(random.randint(0, 2)):
                rule = self._random_way_rule()
                if rule is not None:
                    strategy.way_policy.append(rule)

    def set_baseline_strategy(self, strategy: BaseStrategy):
        """Set a custom baseline strategy to evaluate against instead of Big Money."""
        self._baseline_strategy = strategy

    def set_baseline_panel(self, panel: list[BaseStrategy]):
        """Set a panel of opponents. Games are split evenly across panel members,
        and fitness is the mean of per-opponent win rates. Overrides any single
        baseline set via set_baseline_strategy."""
        if not panel:
            raise ValueError("baseline panel cannot be empty")
        self._baseline_panel = list(panel)

    def _resolve_panel(self) -> list[BaseStrategy]:
        if self._baseline_panel:
            return self._baseline_panel
        if self._baseline_strategy is not None:
            return [self._baseline_strategy]
        if self.default_baseline_panel:
            if self._default_baseline_panel_cache is None:
                self._default_baseline_panel_cache = self.build_default_baseline_panel()
            if self._default_baseline_panel_cache:
                return self._default_baseline_panel_cache
        big_money = self.battle_system.strategy_loader.get_strategy("Big Money")
        if not big_money:
            raise ValueError("Big Money strategy not found")
        return [big_money]

    @staticmethod
    def _margin_to_score(avg_margin: float) -> float:
        """Map an average VP margin (player VP minus opponent VP) onto a
        shaped fitness contribution in ``[-100, 100]``.

        The mapping is the identity with clipping: a +20 average margin
        contributes +20 fitness points, a -20 average margin contributes
        -20, and very large margins clamp at +/-100. This keeps the
        shaping term on the same scale as a 0-100 win-rate signal so the
        weighted mix in :meth:`_shape_fitness` stays well-behaved.
        """
        if avg_margin > 100.0:
            return 100.0
        if avg_margin < -100.0:
            return -100.0
        return float(avg_margin)

    @staticmethod
    def _shape_fitness(win_rate_pct: float, avg_margin: float) -> float:
        """Combine win rate (0-100) and average score margin into a single
        shaped fitness value.

        Weights: 80% win rate (primary signal), 20% margin score. The margin
        score is computed by :meth:`_margin_to_score`, so a +20 average VP
        margin adds +4 fitness points (0.2 * 20) on top of the win-rate
        component, and a -20 average VP margin subtracts 4.
        """
        margin_score = GeneticTrainer._margin_to_score(avg_margin)
        return 0.8 * win_rate_pct + 0.2 * margin_score

    def evaluate_strategy(self, strategy: BaseStrategy) -> float:
        """Evaluate a strategy by playing games against each panel opponent.

        With ``shape_rewards=False`` (the historical behavior), returns the
        mean per-opponent win rate (0-100). With ``shape_rewards=True``
        (the default), returns ``0.8 * win_rate + 0.2 * margin_score`` per
        opponent and averages those — see :meth:`_shape_fitness`.

        When ``_eval_seed_context`` is set (train() sets it per evaluation
        phase), each seat-swapped pair of games is seeded from the context so
        all candidates evaluated in that phase play identical shuffles
        (common random numbers). The global RNG state is restored afterward so
        seeding can't make the GA's own mutation stream deterministic.
        """
        seeding = self._eval_seed_context is not None
        rng_snapshot = random.getstate() if seeding else None
        try:
            panel = list(self._resolve_panel())
            panel.extend(self.hall_of_fame)
            from dominion.ai.genetic_ai import GeneticAI
            from dominion.strategy.rule_pruning import reset_fire_flags

            # Reset fire flags so this eval's window is fresh. The walker
            # will mark rule._fired = True for every rule that matches
            # during the games below; the next-generation step uses those
            # flags to prune dead code.
            if self.rule_pruning:
                reset_fire_flags(strategy)

            games_for_opp = _distribute_games(self.games_per_eval, len(panel))
            breakdown: list[tuple] = []
            for i, opponent in enumerate(panel):
                games_per_opp = games_for_opp[i]
                board_references = self.battle_system._determine_board_references(strategy, opponent)
                kingdom_card_names = board_references.kingdom_cards
                landscape_kwargs = {
                    key: value
                    for key, value in {
                        "events": board_references.events,
                        "projects": board_references.projects,
                        "ways": board_references.ways,
                        "landmarks": board_references.landmarks,
                        "allies": board_references.allies,
                    }.items()
                    if value
                }
                wins = 0
                margin_total = 0.0
                for game_num in range(games_per_opp):
                    if seeding:
                        random.seed(self._game_seed(i, game_num))
                    ai1 = GeneticAI(strategy)
                    ai2 = GeneticAI(opponent)
                    if game_num % 2 == 0:
                        winner, scores, _l, _t = self.battle_system.run_game(
                            ai1,
                            ai2,
                            kingdom_card_names,
                            **landscape_kwargs,
                        )
                    else:
                        winner, scores, _l, _t = self.battle_system.run_game(
                            ai2,
                            ai1,
                            kingdom_card_names,
                            **landscape_kwargs,
                        )
                    if winner == ai1:
                        wins += 1
                    # ``scores`` is keyed by ai.name; an empty dict means no
                    # scores were reported, so treat margin as 0 for this game.
                    if scores:
                        my_score = scores.get(ai1.name, 0)
                        opp_score = scores.get(ai2.name, 0)
                        margin_total += my_score - opp_score
                rate = wins / games_per_opp * 100
                avg_margin = margin_total / games_per_opp
                if self.shape_rewards:
                    fitness = self._shape_fitness(rate, avg_margin)
                    breakdown.append((opponent.name, rate, avg_margin, fitness))
                else:
                    breakdown.append((opponent.name, rate))
            self.last_eval_breakdown = breakdown
            if self.shape_rewards:
                # Mean of the shaped per-opponent fitness values
                return sum(entry[3] for entry in breakdown) / len(breakdown)
            return sum(r for _, r in breakdown) / len(breakdown)
        except Exception as e:
            log.exception("Error evaluating strategy %s. Got error: %s", strategy.name, e)
            # Clear the breakdown so train() can't credit this strategy with
            # the prior candidate's per-opponent results, and return -inf so
            # a failed eval can never outrank legitimate (possibly negative)
            # shaped fitness in best-strategy tracking.
            self.last_eval_breakdown = []
            return float("-inf")
        finally:
            if rng_snapshot is not None:
                random.setstate(rng_snapshot)

    def _game_seed(self, opponent_index: int, game_num: int) -> int:
        """Derive the RNG seed for one game of a seeded evaluation.

        Consecutive seat-swapped games (game_num 2k and 2k+1) share a seed so
        each shuffle sequence is played from both seats. The seed depends only
        on (base, phase context, opponent, pair index) — never on the candidate
        — which is what makes the random numbers *common* across candidates.
        The context contains only ints, so the hash (and therefore the seeds)
        is reproducible across processes for a fixed ``eval_seed``.
        """
        pair_index = game_num // 2
        return hash((self._eval_seed_base, self._eval_seed_context, opponent_index, pair_index)) & 0x7FFFFFFF

    def _eval_with_budget(self, strategy: BaseStrategy, games: int, context: Optional[tuple]) -> float:
        """Run evaluate_strategy with a temporary games budget and seed context."""
        saved_games = self.games_per_eval
        saved_context = self._eval_seed_context
        self.games_per_eval = games
        self._eval_seed_context = context if self.common_random_numbers else None
        try:
            return self.evaluate_strategy(strategy)
        finally:
            self.games_per_eval = saved_games
            self._eval_seed_context = saved_context

    @staticmethod
    def _genome_signature(strategy: BaseStrategy) -> tuple:
        """Structural fingerprint of a genome: every rule's card and condition
        source, in order. Used to skip re-confirming the elite when it is the
        generation's best again (it usually is), saving the confirmation
        budget for genuinely new challengers."""

        def rule_sig(rules) -> tuple:
            return tuple(
                (r.card_name, getattr(getattr(r, "condition", None), "_source", None))
                for r in rules
            )

        way_sig = tuple(
            (r.card_name, r.way_name, getattr(getattr(r, "condition", None), "_source", None))
            for r in getattr(strategy, "way_policy", []) or []
        )
        return (
            rule_sig(strategy.gain_priority),
            rule_sig(strategy.action_priority),
            rule_sig(strategy.treasure_priority),
            rule_sig(strategy.trash_priority),
            way_sig,
        )

    def _record_champion_result(self, fitness: float, breakdown: list[tuple]) -> None:
        """Update the champion's confirmed fitness, breakdown, and win rate."""
        self._best_confirmed = fitness
        self.best_eval_breakdown = list(breakdown)
        if breakdown:
            self._best_win_rate = sum(entry[1] for entry in breakdown) / len(breakdown)

    def _set_champion(self, strategy: BaseStrategy, fitness: float, breakdown: list[tuple]) -> None:
        self._best_strategy = deepcopy(strategy)
        self._record_champion_result(fitness, breakdown)

    def _consider_challenger(self, challenger: BaseStrategy, screen_fitness: float, gen: int) -> None:
        """Decide whether ``challenger`` (this generation's best) should
        replace the incumbent champion.

        The incumbent and challenger are both evaluated on the same
        ``confirm_games`` seeded games, so the comparison is paired: deck luck
        cancels and the better strategy wins the head-to-head. Re-evaluating
        the incumbent every time also keeps its confirmed fitness current as
        the hall-of-fame panel evolves. A champion is never crowned from a
        single screening eval — that is the winner's-curse path this method
        exists to close."""
        if self._best_strategy is not None and self._genome_signature(challenger) == self._genome_signature(
            self._best_strategy
        ):
            return

        context = (_SEED_PHASE_CONFIRM, gen)

        if self._best_strategy is None:
            confirmed = self._eval_with_budget(challenger, self.confirm_games, context)
            if confirmed == float("-inf"):
                return
            self._set_champion(challenger, confirmed, self.last_eval_breakdown)
            log.info(
                "Champion confirmed at %.2f (screen estimate was %.2f)",
                confirmed,
                screen_fitness,
            )
            return

        # Don't spend the confirmation budget on challengers whose screening
        # estimate isn't even close to the incumbent.
        if screen_fitness < self._best_confirmed - self.confirm_slack:
            return

        incumbent_fitness = self._eval_with_budget(self._best_strategy, self.confirm_games, context)
        incumbent_breakdown = list(self.last_eval_breakdown)
        challenger_fitness = self._eval_with_budget(challenger, self.confirm_games, context)
        challenger_breakdown = list(self.last_eval_breakdown)

        if challenger_fitness > incumbent_fitness:
            self._set_champion(challenger, challenger_fitness, challenger_breakdown)
            log.info(
                "Champion replaced: challenger %.2f beat incumbent %.2f (confirmation, %d games)",
                challenger_fitness,
                incumbent_fitness,
                self.confirm_games,
            )
        else:
            if incumbent_fitness != float("-inf"):
                self._record_champion_result(incumbent_fitness, incumbent_breakdown)
            log.info(
                "Champion retained: incumbent %.2f vs challenger %.2f (confirmation, %d games)",
                incumbent_fitness,
                challenger_fitness,
                self.confirm_games,
            )

    def _update_hall_of_fame(self, gen: int) -> None:
        """Add the current champion to the opponent hall of fame (if novel)
        and rebase the champion's confirmed fitness on the new, harder panel."""
        champion = self._best_strategy
        if champion is None:
            return
        sig = self._genome_signature(champion)
        if any(self._genome_signature(member) == sig for member in self.hall_of_fame):
            return

        member = deepcopy(champion)
        member.name = f"HallOfFame-g{gen + 1}"
        self.hall_of_fame.append(member)
        if len(self.hall_of_fame) > self.hall_of_fame_size:
            self.hall_of_fame = self.hall_of_fame[-self.hall_of_fame_size :]
        log.info(
            "Hall of fame updated (%d member%s) — champion joins the opponent panel",
            len(self.hall_of_fame),
            "s" if len(self.hall_of_fame) != 1 else "",
        )

        # The panel just changed, so the incumbent's confirmed fitness is on
        # the old scale; re-measure it so future challenger gating is fair.
        rebased = self._eval_with_budget(champion, self.confirm_games, (_SEED_PHASE_REBASE, gen))
        if rebased != float("-inf"):
            self._record_champion_result(rebased, self.last_eval_breakdown)

    def _crossover(self, parent1: BaseStrategy, parent2: BaseStrategy) -> BaseStrategy:
        """Create a new strategy by combining two parent strategies"""
        child = deepcopy(parent1)

        # Crossover gain priorities
        for i, priority in enumerate(child.gain_priority):
            if random.random() < 0.5 and i < len(parent2.gain_priority):
                child.gain_priority[i] = deepcopy(parent2.gain_priority[i])

        # Crossover action priorities
        if parent2.action_priority:
            split_point = random.randint(0, len(child.action_priority))
            child.action_priority = child.action_priority[:split_point] + deepcopy(
                parent2.action_priority[split_point:]
            )

        # Crossover trash priorities
        if parent2.trash_priority:
            split_point = random.randint(0, len(child.trash_priority))
            child.trash_priority = child.trash_priority[:split_point] + deepcopy(parent2.trash_priority[split_point:])

        # Keep treasure priorities from one parent
        if random.random() < 0.5:
            child.treasure_priority = deepcopy(parent2.treasure_priority)

        # Crossover way_policy: 50/50 take parent2's whole list (way_policy is
        # typically short, so single-point splice is overkill).
        parent2_way_policy = getattr(parent2, "way_policy", None)
        if parent2_way_policy and random.random() < 0.5:
            child.way_policy = deepcopy(parent2_way_policy)

        return child

    def _mutate(self, strategy: BaseStrategy) -> BaseStrategy:
        """Mutate a strategy.

        With ``structured_genome`` (the default), mutations are menu edits —
        reorder, cap nudges, curated re-gating, pick add/drop — applied by
        :func:`dominion.simulation.structured_genome.mutate_menu`. The legacy
        free-form condition rewrites remain behind ``structured_genome=False``."""
        if self.structured_genome:
            from dominion.simulation.structured_genome import mutate_menu
            mutate_menu(strategy, self._kingdom_info, self.mutation_rate)
            self._mutate_way_policy(strategy)
            return strategy

        # --- Mutate gain priorities ---
        # Condition mutations: drop, replace, or fresh-from-none
        for priority in strategy.gain_priority:
            if random.random() < self.mutation_rate:
                if random.random() < 0.3:
                    if priority.condition is None:
                        # No condition — add one
                        if priority.card_name in ["Silver", "Gold", "Province"]:
                            cost = {"Silver": 3, "Gold": 6, "Province": 8}[priority.card_name]
                            priority.condition = PriorityRule.resources("coins", ">=", cost)
                        elif priority.card_name in self.kingdom_cards:
                            priority.condition = PriorityRule.turn_number("<=", random.randint(5, 15))
                        else:
                            priority.condition = self._random_condition_with_compound()
                    else:
                        # Existing condition — half the time drop it, half the time replace
                        if random.random() < 0.5:
                            priority.condition = None
                        else:
                            priority.condition = self._random_condition_with_compound()

        # Reorder: swap two adjacent gain rules
        if random.random() < self.mutation_rate and len(strategy.gain_priority) >= 2:
            i = random.randint(0, len(strategy.gain_priority) - 2)
            strategy.gain_priority[i], strategy.gain_priority[i + 1] = (
                strategy.gain_priority[i + 1],
                strategy.gain_priority[i],
            )

        # Occasionally move a random rule to a new position
        if random.random() < self.mutation_rate * 0.5 and len(strategy.gain_priority) >= 2:
            i = random.randint(0, len(strategy.gain_priority) - 1)
            rule = strategy.gain_priority.pop(i)
            j = random.randint(0, len(strategy.gain_priority))
            strategy.gain_priority.insert(j, rule)

        # Add a new kingdom card that's missing from the gain list
        if random.random() < self.mutation_rate * 0.3:
            existing = {r.card_name for r in strategy.gain_priority}
            missing = [c for c in self.kingdom_cards if c not in existing]
            if missing:
                card = random.choice(missing)
                pos = random.randint(0, len(strategy.gain_priority))
                strategy.gain_priority.insert(pos, PriorityRule(card, self._random_condition_with_compound()))

        # Remove a low-value gain entry (but keep at least 3 rules)
        if random.random() < self.mutation_rate * 0.2 and len(strategy.gain_priority) > 3:
            i = random.randint(0, len(strategy.gain_priority) - 1)
            strategy.gain_priority.pop(i)

        # --- Mutate action priorities ---
        if random.random() < self.mutation_rate:
            if strategy.action_priority:
                # Shuffle a portion of the action priorities
                split_point = random.randint(0, len(strategy.action_priority))
                shuffled = strategy.action_priority[split_point:]
                random.shuffle(shuffled)
                strategy.action_priority = strategy.action_priority[:split_point] + shuffled

                # Possibly modify conditions
                for priority in strategy.action_priority:
                    if random.random() < 0.3:
                        if priority.condition:
                            priority.condition = None
                        else:
                            if priority.card_name in ["Village", "Festival"]:
                                priority.condition = PriorityRule.resources("actions", "<", 2)
                            elif priority.card_name in ["Smithy", "Laboratory"]:
                                priority.condition = PriorityRule.resources("actions", ">=", 1)
                            else:
                                priority.condition = self._random_condition_with_compound()

        # Add/remove action cards (only actual action cards)
        if random.random() < self.mutation_rate * 0.3:
            existing = {r.card_name for r in strategy.action_priority}
            missing = [c for c in self._kingdom_action_cards if c not in existing]
            if missing:
                card = random.choice(missing)
                pos = random.randint(0, len(strategy.action_priority))
                strategy.action_priority.insert(pos, PriorityRule(card, self._random_condition_with_compound()))

        if random.random() < self.mutation_rate * 0.2 and len(strategy.action_priority) > 1:
            i = random.randint(0, len(strategy.action_priority) - 1)
            strategy.action_priority.pop(i)

        # --- Mutate treasure priorities ---
        if random.random() < self.mutation_rate and len(strategy.treasure_priority) >= 2:
            i = random.randint(0, len(strategy.treasure_priority) - 2)
            strategy.treasure_priority[i], strategy.treasure_priority[i + 1] = (
                strategy.treasure_priority[i + 1],
                strategy.treasure_priority[i],
            )

        # Add missing kingdom treasures to treasure priority
        if random.random() < self.mutation_rate * 0.3:
            existing_treasures = {r.card_name for r in strategy.treasure_priority}
            for card_name in self._kingdom_treasure_cards:
                if card_name not in existing_treasures:
                    pos = random.randint(0, len(strategy.treasure_priority))
                    strategy.treasure_priority.insert(pos, PriorityRule(card_name))

        # --- Mutate trash priorities ---
        if random.random() < self.mutation_rate:
            if strategy.trash_priority:
                for priority in strategy.trash_priority:
                    if random.random() < 0.3:
                        if priority.card_name == "Estate":
                            priority.condition = PriorityRule.provinces_left(">", random.randint(2, 6))
                        elif priority.card_name == "Copper":
                            min_treasures = random.randint(2, 4)
                            priority.condition = PriorityRule.has_cards(["Silver", "Gold"], min_treasures)

        self._mutate_way_policy(strategy)

        return strategy

    def _mutate_way_policy(self, strategy: BaseStrategy) -> None:
        """Mutate way_policy in place.

        Only meaningful when the board has Ways. Skipped otherwise so the
        mutator can't grow way_policy on boards where the rules can never fire."""
        if getattr(strategy, "way_policy", None) is None:
            strategy.way_policy = []

        if self._kingdom_ways and self._kingdom_action_cards:
            # Condition tweaks on existing way rules (drop / replace / add fresh)
            for rule in strategy.way_policy:
                if random.random() < self.mutation_rate and random.random() < 0.3:
                    if rule.condition is None:
                        rule.condition = self._random_condition_with_compound()
                    else:
                        if random.random() < 0.5:
                            rule.condition = None
                        else:
                            rule.condition = self._random_condition_with_compound()

            # Insert: try a fresh (card, way) rule
            if random.random() < self.mutation_rate:
                new_rule = self._random_way_rule()
                if new_rule is not None:
                    pos = random.randint(0, len(strategy.way_policy))
                    strategy.way_policy.insert(pos, new_rule)

            # Reorder: swap two adjacent rules
            if random.random() < self.mutation_rate and len(strategy.way_policy) >= 2:
                i = random.randint(0, len(strategy.way_policy) - 2)
                strategy.way_policy[i], strategy.way_policy[i + 1] = (
                    strategy.way_policy[i + 1],
                    strategy.way_policy[i],
                )

            # Retarget: change the way_name on an existing rule
            if random.random() < self.mutation_rate * 0.5 and strategy.way_policy:
                rule = random.choice(strategy.way_policy)
                rule.way_name = random.choice(self._kingdom_ways)

            # Remove a rule occasionally to keep the genome lean
            if random.random() < self.mutation_rate * 0.3 and strategy.way_policy:
                i = random.randint(0, len(strategy.way_policy) - 1)
                strategy.way_policy.pop(i)

    @staticmethod
    def _apply_fitness_sharing(
        population: list[BaseStrategy],
        raw_fitness: list[float],
        threshold: float = 0.8,
        similarity=None,
    ) -> list[float]:
        """Divide each individual's fitness by its niche count (members within
        ``threshold`` similarity, including itself). Clones lose to unique
        strategies at the same skill level.

        ``similarity`` defaults to the raw top-5 gain overlap; structured-menu
        runs pass :func:`kingdom_similarity` instead so the shared greening
        skeleton doesn't put the whole population in one niche."""
        if similarity is None:
            similarity = GeneticTrainer._strategy_similarity
        shared: list[float] = []
        for i, individual in enumerate(population):
            niche = sum(
                1 for other in population
                if similarity(individual, other) >= threshold
            )
            shared.append(raw_fitness[i] / max(1, niche))
        return shared

    @staticmethod
    def _strategy_similarity(a: BaseStrategy, b: BaseStrategy) -> float:
        """Top-5 gain card overlap as a fraction in [0, 1].
        Conditions are ignored — only card identity at the top of the buy menu matters.

        The divisor is the larger of the two effective top-rule counts (capped
        at 5), so identical small strategies (e.g. 3 rules each) still score
        1.0 instead of being artificially capped at 0.6 and dodging fitness
        sharing."""
        top_a = {r.card_name for r in a.gain_priority[:5]}
        top_b = {r.card_name for r in b.gain_priority[:5]}
        denom = max(1, min(5, max(len(top_a), len(top_b))))
        return len(top_a & top_b) / denom

    @staticmethod
    def _normalize_priority_list(rules: list[PriorityRule]) -> list[PriorityRule]:
        """Remove unreachable rules from a priority list.

        Once an unconditional rule for a card is seen, all subsequent rules
        for that card are dead code (the unconditional rule always matches first).
        """
        seen_unconditional: set[str] = set()
        result = []
        for rule in rules:
            if rule.card_name in seen_unconditional:
                continue
            if rule.condition is None:
                seen_unconditional.add(rule.card_name)
            result.append(rule)
        return result

    def _normalize(self, strategy: BaseStrategy) -> BaseStrategy:
        """Normalize all priority lists to remove unreachable rules."""
        if self.structured_genome:
            from dominion.simulation.structured_genome import normalize_menu
            normalize_menu(strategy, self._kingdom_info)
        strategy.gain_priority = self._normalize_priority_list(strategy.gain_priority)
        strategy.action_priority = self._normalize_priority_list(strategy.action_priority)
        strategy.treasure_priority = self._normalize_priority_list(strategy.treasure_priority)
        strategy.trash_priority = self._normalize_priority_list(strategy.trash_priority)
        return strategy

    def _tournament_select(self, population: list[BaseStrategy], fitness_scores: list[float]) -> BaseStrategy:
        """Select a strategy using tournament selection"""
        tournament_size = min(3, len(population))
        tournament_indices = random.sample(range(len(population)), tournament_size)
        winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return deepcopy(population[winner_idx])

    def create_next_generation(
        self,
        population: list[BaseStrategy],
        fitness_scores: list[float],
        selection_fitness: list[float] | None = None,
        immigrant_count: int = 0,
    ) -> list[BaseStrategy]:
        """Create the next generation through elitism, random immigrants, and
        crossover+mutation of selected parents.

        ``fitness_scores`` (raw) is used for elitism so the actual best individual
        always survives. ``selection_fitness`` (defaults to ``fitness_scores``)
        drives tournament selection — pass shared fitness here for diversity
        pressure. ``immigrant_count`` reserves that many slots for fresh
        randomly-generated strategies (genetic-drift breaker)."""
        if selection_fitness is None:
            selection_fitness = fitness_scores

        new_population: list[BaseStrategy] = []

        # Elite by raw fitness
        best_idx = fitness_scores.index(max(fitness_scores))
        new_population.append(deepcopy(population[best_idx]))

        # Random immigrants (capped to leave room for elite)
        immigrants = max(0, min(immigrant_count, self.population_size - 1))
        for _ in range(immigrants):
            new_population.append(self.create_random_strategy())

        # Prune dead rules from non-elite parents after a warmup period.
        # Skipping the warmup avoids prematurely shrinking genomes before
        # the population has had a chance to exercise conditional rules
        # across varied game states.
        pruning_active = (
            self.rule_pruning
            and self.current_generation >= self.prune_warmup_generations
        )

        # Fill remaining slots via tournament selection + crossover + mutation
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(population, selection_fitness)
            parent2 = self._tournament_select(population, selection_fitness)

            if pruning_active:
                from dominion.strategy.rule_pruning import prune_unfired_rules
                prune_unfired_rules(parent1, min_rules=self.prune_min_rules)
                prune_unfired_rules(parent2, min_rules=self.prune_min_rules)

            child = self._crossover(parent1, parent2)
            child = self._mutate(child)
            child = self._normalize(child)
            child.name = f"gen{self.current_generation}-{id(child)}"

            new_population.append(child)

        return new_population

    def train(self) -> Tuple[Optional[BaseStrategy], dict]:
        """Run the genetic algorithm training process"""
        try:
            log.info("Initializing population...")
            population = [self.create_random_strategy() for _ in range(self.population_size)]

            # Inject existing strategies if provided. Each seed gets one exact
            # copy and, when there is room, one mutated neighbor so evolution
            # starts near proven ideas without collapsing the whole population
            # into clones.
            if self._strategies_to_inject:
                injected: list[BaseStrategy] = []
                for strategy in self._strategies_to_inject:
                    injected.append(deepcopy(strategy))
                    variant = self._mutate(deepcopy(strategy))
                    variant = self._normalize(variant)
                    variant.name = f"seed-variant-{id(variant)}"
                    injected.append(variant)

                slot_count = min(len(population), len(injected))
                for slot, strategy in zip(
                    random.sample(range(len(population)), slot_count),
                    injected[:slot_count],
                ):
                    population[slot] = strategy
                self._strategies_to_inject = []

            # Reset champion bookkeeping so a second train() call on the same
            # trainer can't leak state (strategy, fitness, breakdown, hall of
            # fame) from the previous run. Shaped fitness can be negative, so
            # seed the confirmed fitness below any possible value.
            self._best_strategy = None
            self._best_confirmed = float("-inf")
            self._best_win_rate = 0.0
            self.best_eval_breakdown = []
            self.hall_of_fame = []

            # Start training progress tracking
            self.logger.start_training(self.generations)

            for gen in range(self.generations):
                self.current_generation = gen
                log.info("Generation %d/%d", gen + 1, self.generations)

                # Strip dead rules so mutation/crossover the next generation
                # operate on lean genomes. Behavior-preserving.
                if self.simplify_genomes:
                    from dominion.strategy.genome_simplification import (
                        simplify_strategy,
                    )
                    population = [simplify_strategy(s) for s in population]

                # --- Screen: every individual gets the cheap budget. With
                # common random numbers, the whole generation plays the same
                # seeded shuffles so comparisons cancel deck luck.
                if self.common_random_numbers:
                    self._eval_seed_context = (_SEED_PHASE_SCREEN, gen)
                fitness_scores = []
                try:
                    for strategy in population:
                        fitness = self.evaluate_strategy(strategy)
                        fitness_scores.append(fitness)

                        if not self.racing and fitness > self._best_confirmed:
                            # Legacy mode: champion = best single eval ever
                            # seen. Kept behind racing=False for comparison;
                            # subject to the winner's curse on noisy evals.
                            self._set_champion(strategy, fitness, self.last_eval_breakdown)
                            log.info("New best fitness: %.2f", fitness)
                            if len(self.last_eval_breakdown) > 1:
                                parts = ", ".join(
                                    f"{entry[0]}: {entry[1]:.1f}%"
                                    for entry in self.last_eval_breakdown
                                )
                                log.info("  panel breakdown — %s", parts)
                finally:
                    self._eval_seed_context = None

                # --- Refine: re-evaluate the top slice with a bigger budget so
                # elitism and the challenger pick aren't decided by screening
                # noise. The refined estimate pools screen + refine games.
                refined_indices: list[int] = []
                if self.racing and self.refine_games > 0 and len(population) > 1:
                    top_k = max(1, int(round(len(population) * self.race_top_fraction)))
                    ranked = sorted(
                        range(len(population)),
                        key=lambda idx: fitness_scores[idx],
                        reverse=True,
                    )
                    for idx in ranked[:top_k]:
                        if fitness_scores[idx] == float("-inf"):
                            continue
                        extra = self._eval_with_budget(
                            population[idx], self.refine_games, (_SEED_PHASE_REFINE, gen)
                        )
                        if extra == float("-inf"):
                            fitness_scores[idx] = extra
                            continue
                        total_games = self.games_per_eval + self.refine_games
                        fitness_scores[idx] = (
                            fitness_scores[idx] * self.games_per_eval + extra * self.refine_games
                        ) / total_games
                        refined_indices.append(idx)

                # --- Confirm: the generation's best challenges the incumbent
                # champion on a shared block of confirmation games. When a
                # refine pass ran, the challenger is picked among the refined
                # candidates only — a refined (more accurate, lower) estimate
                # must not be compared against unrefined screens, whose max is
                # inflated by noise.
                if self.racing and fitness_scores:
                    challenger_pool = refined_indices or range(len(population))
                    gen_best_idx = max(
                        challenger_pool, key=lambda idx: fitness_scores[idx]
                    )
                    if fitness_scores[gen_best_idx] != float("-inf"):
                        self._consider_challenger(
                            population[gen_best_idx], fitness_scores[gen_best_idx], gen
                        )

                # --- Hall of fame: periodically promote the champion into the
                # opponent panel so the fitness gradient doesn't saturate once
                # the population beats the static baselines.
                if (
                    self.hall_of_fame_size > 0
                    and self._best_strategy is not None
                    and (gen + 1) % self.hall_of_fame_interval == 0
                    and gen + 1 < self.generations
                ):
                    self._update_hall_of_fame(gen)

                # Calculate generation statistics
                avg_fitness = sum(fitness_scores) / len(fitness_scores)

                # Update progress
                self.logger.update_training(gen, self._best_confirmed, avg_fitness)

                # Diversity pressure: shared fitness for selection, random immigrants
                similarity = None
                if self.structured_genome:
                    from dominion.simulation.structured_genome import kingdom_similarity
                    similarity = kingdom_similarity
                shared_fitness = self._apply_fitness_sharing(
                    population, fitness_scores, threshold=self.sharing_threshold,
                    similarity=similarity,
                )
                if self.population_size < 4 or self.immigrant_fraction <= 0:
                    immigrants = 0
                else:
                    immigrants = max(1, int(self.population_size * self.immigrant_fraction))

                population = self.create_next_generation(
                    population,
                    fitness_scores,
                    selection_fitness=shared_fitness,
                    immigrant_count=immigrants,
                )

            # End training progress tracking
            self.logger.end_training()

            # If no candidate was ever evaluated (e.g. empty population),
            # surface the shaped fitness as -inf-equivalent 0.0 so callers
            # don't see a sentinel value.
            reported_fitness = self._best_confirmed if self._best_strategy is not None else 0.0

            metrics = {
                "win_rate": self._best_win_rate,
                "fitness": reported_fitness,
                "generations": self.generations,
                "final_generation": self.generations,
            }

            return self._best_strategy, metrics

        except Exception as exc:
            log.exception("Error during training")
            return None, {"error": str(exc)}

    def inject_strategy(self, strategy: BaseStrategy):
        """Inject an existing strategy into the initial population.
        This should be called before train() is called."""
        self._strategies_to_inject.append(strategy)

    def inject_strategies(self, strategies: list[BaseStrategy]):
        """Inject multiple existing strategies into the initial population."""
        self._strategies_to_inject.extend(strategies)
