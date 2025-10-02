from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class HammerChoiceAI(DummyAI):
    def __init__(self, target: str):
        super().__init__()
        self._target = target

    def choose_buy(self, state, choices):
        for card in choices:
            if card is not None and card.name == self._target:
                return card
        return None


def _make_state(ai: DummyAI):
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda msg: None
    state.supply = {}
    return state, player


def test_hammer_gains_card_selected_by_ai():
    ai = HammerChoiceAI("Village")
    state, player = _make_state(ai)

    state.supply.update({"Village": 5, "Silver": 5})

    hammer = get_card("Hammer")
    hammer.play_effect(state)

    assert [card.name for card in player.discard] == ["Village"]
    assert state.supply["Village"] == 4
