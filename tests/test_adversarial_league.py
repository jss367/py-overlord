"""Tests for the adversarial league — the maintained opponent pool.

The league exists to fix three specific properties of the hall of fame that
let the search drift:

1. mean aggregation lets a candidate farm the weakest panel member;
2. FIFO retention keeps the newest champions rather than the hardest;
3. the pool only ever held this run's own champions, never outside reference
   opponents.

Each is covered below, plus the trainer wiring that makes the pool the panel
the population actually faces.
"""

from __future__ import annotations

import pytest

from dominion.simulation.adversarial_league import (
    ORIGIN_CHAMPION,
    ORIGIN_SEED,
    AdversarialLeague,
    aggregate_fitness,
    build_seeded_league,
    genome_signature,
)
from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def _make_strategy(name: str, *gain_cards: str) -> BaseStrategy:
    s = BaseStrategy()
    s.name = name
    s.gain_priority = [PriorityRule(c) for c in (gain_cards or ("Province",))]
    s.treasure_priority = [PriorityRule("Gold"), PriorityRule("Copper")]
    return s


def _make_trainer(**kwargs) -> GeneticTrainer:
    defaults = dict(
        kingdom_cards=["Village", "Smithy"],
        population_size=4,
        generations=1,
        games_per_eval=2,
        eval_seed=1234,
    )
    defaults.update(kwargs)
    return GeneticTrainer(**defaults)


# ---------------------------------------------------------------------------
# Aggregation: worst-case pressure
# ---------------------------------------------------------------------------


class TestAggregateFitness:
    def test_zero_weight_is_the_historical_mean(self):
        assert aggregate_fitness([70.0, 40.0], worst_case_weight=0.0) == 55.0

    def test_full_weight_scores_on_the_worst_half(self):
        # Worst half of four values is the two lowest: (30 + 40) / 2.
        assert aggregate_fitness(
            [90.0, 80.0, 40.0, 30.0], worst_case_weight=1.0
        ) == pytest.approx(35.0)

    def test_blend_sits_between_mean_and_worst(self):
        values = [90.0, 80.0, 40.0, 30.0]
        mean = aggregate_fitness(values, worst_case_weight=0.0)
        worst = aggregate_fitness(values, worst_case_weight=1.0)
        blend = aggregate_fitness(values, worst_case_weight=0.5)
        assert worst < blend < mean
        assert blend == pytest.approx((mean + worst) / 2)

    def test_panel_farming_loses_to_balanced_play_under_worst_case(self):
        """The objective failure this whole module exists to fix.

        A specialist beats the weak opponent 70% and loses to the sharp one
        40%; a balanced strategy goes 55/50. Under the mean the specialist
        wins (55 vs 52.5), which is why the search drifts toward it. Under
        worst-case pressure the ordering flips.
        """

        specialist = [70.0, 40.0]
        balanced = [55.0, 50.0]

        assert aggregate_fitness(specialist, worst_case_weight=0.0) > aggregate_fitness(
            balanced, worst_case_weight=0.0
        )
        assert aggregate_fitness(specialist, worst_case_weight=1.0) < aggregate_fitness(
            balanced, worst_case_weight=1.0
        )

    def test_empty_values_are_zero(self):
        assert aggregate_fitness([], worst_case_weight=0.5) == 0.0


# ---------------------------------------------------------------------------
# Pool membership
# ---------------------------------------------------------------------------


