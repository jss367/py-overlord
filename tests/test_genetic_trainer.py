import importlib
import types
from pathlib import Path

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def make_stub_strategy() -> BaseStrategy:
    strategy = BaseStrategy()
    strategy.name = "Stub"
    strategy.gain_priority = [PriorityRule("Province")]
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return strategy


def test_evaluate_strategy_counts_second_seat_wins(monkeypatch):
    # shape_rewards=False to keep this asserting raw win-rate behavior.
    trainer = GeneticTrainer(
        ["Village"], population_size=1, generations=1, games_per_eval=2,
        shape_rewards=False,
    )

    # Provide a deterministic strategy under test
    strategy = make_stub_strategy()

    call_counter = types.SimpleNamespace(count=0)

    def fake_run_game(first_ai, second_ai, kingdom):
        call_counter.count += 1
        # Big Money (second_ai in the first call) wins when our strategy leads.
        # Our strategy (second_ai in the second call) wins when going second.
        # Provide minimal scores so reward shaping (when on) has data.
        scores = {first_ai.name: 0, second_ai.name: 1}
        return second_ai, scores, None, 0

    monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)

    win_rate = trainer.evaluate_strategy(strategy)

    assert call_counter.count == 2
    assert win_rate == 50.0


# ---------------------------------------------------------------------------
# New tests: condition generation, evaluation, and serialization
# ---------------------------------------------------------------------------


def _make_mock_state(turn_number=5, provinces_left=8, empty_piles=0, players=None):
    """Create a lightweight mock GameState."""
    state = types.SimpleNamespace()
    state.turn_number = turn_number
    state.supply = {"Province": provinces_left}
    state.empty_piles = empty_piles
    state.players = players if players is not None else []
    return state


def _make_mock_player(coins=3, actions=1, buys=1, vp=3, all_cards=None):
    """Create a lightweight mock PlayerState."""
    player = types.SimpleNamespace()
    player.coins = coins
    player.actions = actions
    player.buys = buys
    player.hand = []
    player.count_in_deck = lambda card_name: {"Silver": 2, "Gold": 1}.get(card_name, 0)
    cards = all_cards if all_cards is not None else []
    player.all_cards = lambda _cards=cards: list(_cards)
    player.get_victory_points = lambda _g=None, _vp=vp: _vp
    return player


class TestConditionsAreCallable:
    """Verify that create_random_strategy produces callable (not string) conditions."""

    def test_gain_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village", "Smithy"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.gain_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Gain condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )

    def test_action_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village", "Smithy", "Laboratory"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.action_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Action condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )

    def test_trash_conditions_are_callable_or_none(self):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1)
        strategy = trainer.create_random_strategy()

        for rule in strategy.trash_priority:
            assert rule.condition is None or callable(rule.condition), (
                f"Trash condition for {rule.card_name} is {type(rule.condition)}, expected callable or None"
            )


class TestConditionsEvaluate:
    """Verify that conditions actually produce boolean results when called."""

    def test_provinces_left(self):
        cond = PriorityRule.provinces_left("<=", 4)
        state = _make_mock_state(provinces_left=3)
        player = _make_mock_player()
        assert cond(state, player) is True

        state2 = _make_mock_state(provinces_left=6)
        assert cond(state2, player) is False

    def test_turn_number(self):
        cond = PriorityRule.turn_number(">=", 5)
        assert cond(_make_mock_state(turn_number=5), _make_mock_player()) is True
        assert cond(_make_mock_state(turn_number=3), _make_mock_player()) is False

    def test_resources(self):
        cond = PriorityRule.resources("coins", ">=", 6)
        assert cond(_make_mock_state(), _make_mock_player(coins=8)) is True
        assert cond(_make_mock_state(), _make_mock_player(coins=3)) is False

    def test_has_cards(self):
        cond = PriorityRule.has_cards(["Silver", "Gold"], 3)
        player = _make_mock_player()  # Silver=2, Gold=1 → total 3
        assert cond(_make_mock_state(), player) is True

        cond2 = PriorityRule.has_cards(["Silver", "Gold"], 5)
        assert cond2(_make_mock_state(), player) is False

    def test_random_strategy_conditions_evaluate(self):
        """Every callable condition on a random strategy should evaluate without error."""
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1,
        )
        strategy = trainer.create_random_strategy()
        state = _make_mock_state()
        player = _make_mock_player()

        for rule_list in [strategy.gain_priority, strategy.action_priority, strategy.trash_priority]:
            for rule in rule_list:
                if rule.condition is not None:
                    result = rule.condition(state, player)
                    assert isinstance(result, bool), (
                        f"Condition for {rule.card_name} returned {type(result)}, expected bool"
                    )


