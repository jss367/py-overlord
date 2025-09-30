from typing import Optional, Set

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import DummyAI


class TraderTestAI(DummyAI):
    def __init__(self, trash_target: Optional[str] = None, reveal_for: Optional[Set[str]] = None):
        super().__init__()
        self.trash_target = trash_target
        self.reveal_for = reveal_for or set()

    def choose_card_to_trash(self, state, choices):
        if not self.trash_target:
            return None
        for card in choices:
            if card.name == self.trash_target:
                return card
        return None

    def should_reveal_trader(self, state, player, gained_card, *, to_deck):
        return gained_card.name in self.reveal_for


def _prepare_state(ai):
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Trader"), get_card("Duchy")])
    player = state.players[0]
    player.actions = 1
    player.hand = []
    player.in_play = []
    player.discard = []
    player.deck = []
    return state, player


def test_trader_trashes_and_gains_silvers():
    ai = TraderTestAI(trash_target="Duchy")
    state, player = _prepare_state(ai)

    trader_card = get_card("Trader")
    duchy = get_card("Duchy")
    player.hand = [trader_card, duchy]
    player.cost_reduction = 1

    player.hand.remove(trader_card)
    player.in_play.append(trader_card)

    trader_card.play_effect(state)

    assert all(card.name != "Duchy" for card in player.hand)
    assert any(card.name == "Duchy" for card in state.trash)
    silvers = [card for card in player.discard if card.name == "Silver"]
    assert len(silvers) == 4


def test_trader_reaction_exchanges_gain_for_silver():
    ai = TraderTestAI(reveal_for={"Estate"})
    state, player = _prepare_state(ai)

    trader_card = get_card("Trader")
    player.hand = [trader_card]

    estate = get_card("Estate")
    state.supply["Estate"] = 8
    state.supply["Silver"] = 40

    state.supply["Estate"] -= 1
    gained = state.gain_card(player, estate, to_deck=True)

    assert gained.name == "Silver"
    assert player.deck[0].name == "Silver"
    assert all(card.name != "Estate" for card in player.deck + player.discard)
    assert state.supply["Estate"] == 8
    assert state.supply["Silver"] == 39