class TestLeagueMembership:
    def test_add_returns_true_and_renames_a_copy(self):
        league = AdversarialLeague(capacity=3)
        original = _make_strategy("Champ", "Province")

        assert league.add(original, name="League-g10", origin=ORIGIN_CHAMPION) is True
        assert len(league) == 1
        assert league.members[0].name == "League-g10"
        # The pool holds a copy; renaming it must not touch the caller's object.
        assert original.name == "Champ"

    def test_structurally_identical_members_are_rejected(self):
        league = AdversarialLeague(capacity=3)
        league.add(_make_strategy("A", "Province", "Gold"), name="A", origin=ORIGIN_SEED)

        # Same rules, different name — this is the champion that re-derives a
        # member the pool already holds.
        assert (
            league.add(
                _make_strategy("B", "Province", "Gold"), name="B", origin=ORIGIN_CHAMPION
            )
            is False
        )
        assert len(league) == 1

    def test_colliding_names_are_uniquified(self):
        """Distinct members must never share a name.

        The trainer promotes its champion at a fixed generation of every
        round, so it proposes the same ``League-g10`` each time. Sharing a
        name makes :meth:`record_champion_results` assign one member's win
        rate to the other and corrupts retention — observed in the first Oslo
        league run, where two distinct members both reported 33.3%.
        """

        league = AdversarialLeague(capacity=4)
        league.add(_make_strategy("A", "Province"), name="League-g10", origin=ORIGIN_CHAMPION)
        league.add(_make_strategy("B", "Gold"), name="League-g10", origin=ORIGIN_CHAMPION)
        league.add(_make_strategy("C", "Duchy"), name="League-g10", origin=ORIGIN_CHAMPION)

        names = [m.name for m in league.members]
        assert names == ["League-g10", "League-g10 (2)", "League-g10 (3)"]
        assert len(set(names)) == len(names)
        # The pooled strategy object carries the uniquified name too, so the
        # trainer's breakdown entries match the member record.
        assert [m.strategy.name for m in league.members] == names

    def test_uniquified_members_record_their_own_results(self):
        league = AdversarialLeague(capacity=4)
        league.add(_make_strategy("A", "Province"), name="League-g10", origin=ORIGIN_CHAMPION)
        league.add(_make_strategy("B", "Gold"), name="League-g10", origin=ORIGIN_CHAMPION)

        league.record_champion_results([("League-g10", 30.0), ("League-g10 (2)", 90.0)])

        assert [m.last_champion_win_rate for m in league.members] == [30.0, 90.0]

    def test_capacity_must_be_positive(self):
        with pytest.raises(ValueError):
            AdversarialLeague(capacity=0)

    def test_genome_signature_ignores_name_but_tracks_rules(self):
        a = _make_strategy("A", "Province")
        b = _make_strategy("B", "Province")
        c = _make_strategy("C", "Duchy")
        assert genome_signature(a) == genome_signature(b)
        assert genome_signature(a) != genome_signature(c)


# ---------------------------------------------------------------------------
# Retention: hardest members survive, not newest
# ---------------------------------------------------------------------------


class TestRetention:
    def _stocked_league(self, capacity=2):
        league = AdversarialLeague(capacity=capacity)
        league.add(_make_strategy("Easy", "Copper"), name="Easy", origin=ORIGIN_SEED)
        league.add(_make_strategy("Hard", "Province"), name="Hard", origin=ORIGIN_SEED)
        league.add(_make_strategy("Mid", "Duchy"), name="Mid", origin=ORIGIN_SEED)
        return league

    def test_record_champion_results_matches_by_name(self):
        league = self._stocked_league()
        league.record_champion_results(
            [("Easy", 90.0, 12.0, 88.0), ("Hard", 35.0, -4.0, 30.0), ("Ignored", 50.0)]
        )

        rates = {m.name: m.last_champion_win_rate for m in league.members}
        assert rates == {"Easy": 90.0, "Hard": 35.0, "Mid": None}

    def test_prune_drops_the_easiest_member(self):
        league = self._stocked_league(capacity=2)
        league.record_champion_results(
            [("Easy", 90.0), ("Hard", 35.0), ("Mid", 60.0)]
        )

        dropped = league.prune()

        assert [m.name for m in dropped] == ["Easy"]
        assert {m.name for m in league.members} == {"Hard", "Mid"}

    def test_prune_never_evicts_an_unmeasured_member(self):
        """A member that has not been faced has no evidence against it.

        This is what stops a freshly added best response from being dropped
        before it has ever supplied gradient.
        """

        league = self._stocked_league(capacity=2)
        league.record_champion_results([("Easy", 90.0), ("Hard", 35.0)])

        league.prune()

        assert "Mid" in {m.name for m in league.members}
        assert "Easy" not in {m.name for m in league.members}

    def test_retention_is_by_difficulty_not_recency(self):
        """The FIFO failure: the newest member is kept even when it is the
        easiest. Difficulty-based retention keeps the older, harder one."""

        league = AdversarialLeague(capacity=1)
        league.add(_make_strategy("Old", "Province"), name="Old", origin=ORIGIN_SEED)
        league.add(_make_strategy("New", "Copper"), name="New", origin=ORIGIN_CHAMPION)
        league.record_champion_results([("Old", 30.0), ("New", 95.0)])

        league.prune()

        assert [m.name for m in league.members] == ["Old"]

    def test_hardest_reports_the_binding_opponent(self):
        league = self._stocked_league(capacity=3)
        league.record_champion_results([("Easy", 90.0), ("Hard", 35.0), ("Mid", 60.0)])
        assert league.hardest().name == "Hard"

    def test_hardest_is_none_before_anything_is_measured(self):
        assert self._stocked_league(capacity=3).hardest() is None

    def test_summary_is_serialisable(self):
        league = self._stocked_league(capacity=3)
        league.record_champion_results([("Hard", 35.0)])
        summary = league.summary()
        assert {"name", "origin", "champion_win_rate"} == set(summary[0])
        assert {row["name"]: row["champion_win_rate"] for row in summary}["Hard"] == 35.0