class TestNewPrimitives:
    """Verify the new condition primitives evaluate correctly and tag _source."""

    def test_empty_piles_evaluates(self):
        cond = PriorityRule.empty_piles(">=", 2)
        assert cond(_make_mock_state(empty_piles=3), _make_mock_player()) is True
        assert cond(_make_mock_state(empty_piles=1), _make_mock_player()) is False

    def test_empty_piles_source(self):
        cond = PriorityRule.empty_piles(">=", 2)
        assert cond._source == "PriorityRule.empty_piles('>=', 2)"

    def test_deck_size_evaluates(self):
        # all_cards returns a list whose length is the deck size
        player = _make_mock_player(all_cards=[1, 2, 3, 4, 5])
        cond = PriorityRule.deck_size(">=", 5)
        assert cond(_make_mock_state(), player) is True
        cond_lt = PriorityRule.deck_size("<", 3)
        assert cond_lt(_make_mock_state(), player) is False

    def test_deck_size_source(self):
        cond = PriorityRule.deck_size(">", 10)
        assert cond._source == "PriorityRule.deck_size('>', 10)"

    def test_action_density_evaluates(self):
        # 2 of 4 cards are actions → density 50%
        action_card = types.SimpleNamespace(is_action=True)
        treasure_card = types.SimpleNamespace(is_action=False)
        deck = [action_card, action_card, treasure_card, treasure_card]
        player = _make_mock_player(all_cards=deck)

        cond_high = PriorityRule.action_density(">=", 50)
        assert cond_high(_make_mock_state(), player) is True
        cond_low = PriorityRule.action_density(">=", 75)
        assert cond_low(_make_mock_state(), player) is False

    def test_action_density_empty_deck_safe(self):
        """Empty deck must not divide by zero — treat density as 0."""
        cond = PriorityRule.action_density(">=", 1)
        empty_player = _make_mock_player(all_cards=[])
        # 0% density should be < 1, so >=1 is False
        assert cond(_make_mock_state(), empty_player) is False

    def test_action_density_source(self):
        cond = PriorityRule.action_density(">=", 40)
        assert cond._source == "PriorityRule.action_density('>=', 40)"

    def test_score_diff_evaluates(self):
        # My VP=10, opponent VP=4 → diff +6
        me = _make_mock_player(vp=10)
        opp = _make_mock_player(vp=4)
        state = _make_mock_state(players=[me, opp])
        cond_winning = PriorityRule.score_diff(">=", 5)
        assert cond_winning(state, me) is True
        cond_blowout = PriorityRule.score_diff(">=", 10)
        assert cond_blowout(state, me) is False

    def test_score_diff_when_losing(self):
        me = _make_mock_player(vp=2)
        opp = _make_mock_player(vp=8)
        state = _make_mock_state(players=[me, opp])
        cond = PriorityRule.score_diff("<=", -3)
        assert cond(state, me) is True

    def test_score_diff_source(self):
        cond = PriorityRule.score_diff(">=", 6)
        assert cond._source == "PriorityRule.score_diff('>=', 6)"


