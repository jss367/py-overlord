from dominion.cards.plunder import LOOT_CARD_NAMES
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def test_wealthy_village_does_not_gain_loot_when_empty():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])

    for loot in LOOT_CARD_NAMES:
        state.supply[loot] = 0

    player.in_play = [get_card("Copper"), get_card("Silver"), get_card("Gold")]

    wealthy_village = get_card("Wealthy Village")
    state.supply[wealthy_village.name] = 1
    state.supply[wealthy_village.name] -= 1

    state.gain_card(player, wealthy_village)

    assert all(card.name not in LOOT_CARD_NAMES for card in player.discard)
    assert all(state.supply[loot] == 0 for loot in LOOT_CARD_NAMES)