# ---------------------------------------------------------------------------
# Seeding from the board
# ---------------------------------------------------------------------------


class TestSeededLeague:
    def test_extras_are_seeded_before_engine_archetypes(self):
        from dominion.boards.loader import load_board

        board = load_board("boards/oslo.txt")
        reference = _make_strategy("Reference", "Province", "Gold")

        league = build_seeded_league(
            board, capacity=3, max_engines=3, extra=[("Reference", reference)]
        )

        assert league.members[0].name == "Reference"
        assert all(m.origin == ORIGIN_SEED for m in league.members)
        # Oslo has a viable village+draw core, so engines fill the rest.
        assert len(league) > 1

    def test_capacity_is_respected(self):
        from dominion.boards.loader import load_board

        board = load_board("boards/oslo.txt")
        league = build_seeded_league(board, capacity=1, max_engines=3)
        assert len(league) == 1


# ---------------------------------------------------------------------------
# Trainer wiring
# ---------------------------------------------------------------------------


class TestTrainerIntegration:
    def test_league_supersedes_the_hall_of_fame_in_the_panel(self):
        league = AdversarialLeague(capacity=2)
        league.add(_make_strategy("Pool", "Province"), name="Pool", origin=ORIGIN_SEED)
        trainer = _make_trainer(league=league)
        trainer.hall_of_fame = [_make_strategy("HallOfFame-g10", "Gold")]

        assert [s.name for s in trainer._pool_opponents()] == ["Pool"]

    def test_hall_of_fame_is_used_when_no_league_is_supplied(self):
        trainer = _make_trainer()
        trainer.hall_of_fame = [_make_strategy("HallOfFame-g10", "Gold")]

        assert [s.name for s in trainer._pool_opponents()] == ["HallOfFame-g10"]

    def test_default_aggregation_is_unchanged(self):
        """Existing runs must keep scoring on the plain mean."""

        trainer = _make_trainer()
        assert trainer.worst_case_weight == 0.0
        assert trainer._aggregate([70.0, 40.0]) == 55.0

    def test_worst_case_weight_reaches_the_aggregator(self):
        trainer = _make_trainer(worst_case_weight=1.0)
        assert trainer._aggregate([70.0, 40.0]) == 40.0

    def test_update_league_promotes_champion_and_rebases(self, monkeypatch):
        league = AdversarialLeague(capacity=3)
        league.add(_make_strategy("Seed", "Province"), name="Seed", origin=ORIGIN_SEED)
        trainer = _make_trainer(league=league)
        trainer._best_strategy = _make_strategy("Champ", "Gold", "Silver")
        trainer._best_confirmed = 80.0

        def fake(strategy, games, context):
            trainer.last_eval_breakdown = [("Seed", 44.0)]
            return 52.0

        monkeypatch.setattr(trainer, "_eval_with_budget", fake)

        trainer._update_league(gen=9)

        assert [m.name for m in league.members] == ["Seed", "League-g10"]
        # Fitness was re-measured on the new, harder pool.
        assert trainer._best_confirmed == 52.0
        # And the rebase result updated the pool's difficulty record.
        assert league.members[0].last_champion_win_rate == 44.0

    def test_update_league_skips_a_duplicate_champion(self, monkeypatch):
        league = AdversarialLeague(capacity=3)
        league.add(_make_strategy("Seed", "Province"), name="Seed", origin=ORIGIN_SEED)
        trainer = _make_trainer(league=league)
        trainer._best_strategy = _make_strategy("Champ", "Province")
        trainer._best_confirmed = 80.0

        calls = []
        monkeypatch.setattr(
            trainer, "_eval_with_budget", lambda *a, **k: calls.append(a) or 52.0
        )

        trainer._update_league(gen=9)

        assert len(league) == 1
        # No rebase: the panel did not change, so no budget was spent.
        assert calls == []
        assert trainer._best_confirmed == 80.0

    def test_league_members_are_faced_during_evaluation(self, monkeypatch):
        league = AdversarialLeague(capacity=2)
        league.add(_make_strategy("Pool", "Province"), name="Pool", origin=ORIGIN_SEED)
        trainer = _make_trainer(games_per_eval=4, league=league)
        trainer.set_baseline_panel([_make_strategy("Baseline", "Province")])

        games_against: dict[str, int] = {}

        def fake_run_game(ai1, ai2, kingdom_cards, **kwargs):
            for ai in (ai1, ai2):
                if ai.strategy.name in {"Baseline", "Pool"}:
                    games_against[ai.strategy.name] = games_against.get(ai.strategy.name, 0) + 1
            return ai1, {}, None, 0

        monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)

        trainer.evaluate_strategy(_make_strategy("Candidate", "Gold"))

        # 4 games split across the baseline panel and the pool.
        assert games_against == {"Baseline": 2, "Pool": 2}