class TestRandomConditionVocabulary:
    """The genetic trainer's _random_condition should draw from the full primitive set,
    not just the original 4 kinds (provinces_left/turn_number/resources/has_cards)."""

    def test_random_condition_includes_new_primitives(self):
        """Sampling 400 conditions should produce at least one of each new primitive."""
        random_local = __import__("random")
        random_local.seed(0)
        trainer = GeneticTrainer(["Village", "Smithy", "Market"], population_size=1, generations=1)
        sources: set[str] = set()
        for _ in range(400):
            cond = trainer._random_condition()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            # Tag by primitive name (everything before the first '(')
            sources.add(src.split("(")[0])

        expected = {
            "PriorityRule.empty_piles",
            "PriorityRule.deck_size",
            "PriorityRule.action_density",
            "PriorityRule.score_diff",
            "PriorityRule.actions_in_play",
            "PriorityRule.max_in_deck",
        }
        missing = expected - sources
        assert not missing, f"Random vocabulary missing: {missing}. Got: {sources}"

    def test_random_condition_includes_cauldron_primitives(self):
        """Sampling many conditions should produce card_in_play, actions_gained_this_turn,
        and cards_gained_this_turn — the new vocabulary needed for Cauldron-style triggers."""
        random_local = __import__("random")
        random_local.seed(1)
        trainer = GeneticTrainer(["Village", "Smithy", "Market"], population_size=1, generations=1)
        sources: set[str] = set()
        for _ in range(800):
            cond = trainer._random_condition()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            sources.add(src.split("(")[0])

        expected = {
            "PriorityRule.card_in_play",
            "PriorityRule.actions_gained_this_turn",
            "PriorityRule.cards_gained_this_turn",
        }
        missing = expected - sources
        assert not missing, f"Cauldron vocabulary missing: {missing}. Got: {sources}"

    def test_random_condition_card_in_play_uses_kingdom_action(self):
        """When _random_condition returns card_in_play it must reference one of the
        kingdom action cards, not a hard-coded card name."""
        random_local = __import__("random")
        random_local.seed(2)
        kingdom = ["Village", "Smithy", "Market"]
        trainer = GeneticTrainer(kingdom, population_size=1, generations=1)
        seen_cards: set[str] = set()
        for _ in range(800):
            cond = trainer._random_condition()
            if cond is None:
                continue
            src = getattr(cond, "_source", "")
            if not src.startswith("PriorityRule.card_in_play("):
                continue
            # Extract the card name from the source string
            inner = src[len("PriorityRule.card_in_play("):-1]
            # inner is repr-form, e.g. "'Village'" — strip surrounding quotes
            card_name = inner.strip().strip("'").strip('"')
            seen_cards.add(card_name)

        assert seen_cards, "card_in_play was never sampled"
        # Every sampled card must be a real kingdom action card
        assert seen_cards <= set(kingdom), (
            f"card_in_play sampled non-kingdom names: {seen_cards - set(kingdom)}"
        )


class TestSourceAttribute:
    """Verify that PriorityRule helpers tag lambdas with _source."""

    def test_provinces_left_source(self):
        cond = PriorityRule.provinces_left("<=", 4)
        assert hasattr(cond, "_source")
        assert cond._source == "PriorityRule.provinces_left('<=', 4)"

    def test_turn_number_source(self):
        cond = PriorityRule.turn_number(">=", 10)
        assert cond._source == "PriorityRule.turn_number('>=', 10)"

    def test_resources_source(self):
        cond = PriorityRule.resources("coins", ">=", 6)
        assert cond._source == "PriorityRule.resources('coins', '>=', 6)"

    def test_has_cards_source(self):
        cond = PriorityRule.has_cards(["Silver", "Gold"], 3)
        assert cond._source == "PriorityRule.has_cards(['Silver', 'Gold'], 3)"

    def test_always_true_source(self):
        cond = PriorityRule.always_true()
        assert cond._source == "PriorityRule.always_true()"

    def test_and_source(self):
        cond = PriorityRule.and_(
            PriorityRule.provinces_left("<=", 4),
            PriorityRule.resources("coins", ">=", 6),
        )
        assert "PriorityRule.and_(" in cond._source
        assert "PriorityRule.provinces_left" in cond._source
        assert "PriorityRule.resources" in cond._source


