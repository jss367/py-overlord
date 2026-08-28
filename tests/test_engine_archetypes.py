"""Tests for board-derived engine archetypes (dominion.analysis.engine_archetypes)."""

from __future__ import annotations

import pytest

from dominion.analysis.engine_archetypes import (
    build_engine_seeds,
    enumerate_engine_parts,
)
from dominion.boards.loader import BoardConfig, load_board


def _condition_source(rule) -> str:
    return getattr(rule.condition, "_source", "") if rule.condition else ""


def _gain_rules(strategy) -> dict[str, str]:
    """Map card -> condition source for the FIRST rule naming that card."""
    out: dict[str, str] = {}
    for rule in strategy.gain_priority:
        out.setdefault(rule.card_name, _condition_source(rule))
    return out


class TestEnumeration:
    def test_no_village_means_no_engines(self):
        board = BoardConfig(kingdom_cards=["Smithy", "Witch", "Chapel", "Moat"])
        assert enumerate_engine_parts(board) == []

    def test_no_draw_means_no_engines(self):
        board = BoardConfig(kingdom_cards=["Village", "Chapel", "Militia"])
        assert enumerate_engine_parts(board) == []

    def test_village_smithy_forms_a_core(self):
        board = BoardConfig(kingdom_cards=["Village", "Smithy", "Chapel", "Market"])
        engines = enumerate_engine_parts(board)
        assert engines
        assert engines[0].village.name == "Village"
        assert engines[0].draw.name == "Smithy"

    def test_max_engines_bounds_output(self):
        board = BoardConfig(
            kingdom_cards=["Village", "Festival", "Smithy", "Witch", "Moat"]
        )
        assert len(enumerate_engine_parts(board, max_engines=2)) == 2

    def test_seed_names_are_unique(self):
        board = BoardConfig(
            kingdom_cards=["Village", "Festival", "Smithy", "Witch", "Moat"]
        )
        names = [name for name, _ in build_engine_seeds(board, max_engines=3)]
        assert len(names) == len(set(names))

    def test_buy_source_added_when_core_lacks_buys(self):
        # Market's $1 keeps it out of the payload slot, so it can only
        # enter the composition through the +buy backfill.
        board = BoardConfig(kingdom_cards=["Village", "Smithy", "Market"])
        parts = enumerate_engine_parts(board)[0]
        assert parts.buy_source is not None and parts.buy_source.name == "Market"

    def test_no_buy_source_when_core_has_buys(self):
        board = BoardConfig(kingdom_cards=["Workers' Village", "Smithy", "Woodcutter"])
        parts = enumerate_engine_parts(board)[0]
        assert parts.buy_source is None


class TestSeedShape:
    def test_seed_delays_greening_and_caps_core_high(self):
        board = BoardConfig(kingdom_cards=["Village", "Smithy", "Market", "Chapel"])
        _name, strat = build_engine_seeds(board)[0]
        gains = _gain_rules(strat)

        # Province is gated (engine seeds green late), never unconditional.
        assert gains["Province"]
        # Core caps reach deep-engine counts.
        assert "PriorityRule.max_in_deck('Smithy', 7)" in gains["Smithy"]
        assert "PriorityRule.max_in_deck('Village', 7)" in gains["Village"]
        # Draw is balanced against the village count.
        assert "deck_count_diff" in gains["Smithy"]
        # Economy fallback exists and Silver is ungated.
        assert gains["Silver"] == ""

    def test_actions_ordered_villages_before_draw(self):
        board = BoardConfig(kingdom_cards=["Village", "Smithy", "Market"])
        _name, strat = build_engine_seeds(board)[0]
        order = [r.card_name for r in strat.action_priority]
        assert order.index("Village") < order.index("Smithy")


class TestOsloRediscovery:
    """Acceptance: with no human hint and no strategy library, the
    enumerator must reproduce the Workers' Village / Magnate engine
    topology on the Oslo board — the composition that previously required
    the user to supply it (partial engines lose to money, so the GA could
    never assemble it from mutation)."""

    @pytest.fixture(scope="class")
    def oslo_seeds(self):
        return build_engine_seeds(load_board("boards/oslo.txt"))

    def test_top_seed_is_workers_village_magnate(self, oslo_seeds):
        name, _strat = oslo_seeds[0]
        assert name == "Engine Workers' Village + Magnate"

    def test_topology_includes_payload_multiplier_and_gainer(self, oslo_seeds):
        _name, strat = oslo_seeds[0]
        gains = _gain_rules(strat)
        for piece in ("Workers' Village", "Magnate", "Bank", "King's Court", "Anvil"):
            assert piece in gains, f"missing engine piece: {piece}"

    def test_core_counts_reach_winning_depth(self, oslo_seeds):
        """The known-best engine runs seven Villages and seven Magnates;
        the seed must start in that region, not at the conservative caps
        that made the composition unsearchable."""
        _name, strat = oslo_seeds[0]
        gains = _gain_rules(strat)
        assert "PriorityRule.max_in_deck(\"Workers' Village\", 7)" in gains["Workers' Village"]
        assert "PriorityRule.max_in_deck('Magnate', 7)" in gains["Magnate"]

    def test_colony_greening_gates(self, oslo_seeds):
        _name, strat = oslo_seeds[0]
        gains = _gain_rules(strat)
        assert gains["Colony"] == ""  # win condition, ungated
        assert "colonies_left" in gains["Province"]

    @pytest.mark.slow
    def test_seed_is_competitive_before_any_evolution(self):
        """The unevolved seed must clear the fitness valley on its own:
        comfortably ahead of Big Money, so the island GA starts from a
        working engine rather than a losing pile of parts. (The user's
        literal seed strategy won ~10% before evolution; this template
        battles ~60%+. The floor here is loose to keep the test stable.)"""
        import logging

        from dominion.simulation.strategy_battle import StrategyBattle

        logging.disable(logging.CRITICAL)
        try:
            board = load_board("boards/oslo.txt")
            name, seed = build_engine_seeds(board)[0]
            battle = StrategyBattle(
                board_config=board,
                log_folder="battle_logs/_engine_seed_test",
                log_frequency=10_000,
            )
            battle.strategy_loader.register_strategy(name, lambda: seed)
            result = battle.run_battle(name, "Big Money", num_games=40)
        finally:
            logging.disable(logging.NOTSET)
        win_rate = result["strategy1_wins"] / result["games_played"]
        assert win_rate >= 0.35, f"engine seed only won {win_rate:.0%} vs Big Money"
