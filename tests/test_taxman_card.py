from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class TaxmanAI(DummyAI):
    def __init__(self, trash_name: str | None = None, gain_name: str | None = None):
        super().__init__()
        self.trash_name = trash_name
        self.gain_name = gain_name

    def choose_card_to_trash(
        self, state: GameState, choices: list[Card]
    ) -> Optional[Card]:
        if self.trash_name is None:
            return None
        return next((card for card in choices if card and card.name == self.trash_name), None)

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        if self.gain_name is None:
            return None
        return next((card for card in choices if card and card.name == self.gain_name), None)


def make_state(*ais: DummyAI) -> GameState:
    players = [PlayerState(ai) for ai in ais]
    state = GameState(players=players)
    state.setup_supply([])
    state.current_player_index = 0
    state.phase = "action"
    for player in players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.in_play = []
        player.duration = []
    return state


def play_taxman(state: GameState) -> None:
    player = state.current_player
    taxman = next(card for card in player.hand if card.name == "Taxman")
    player.hand.remove(taxman)
    player.in_play.append(taxman)
    taxman.on_play(state)


def test_taxman_ai_can_decline_trashing_treasure():
    state = make_state(TaxmanAI(), DummyAI())
    attacker, defender = state.players
    copper = get_card("Copper")
    attacker.hand = [get_card("Taxman"), copper]
    defender.hand = [
        get_card("Copper"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
    ]
    silver_before = state.supply["Silver"]

    play_taxman(state)

    assert copper in attacker.hand
    assert state.trash == []
    assert attacker.deck == []
    assert len(defender.hand) == 5
    assert defender.discard == []
    assert state.supply["Silver"] == silver_before


def test_taxman_trashes_copper_and_gains_silver_to_deck():
    state = make_state(TaxmanAI(trash_name="Copper", gain_name="Silver"))
    player = state.players[0]
    copper = get_card("Copper")
    player.hand = [get_card("Taxman"), copper]
    silver_before = state.supply["Silver"]

    play_taxman(state)

    assert copper not in player.hand
    assert state.trash == [copper]
    assert player.deck[-1].name == "Silver"
    assert player.discard == []
    assert state.supply["Silver"] == silver_before - 1


def test_taxman_opponents_discard_matching_copper_without_gaining_silver():
    state = make_state(TaxmanAI(trash_name="Copper", gain_name="Silver"), DummyAI())
    attacker, defender = state.players
    defender_copper = get_card("Copper")
    attacker.hand = [get_card("Taxman"), get_card("Copper")]
    defender.hand = [
        defender_copper,
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
    ]

    play_taxman(state)

    assert defender_copper not in defender.hand
    assert defender.discard == [defender_copper]
    assert [card.name for card in defender.deck] == []
    assert all(card.name != "Silver" for card in defender.hand + defender.discard)


def test_taxman_opponent_with_fewer_than_five_cards_is_unaffected():
    state = make_state(TaxmanAI(trash_name="Copper", gain_name="Silver"), DummyAI())
    attacker, defender = state.players
    defender_copper = get_card("Copper")
    attacker.hand = [get_card("Taxman"), get_card("Copper")]
    defender.hand = [
        defender_copper,
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
    ]
    original_hand = list(defender.hand)

    play_taxman(state)

    assert defender.hand == original_hand
    assert defender.discard == []