class TestSerialization:
    """Verify that save_strategy_as_python produces importable Python."""

    def test_round_trip(self, tmp_path):
        """Write a strategy, import it, and verify conditions still work."""
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "TestRoundTrip"
        strategy.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver", PriorityRule.turn_number("<", 10)),
        ]
        strategy.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]
        strategy.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold"], 3)),
        ]

        out_file = tmp_path / "test_strategy.py"
        save_strategy_as_python(strategy, out_file, "TestStrategy")

        # Read the generated source and verify it contains no '<lambda>' or '<function'
        source = out_file.read_text()
        assert "<lambda" not in source, f"Source contains raw lambda repr:\n{source}"
        assert "<function" not in source, f"Source contains raw function repr:\n{source}"

        # The file should contain PriorityRule.resources etc.
        assert "PriorityRule.resources" in source
        assert "PriorityRule.provinces_left" in source

        # Import the generated module and verify it works
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("test_strategy")
            generated = mod.TestStrategy()
            assert generated.name == "TestRoundTrip"
            assert len(generated.gain_priority) == 4

            # Verify the conditions are callable and evaluate
            state = _make_mock_state()
            player = _make_mock_player(coins=8)
            province_rule = generated.gain_priority[0]
            assert province_rule.condition is not None
            assert callable(province_rule.condition)
            assert province_rule.condition(state, player) is True
        finally:
            sys.path.pop(0)
            sys.modules.pop("test_strategy", None)

    def test_none_conditions_serialize_cleanly(self, tmp_path):
        """Rules without conditions should not emit broken repr."""
        from runner import save_strategy_as_python

        strategy = BaseStrategy()
        strategy.name = "NoConditions"
        strategy.gain_priority = [PriorityRule("Province"), PriorityRule("Gold")]
        strategy.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        out_file = tmp_path / "no_cond_strategy.py"
        save_strategy_as_python(strategy, out_file, "NoCondStrategy")

        source = out_file.read_text()
        assert "<lambda" not in source
        assert "<function" not in source

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            mod = importlib.import_module("no_cond_strategy")
            generated = mod.NoCondStrategy()
            assert len(generated.gain_priority) == 2
            assert generated.gain_priority[0].condition is None
        finally:
            sys.path.pop(0)
            sys.modules.pop("no_cond_strategy", None)


def _make_dummy_opponent(name: str) -> BaseStrategy:
    opp = BaseStrategy()
    opp.name = name
    opp.gain_priority = [PriorityRule("Province")]
    opp.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return opp


class TestPanelEvaluation:
    """Verify panel-based fitness: split games across multiple opponents."""

    def test_panel_evaluation_distributes_games_across_opponents(self, monkeypatch):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=4, shape_rewards=False)
        strategy = make_stub_strategy()

        opp_a = _make_dummy_opponent("OpponentA")
        opp_b = _make_dummy_opponent("OpponentB")
        trainer.set_baseline_panel([opp_a, opp_b])

        games_against = {"OpponentA": 0, "OpponentB": 0}

        def fake_run_game(first_ai, second_ai, kingdom):
            for ai in (first_ai, second_ai):
                if ai.strategy.name in games_against:
                    games_against[ai.strategy.name] += 1
            return first_ai, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
        trainer.evaluate_strategy(strategy)

        assert games_against["OpponentA"] == 2, games_against
        assert games_against["OpponentB"] == 2, games_against

    def test_panel_fitness_is_mean_of_per_opponent_rates(self, monkeypatch):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=4, shape_rewards=False)
        strategy = make_stub_strategy()
        strategy.name = "Stub"

        opp_a = _make_dummy_opponent("AlwaysLose")
        opp_b = _make_dummy_opponent("AlwaysWin")
        trainer.set_baseline_panel([opp_a, opp_b])

        def fake_run_game(first_ai, second_ai, kingdom):
            # Stub beats AlwaysLose in every game, loses to AlwaysWin in every game
            names = (first_ai.strategy.name, second_ai.strategy.name)
            if "AlwaysLose" in names:
                winner = first_ai if first_ai.strategy.name == "Stub" else second_ai
            else:  # AlwaysWin matchup
                winner = first_ai if first_ai.strategy.name == "AlwaysWin" else second_ai
            return winner, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)

        fitness = trainer.evaluate_strategy(strategy)
        # 100% vs AlwaysLose, 0% vs AlwaysWin → mean 50%
        assert fitness == 50.0, f"Expected 50.0, got {fitness}"

    def test_panel_evaluation_uses_full_games_budget(self, monkeypatch):
        """games_per_eval=10 with 3 opponents should run exactly 10 total games
        (distributed 4+3+3), not 9 from floor division."""
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=10, shape_rewards=False)
        strategy = make_stub_strategy()

        opp_a = _make_dummy_opponent("A")
        opp_b = _make_dummy_opponent("B")
        opp_c = _make_dummy_opponent("C")
        trainer.set_baseline_panel([opp_a, opp_b, opp_c])

        games = {"A": 0, "B": 0, "C": 0}

        def fake_run_game(first_ai, second_ai, kingdom):
            for ai in (first_ai, second_ai):
                if ai.strategy.name in games:
                    games[ai.strategy.name] += 1
            return first_ai, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
        trainer.evaluate_strategy(strategy)

        assert sum(games.values()) == 10, f"Expected 10 total games, got {sum(games.values())}: {games}"
        # Every opponent gets at least floor(10/3)=3 games
        for n in games.values():
            assert n in (3, 4), f"Each opponent should get 3 or 4 games, got {n}"

    def test_panel_with_duplicate_opponent_names_preserves_all_rates(self, monkeypatch):
        """Two panel members sharing a name (e.g. both BigMoneySmithy variants)
        must both contribute to the breakdown — a dict keyed by name silently
        loses one of them."""
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=4, shape_rewards=False)
        strategy = make_stub_strategy()
        strategy.name = "Stub"

        opp_a1 = _make_dummy_opponent("Twin")
        opp_a2 = _make_dummy_opponent("Twin")
        trainer.set_baseline_panel([opp_a1, opp_a2])

        # opp_a1 always loses to Stub, opp_a2 always beats Stub
        def fake_run_game(first_ai, second_ai, kingdom):
            for ai in (first_ai, second_ai):
                if ai.strategy is opp_a1:
                    winner = first_ai if first_ai.strategy.name == "Stub" else second_ai
                    return winner, {}, None, 0
                if ai.strategy is opp_a2:
                    winner = first_ai if first_ai.strategy is opp_a2 else second_ai
                    return winner, {}, None, 0
            return first_ai, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
        trainer.evaluate_strategy(strategy)

        breakdown = trainer.last_eval_breakdown
        assert len(breakdown) == 2, (
            f"Expected 2 entries (one per panel member), got {len(breakdown)}: {breakdown}"
        )

    def test_panel_per_opponent_breakdown_is_exposed(self, monkeypatch):
        trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=4, shape_rewards=False)
        strategy = make_stub_strategy()
        strategy.name = "Stub"

        opp_a = _make_dummy_opponent("AlwaysLose")
        opp_b = _make_dummy_opponent("AlwaysWin")
        trainer.set_baseline_panel([opp_a, opp_b])

        def fake_run_game(first_ai, second_ai, kingdom):
            names = (first_ai.strategy.name, second_ai.strategy.name)
            if "AlwaysLose" in names:
                winner = first_ai if first_ai.strategy.name == "Stub" else second_ai
            else:
                winner = first_ai if first_ai.strategy.name == "AlwaysWin" else second_ai
            return winner, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)
        trainer.evaluate_strategy(strategy)

        breakdown = trainer.last_eval_breakdown
        assert breakdown == [("AlwaysLose", 100.0), ("AlwaysWin", 0.0)], breakdown


