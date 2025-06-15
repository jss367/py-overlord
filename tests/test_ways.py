from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.ways.butterfly import WayOfTheButterfly
from tests.utils import DummyAI


class ButterflyAI(DummyAI):
    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_way(self, state, card, ways):
        for w in ways:
            if w and w.name == "Way of the Butterfly":
                return w
        return None


def test_way_of_the_butterfly():
    ai = ButterflyAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village"), get_card("Smithy")], ways=[WayOfTheButterfly()])
    player = state.players[0]
    player.hand = [get_card("Village")]
    state.phase = "action"
    village_supply_before = state.supply["Village"]
    smithy_supply_before = state.supply["Smithy"]
    state.handle_action_phase()
    assert state.supply["Village"] == village_supply_before + 1
    assert state.supply["Smithy"] == smithy_supply_before - 1
    assert any(card.name == "Smithy" for card in player.discard)
