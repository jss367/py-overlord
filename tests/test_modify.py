from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import TrashFirstAI


def make_state(ai) -> tuple[GameState, PlayerState]:
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    return state, player


class CantripModifyAI(TrashFirstAI):
    """AI that always chooses the cantrip option after trashing."""

    def choose_buy(self, state, choices: list[Optional[Card]]):
        return None


class GainFirstModifyAI(TrashFirstAI):
    """AI that prefers gaining a card if any valid choice exists."""

    def choose_buy(self, state, choices: list[Optional[Card]]):
        for choice in choices:
            if choice is not None:
                return choice
        return None


def test_modify_cantrip_when_no_gain_available():
    state, player = make_state(CantripModifyAI())
    modify = get_card("Modify")

    trashed_card = get_card("Copper")
    player.hand = [trashed_card]
    player.deck = [get_card("Silver")]
    player.actions = 0
    state.supply = {"Estate": 4}

    modify.play_effect(state)

    assert len(player.hand) == 1 and player.hand[0].name == "Silver"
    assert player.actions == 1
    assert state.trash and state.trash[-1].name == "Copper"
    assert state.supply["Estate"] == 4


def test_modify_gains_card_when_ai_prefers_gain():
    state, player = make_state(GainFirstModifyAI())
    modify = get_card("Modify")

    trashed_card = get_card("Estate")
    player.hand = [trashed_card]
    player.actions = 0
    state.supply = {"Silver": 5}

    modify.play_effect(state)

    assert player.actions == 0
    assert state.trash and state.trash[-1].name == "Estate"
    assert state.supply["Silver"] == 4
    assert any(card.name == "Silver" for card in player.discard)
    assert not player.hand