def _strategy_with_gain(*card_names: str) -> BaseStrategy:
    s = BaseStrategy()
    s.name = "tmp"
    s.gain_priority = [PriorityRule(c) for c in card_names]
    s.action_priority = []
    s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]
    s.trash_priority = []
    return s


class TestStrategySimilarity:
    """Top-5 gain similarity: intersection of first-5 card names / 5."""

    def test_identical_top_five_is_1(self):
        s1 = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate", "Copper")
        s2 = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate", "Duchy")
        assert GeneticTrainer._strategy_similarity(s1, s2) == 1.0

    def test_disjoint_top_five_is_0(self):
        s1 = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate")
        s2 = _strategy_with_gain("Duchy", "Copper", "Curse", "Festival", "Mine")
        assert GeneticTrainer._strategy_similarity(s1, s2) == 0.0

    def test_partial_overlap(self):
        s1 = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate")
        s2 = _strategy_with_gain("Province", "Gold", "Festival", "Mine", "Duchy")
        # Intersection: {Province, Gold} → 2/5 = 0.4
        assert GeneticTrainer._strategy_similarity(s1, s2) == 0.4

    def test_short_lists_padded_safely(self):
        s1 = _strategy_with_gain("Province", "Gold")  # only 2 cards
        s2 = _strategy_with_gain("Province", "Gold", "Silver", "Witch", "Estate")
        # Intersection of first-5: {Province, Gold} → 2/5 = 0.4
        assert GeneticTrainer._strategy_similarity(s1, s2) == 0.4

    def test_short_identical_strategies_get_similarity_one(self):
        """A 3-rule strategy compared to itself must score 1.0, otherwise
        identical small strategies dodge fitness sharing (0.6 < 0.8 threshold)."""
        s1 = _strategy_with_gain("Province", "Gold", "Witch")
        s2 = _strategy_with_gain("Province", "Gold", "Witch")
        sim = GeneticTrainer._strategy_similarity(s1, s2)
        assert sim == 1.0, f"Identical 3-rule strategies should be 1.0, got {sim}"

    def test_only_card_name_matters_not_condition(self):
        """Conditions don't affect similarity."""
        s1 = BaseStrategy()
        s1.gain_priority = [PriorityRule("Province", PriorityRule.provinces_left("<=", 4)), PriorityRule("Gold")]
        s2 = BaseStrategy()
        s2.gain_priority = [PriorityRule("Province"), PriorityRule("Gold", PriorityRule.turn_number(">=", 10))]
        assert GeneticTrainer._strategy_similarity(s1, s2) == GeneticTrainer._strategy_similarity(s2, s1)


