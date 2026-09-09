"""Kimberley board: Mine decisions, multiplier targeting, and search diagnostics."""

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from generated_strategies.kimberley_mine_engine import create_kimberley_mine_engine
from scripts import search_kimberley as search


def _state(player, supply, phase="action"):
    return GameState(players=[player], supply=supply, phase=phase)


def test_mine_climbs_gold_to_platinum_before_smaller_steps():
    strategy = create_kimberley_mine_engine()
    player = PlayerState(ai=GeneticAI(strategy))
    player.hand = [get_card(n) for n in ["Copper", "Silver", "Gold", "Mine"]]
    state = _state(player, {"Platinum": 12, "Gold": 30, "Silver": 40})

    treasures = [c for c in player.hand if c.is_treasure]
    assert player.ai.choose_mine_treasure(state, player, treasures).name == "Gold"
    gains = [get_card(n) for n in ["Platinum", "Gold", "Silver", "Copper"]]
    assert player.ai.choose_mine_gain(state, player, gains).name == "Platinum"

    # With the Platinum pile empty, Gold is no longer worth trashing.
    state.supply["Platinum"] = 0
    assert player.ai.choose_mine_treasure(state, player, treasures).name == "Silver"


def test_mine_is_not_played_without_an_upgradeable_treasure():
    strategy = create_kimberley_mine_engine()
    player = PlayerState(ai=GeneticAI(strategy), actions=1)
    player.hand = [get_card(n) for n in ["Platinum", "Mine", "Smithy"]]
    state = _state(player, {"Platinum": 0, "Gold": 30, "Silver": 40})
    state._choosing_main_action_phase = True

    choice = strategy.choose_action(state, player, [c for c in player.hand if c.is_action])
    assert choice.name == "Smithy"


def test_kings_court_targets_mine_when_it_can_climb():
    strategy = create_kimberley_mine_engine()
    player = PlayerState(ai=GeneticAI(strategy))
    player.hand = [get_card(n) for n in ["Copper", "Mine", "Smithy", "Laboratory"]]
    state = _state(player, {"Platinum": 12, "Gold": 30, "Silver": 40})

    actions = [c for c in player.hand if c.is_action]
    assert player.ai.choose_action(state, actions + [None]).name == "Mine"
    player.hand = [get_card(n) for n in ["Platinum", "Mine", "Smithy"]]
    state.supply["Platinum"] = 0
    actions = [c for c in player.hand if c.is_action]
    assert player.ai.choose_action(state, actions + [None]).name == "Smithy"


def test_published_strategy_buys_colony_once_it_owns_platinum():
    strategy = create_kimberley_mine_engine()
    player = PlayerState(ai=GeneticAI(strategy), turns_taken=6, coins=11)
    player.deck = [get_card(n) for n in ["Platinum", "Mine", "Silver"]]
    state = _state(player, {"Colony": 8, "Province": 8, "Platinum": 11}, phase="buy")
    choices = [get_card(n) for n in ["Colony", "Province", "Platinum", "Gold"]]

    assert player.ai.choose_buy(state, choices).name == "Colony"
    player.deck = [get_card(n) for n in ["Gold", "Mine", "Silver"]]
    assert player.ai.choose_buy(state, choices).name == "Platinum"


def test_board_lists_every_synergy_piece():
    assert set(search.BOARD.kingdom_cards) >= {
        "Mine", "King's Court", "Throne Room", "Market Square", "Priest", "Colony", "Platinum"
    }
    assert search.BOARD.projects == ["Sewers"]
    assert search.BOARD.landmarks == ["Tomb"]


@pytest.mark.parametrize("turn_limit", [101, 160])
@pytest.mark.parametrize("normal_end", [False, True])
def test_search_reports_only_unnatural_turn_limit_endings_as_truncated(
    monkeypatch, turn_limit, normal_end
):
    class EndAtLimit(search.GameState):
        def play_turn(self):
            self.turn_number = turn_limit
            if normal_end:
                self.supply["Colony"] = 0

    monkeypatch.setattr(search, "GameState", EndAtLimit)

    result = search.match(({}, search.REFERENCE, 2, 100))

    assert result["totals"]["truncated"] == (0 if normal_end else 2)
