from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class NamedCardAI(DummyAI):
    def __init__(self, named: str):
        super().__init__()
        self.named = named

    def name_card_for_wishing_well(self, state, player):
        return self.named


def _state_with_sorcerer(opponent_ai):
    attacker = PlayerState(DummyAI())
    opponent = PlayerState(opponent_ai)
    state = GameState(players=[attacker, opponent])
    state.supply["Curse"] = 10
    return state, attacker, opponent


def test_sorcerer_wrong_name_gains_curse_onto_deck():
    state, attacker, opponent = _state_with_sorcerer(NamedCardAI("Copper"))
    opponent.deck = [get_card("Estate")]

    get_card("Sorcerer").play_effect(state)

    assert attacker.favors == 1
    assert state.supply["Curse"] == 9
    assert [card.name for card in opponent.deck] == ["Estate", "Curse"]


def test_sorcerer_correct_name_avoids_curse_and_keeps_revealed_card():
    state, attacker, opponent = _state_with_sorcerer(NamedCardAI("Estate"))
    opponent.deck = [get_card("Estate")]

    get_card("Sorcerer").play_effect(state)

    assert attacker.favors == 1
    assert state.supply["Curse"] == 10
    assert [card.name for card in opponent.deck] == ["Estate"]


def test_sorcerer_no_revealed_card_does_not_gain_curse():
    state, attacker, opponent = _state_with_sorcerer(NamedCardAI("Copper"))
    opponent.deck = []
    opponent.discard = []

    get_card("Sorcerer").play_effect(state)

    assert attacker.favors == 1
    assert state.supply["Curse"] == 10
    assert opponent.deck == []
    assert opponent.discard == []