class TestCreateNextGenerationElitism:
    """Elitism uses raw fitness; selection uses (optional) selection_fitness."""

    def test_elite_picked_by_raw_fitness_when_selection_fitness_differs(self):
        trainer = GeneticTrainer(["Village"], population_size=3, generations=1, mutation_rate=0.0)
        clone_a = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate")
        clone_b = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate")
        unique = _strategy_with_gain("Festival", "Mine", "Curse", "Duchy", "Copper")
        # Treasure pri must be present for crossover (which copies from parents)
        for s in (clone_a, clone_b, unique):
            s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Silver"), PriorityRule("Copper")]

        pop = [clone_a, clone_b, unique]
        raw = [80.0, 80.0, 70.0]
        shared = [40.0, 40.0, 70.0]

        next_pop = trainer.create_next_generation(pop, raw, selection_fitness=shared)

        # Elite is one of the clones (raw fitness 80)
        assert next_pop[0].gain_priority[0].card_name == "Province"


class TestImmigrantFractionZeroIsHonored:
    """immigrant_fraction=0 must produce 0 immigrants — currently the
    max(1, ...) floor silently overrides this."""

    def test_zero_immigrant_fraction_passes_zero_to_next_gen(self, monkeypatch):
        trainer = GeneticTrainer(
            ["Village"],
            population_size=8,
            generations=1,
            games_per_eval=2,
            immigrant_fraction=0.0,
        )
        monkeypatch.setattr(trainer, "evaluate_strategy", lambda s: 50.0)

        captured: dict = {}
        original = trainer.create_next_generation

        def spy(pop, raw, **kwargs):
            captured["immigrants"] = kwargs.get("immigrant_count", 0)
            return original(pop, raw, **kwargs)

        monkeypatch.setattr(trainer, "create_next_generation", spy)
        trainer.train()

        assert captured["immigrants"] == 0, (
            f"immigrant_fraction=0 should yield 0 immigrants, got {captured['immigrants']}"
        )


class TestTrainWiresDiversityPressure:
    """train() should pass selection_fitness (sharing-adjusted) and a non-zero
    immigrant_count to create_next_generation."""

    def test_train_passes_shared_fitness_and_immigrants(self, monkeypatch):
        trainer = GeneticTrainer(["Village"], population_size=8, generations=1, games_per_eval=2)
        monkeypatch.setattr(trainer, "evaluate_strategy", lambda s: 50.0)

        captured: dict = {}
        original = trainer.create_next_generation

        def spy(pop, raw, **kwargs):
            captured["selection"] = kwargs.get("selection_fitness")
            captured["immigrants"] = kwargs.get("immigrant_count", 0)
            return original(pop, raw, **kwargs)

        monkeypatch.setattr(trainer, "create_next_generation", spy)

        trainer.train()

        assert captured.get("selection") is not None, "selection_fitness must be passed"
        assert captured["immigrants"] >= 1, (
            f"immigrant_count should be >= 1 for population_size=8, got {captured['immigrants']}"
        )


