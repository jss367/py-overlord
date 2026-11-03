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

    def should_discard_exiled_copies(self, state, player, gained_card):
        # Always accept, so tests exercise gain_card's exiled-copy matching
        # rather than the default AI's junk filter.
        return True


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
    player.deck = [get_card("Copper")]
    player.actions = 0
    player.cost_reduction = 1

    player.hand.remove(trader_card)
    player.in_play.append(trader_card)

    trader_card.on_play(state)

    assert all(card.name != "Duchy" for card in player.hand)
    assert any(card.name == "Duchy" for card in state.trash)
    silvers = [card for card in player.discard if card.name == "Silver"]
    assert len(silvers) == 4
    assert player.actions == 0
    assert player.deck and player.deck[-1].name == "Copper"


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
    assert not player.deck
    assert [c.name for c in player.discard] == ["Silver"]
    assert all(card.name != "Estate" for card in player.deck + player.discard)
    assert state.supply["Estate"] == 8
    assert state.supply["Silver"] == 39


def test_trader_exchange_discards_exiled_original_copies_not_silvers():
    """The Estate was gained; the exchanged Silver was not gained."""

    ai = TraderTestAI(reveal_for={"Estate"})
    state, player = _prepare_state(ai)

    player.hand = [get_card("Trader")]
    player.exile = [get_card("Silver"), get_card("Silver"), get_card("Estate")]
    state.supply["Estate"] = 8
    state.supply["Silver"] = 40

    state.supply["Estate"] -= 1
    gained = state.gain_card(player, get_card("Estate"))

    assert gained.name == "Silver"
    assert [card.name for card in player.exile] == ["Silver", "Silver"]
    assert sorted(c.name for c in player.discard) == ["Estate", "Silver"]
    assert player.gained_cards_this_turn == ["Estate"]


def test_trader_exchange_preserves_original_gain_exile_trigger():
    """Original-gain Exile triggers survive an exchange."""

    ai = TraderTestAI(reveal_for={"Estate"})
    state, player = _prepare_state(ai)

    player.hand = [get_card("Trader")]
    player.exile = [get_card("Estate")]
    state.supply["Estate"] = 8
    state.supply["Silver"] = 40

    state.supply["Estate"] -= 1
    gained = state.gain_card(player, get_card("Estate"))

    assert gained.name == "Silver"
    assert player.exile == []
    assert sorted(card.name for card in player.discard) == ["Estate", "Silver"]


def test_trader_exchange_does_not_create_a_silver_gain_for_gatekeeper():
    """Gatekeeper cannot exile the Silver received by exchange."""

    ai = TraderTestAI(reveal_for={"Estate"})
    state, player = _prepare_state(ai)

    player.hand = [get_card("Trader")]
    player.exile = [get_card("Estate")]
    player.gatekeeper_attacks = 1
    state.supply["Estate"] = 8
    state.supply["Silver"] = 40

    state.supply["Estate"] -= 1
    gained = state.gain_card(player, get_card("Estate"))

    assert gained.name == "Silver"
    assert player.exile == []
    assert sorted(c.name for c in player.discard) == ["Estate", "Silver"]
    assert player.gained_cards_this_turn == ["Estate"]
