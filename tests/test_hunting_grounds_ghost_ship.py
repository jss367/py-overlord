"""Board setup, legal card interactions and policy integration for the new kingdom."""

from collections import Counter
import json
from pathlib import Path

import pytest

from dominion.ai.base_ai import AI
from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategy_loader import StrategyLoader
from dominion.strategy.strategies.hunting_grounds_ghost_ship import (
    KINGDOM,
    HuntingGroundsPolicy,
)
from scripts.search_hunting_grounds_ghost_ship import match


def setup(**params):
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(HuntingGroundsPolicy(**params)) for _ in range(2)],
        [get_card(n) for n in KINGDOM],
    )
    return state, state.current_player


def test_board_and_provenance_cover_ten_historically_unused_piles():
    audit = json.loads(
        Path("scripts/data/hunting_grounds_ghost_ship_provenance.json").read_text()
    )
    assert len(KINGDOM) == len(set(KINGDOM)) == 10
    assert list(KINGDOM) == audit["cards"]
    assert all(not refs for refs in audit["local_history_matches"].values())
    assert all(not refs for refs in audit["catalog_references"].values())
    board = load_board("boards/hunting_grounds_ghost_ship.txt")
    assert board.kingdom_cards == list(KINGDOM)
    state, _ = setup()
    assert not {"Potion", "Platinum", "Colony", "Necropolis"} & state.supply.keys()
    for p in state.players:
        assert Counter(c.name for c in p.all_cards()) == {"Copper": 7, "Estate": 3}
    assert StrategyLoader().get_strategy("hunting_grounds_ghost_ship") is not None


def test_ghost_ship_draws_two_and_keeps_opponents_draw_in_hand():
    state, player = setup()
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(4)]
    other = state.players[1]
    other.hand = [
        get_card(n)
        for n in ["Estate", "Copper", "Gold", "Farming Village", "Hunting Grounds"]
    ]
    get_card("Ghost Ship").on_play(state)
    assert len(player.hand) == 2
    assert {c.name for c in other.hand} == {
        "Gold",
        "Farming Village",
        "Hunting Grounds",
    }
    assert len(other.hand) == 3


def test_opponents_bishop_trashes_own_copper_using_own_money_density():
    state, player = setup(copper_floor=0)
    player.hand = []
    player.deck = []
    player.discard = []
    other = state.players[1]
    other.hand = [get_card("Copper"), get_card("Gold")]
    other.deck = [get_card("Gold"), get_card("Gold")]
    other.discard = []
    get_card("Bishop").on_play(state)
    assert [c.name for c in other.hand] == ["Gold"]
    assert player.vp_tokens == 1


def test_bishop_trashing_hunting_grounds_awards_duchy_and_four_tokens():
    state, player = setup(bishop_fodder=True)
    player.hand = [get_card("Hunting Grounds")]
    duchies = state.supply["Duchy"]
    get_card("Bishop").on_play(state)
    assert player.vp_tokens == 4
    assert state.supply["Duchy"] == duchies - 1
    assert any(c.name == "Duchy" for c in player.discard)


def test_apprentice_consumes_estate_and_draws_exactly_two():
    state, player = setup()
    player.hand = [get_card("Estate")]
    player.deck = [get_card("Silver") for _ in range(5)]
    player.actions = 0
    get_card("Apprentice").on_play(state)
    assert [c.name for c in player.hand] == ["Silver", "Silver"]
    assert player.actions == 1


def test_clean_deck_skips_mandatory_trashers_and_raze_trashes_itself():
    state, player = setup()
    player.hand = [get_card(n) for n in ["Apprentice", "Bishop", "Gold"]]
    assert player.ai.choose_action(state, player.hand[:2]) is None
    raze = get_card("Raze")
    player.in_play = [raze]
    player.deck = [get_card("Silver"), get_card("Copper")]
    raze.on_play(state)
    assert raze not in player.in_play
    assert len(player.hand) == 4
    assert player.hand[-1].name == "Silver"


def test_quarry_discount_applies_to_actions_only():
    state, player = setup()
    player.in_play = [get_card("Quarry")]
    assert state.get_card_cost(player, get_card("Hunting Grounds")) == 4
    assert state.get_card_cost(player, get_card("Province")) == 8
    assert state.get_card_cost(player, get_card("Cache")) == 5


def test_new_hooks_preserve_generic_ai_fallbacks():
    state, player = setup()
    player.ai = GeneticAI(EnhancedStrategy())
    choices = [get_card("Estate"), get_card("Silver")]
    for name in [
        "choose_card_to_raze",
        "choose_card_to_keep_from_raze",
        "choose_card_to_topdeck_from_hand",
    ]:
        assert getattr(player.ai, name)(state, player, choices) is getattr(AI, name)(
            player.ai, state, player, choices
        )


def test_seeded_match_is_reproducible_and_finishes_normally():
    task = ({"targets": [["Ghost Ship", 2]]}, {}, 4, 42)
    first = match(task)
    assert first == match(task)
    assert first["truncated"] == 0
    assert len(first["pair_points"]) == 2
    with pytest.raises(ValueError):
        match(({}, {}, 3, 42))


def test_incomplete_games_cannot_select_a_winner():
    from scripts.search_hunting_grounds_ghost_ship import ranking

    rows = [
        dict(a={"opening": "Raze"}, b={}, rate=1, truncated=1),
        dict(a={"opening": "Silver"}, b={}, rate=0.5, truncated=0),
    ]
    assert ranking(rows, screen=True) == [(0.5, {"opening": "Silver"})]


def test_published_policy_matches_frozen_validation_winner():
    from dominion.strategy.strategies.hunting_grounds_ghost_ship import (
        create_hunting_grounds_ghost_ship,
    )

    rows = json.loads(
        Path("scripts/data/hunting_grounds_ghost_ship/validate.json").read_text()
    )
    published = create_hunting_grounds_ghost_ship().params
    assert all(HuntingGroundsPolicy(**r["a"]).params == published for r in rows)
    assert all(r["truncated"] == 0 for r in rows)
    assert all(r["seed"] >= 1000000 for r in rows)