class TestRandomImmigrants:
    """create_next_generation with immigrant_count > 0 should reserve slots for
    fresh randomly-generated strategies, not just crossover children."""

    def test_immigrants_replace_no_elite_slot(self):
        # Population of 4 identical clones. With immigrant_count=2 and elite=1,
        # only 1 slot is filled by crossover (which would clone). The 2
        # immigrant slots must contain genuinely different strategies.
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Festival", "Laboratory", "Witch"],
            population_size=4, generations=1, mutation_rate=0.0,
        )
        clone = _strategy_with_gain("Province", "Gold", "Witch", "Silver", "Estate")
        clone.action_priority = []
        clone.trash_priority = []
        pop = [_deepcopy_strategy(clone) for _ in range(4)]
        raw = [50.0, 50.0, 50.0, 50.0]

        next_pop = trainer.create_next_generation(pop, raw, immigrant_count=2)

        # At least 2 of the 4 should have a top-5 different from the clone
        # (immigrants are randomly generated)
        clone_top5 = {r.card_name for r in clone.gain_priority[:5]}
        differing = sum(
            1 for s in next_pop
            if {r.card_name for r in s.gain_priority[:5]} != clone_top5
        )
        assert differing >= 2, (
            f"Expected at least 2 immigrants with differing top-5; got {differing}"
        )


def _deepcopy_strategy(s: BaseStrategy) -> BaseStrategy:
    from copy import deepcopy as _dc
    out = _dc(s)
    return out


class TestFitnessSharing:
    """Niche-based fitness sharing: clones share their fitness so unique strategies
    get a selection edge at equal raw fitness."""

    def test_clones_share_fitness_unique_keeps_full(self):
        pop = [
            _strategy_with_gain("A", "B", "C", "D", "E"),
            _strategy_with_gain("A", "B", "C", "D", "E"),
            _strategy_with_gain("A", "B", "C", "D", "E"),
            _strategy_with_gain("X", "Y", "Z", "W", "V"),
        ]
        raw = [60.0, 60.0, 60.0, 60.0]
        shared = GeneticTrainer._apply_fitness_sharing(pop, raw, threshold=0.8)
        assert shared[0] == 20.0  # 60 / 3 clones
        assert shared[1] == 20.0
        assert shared[2] == 20.0
        assert shared[3] == 60.0  # alone in its niche

    def test_no_clones_returns_unchanged(self):
        pop = [
            _strategy_with_gain("A", "B", "C", "D", "E"),
            _strategy_with_gain("V", "W", "X", "Y", "Z"),
        ]
        raw = [40.0, 70.0]
        shared = GeneticTrainer._apply_fitness_sharing(pop, raw, threshold=0.8)
        assert shared == [40.0, 70.0]


class TestMutationReplacesConditions:
    """An existing condition can mutate into a *different* condition,
    not just toggle between itself and None."""

    def test_mutation_can_replace_existing_condition_with_different_one(self):
        from copy import deepcopy as _deepcopy
        trainer = GeneticTrainer(["Village", "Smithy"], population_size=1, generations=1, mutation_rate=1.0)

        strategy = BaseStrategy()
        strategy.name = "X"
        initial_cond = PriorityRule.provinces_left("<=", 4)
        initial_source = initial_cond._source
        strategy.gain_priority = [
            PriorityRule("Village"),
            PriorityRule("Province", initial_cond),
            PriorityRule("Gold"),
        ]
        strategy.action_priority = []
        strategy.treasure_priority = [PriorityRule("Gold"), PriorityRule("Copper")]
        strategy.trash_priority = []

        seen_different_condition = False
        for _ in range(80):
            mutated = trainer._mutate(_deepcopy(strategy))
            for rule in mutated.gain_priority:
                if rule.card_name == "Province" and rule.condition is not None:
                    src = getattr(rule.condition, "_source", "")
                    if src and src != initial_source:
                        seen_different_condition = True
                        break
            if seen_different_condition:
                break

        assert seen_different_condition, (
            "Mutation never replaced the existing condition with a different one"
        )


class TestMutationProducesCallableConditions:
    """Mutations should also produce callable conditions, not strings."""

    def test_mutated_conditions_are_callable(self):
        trainer = GeneticTrainer(
            ["Village", "Smithy", "Market", "Laboratory"],
            population_size=1, generations=1, mutation_rate=1.0,  # Force mutations
        )
        strategy = trainer.create_random_strategy()

        # Mutate many times to exercise all paths
        for _ in range(20):
            strategy = trainer._mutate(strategy)

        for rule_list in [strategy.gain_priority, strategy.action_priority, strategy.trash_priority]:
            for rule in rule_list:
                assert rule.condition is None or callable(rule.condition), (
                    f"After mutation, condition for {rule.card_name} is {type(rule.condition)}"
                )