class TestCustomConditionSignatures:
    @staticmethod
    def _gated_strategy(copies):
        from generated_strategies.oslo_workers_village_magnate_engine import (
            _multi_colony_greening_gate,
        )
        strategy = _make_strategy('Colony engine', 'Colony')
        strategy.gain_priority[0].condition = _multi_colony_greening_gate(copies, 20)
        return strategy

    def test_different_closure_values_remain_distinct_pool_members(self):
        league = AdversarialLeague(capacity=3)
        for copies in (2, 5):
            assert league.add(
                self._gated_strategy(copies), name=f'Gate {copies}', origin=ORIGIN_SEED
            )
        assert not league.add(
            self._gated_strategy(2), name='Duplicate', origin=ORIGIN_CHAMPION
        )
        assert len(league) == 2

    def test_copy_and_worker_roundtrip_preserve_signature(self):
        from copy import deepcopy
        import cloudpickle

        strategy = self._gated_strategy(4)
        signature = genome_signature(strategy)
        clone = deepcopy(strategy)
        clone.name = 'Renamed'
        clone.gain_priority[0]._fired = True
        assert genome_signature(clone) == signature
        assert genome_signature(cloudpickle.loads(cloudpickle.dumps(strategy))) == signature
        assert GeneticTrainer._genome_signature(clone) == signature

    def test_unconditional_and_custom_conditions_differ(self):
        custom = self._gated_strategy(4)
        unconditional = _make_strategy('Always', 'Colony')
        assert genome_signature(custom) != genome_signature(unconditional)

    def test_defaults_and_way_conditions_are_included(self):
        from dominion.strategy.enhanced_strategy import WayRule

        def gate(threshold):
            return lambda state, player, limit=threshold: player.coins >= limit

        a = _make_strategy('A')
        b = _make_strategy('B')
        a.way_policy = [WayRule('Village', 'Way of the Otter', gate(4))]
        b.way_policy = [WayRule('Village', 'Way of the Otter', gate(8))]
        assert genome_signature(a) != genome_signature(b)
