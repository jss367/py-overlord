"""Wizards split pile supply sizing across player counts.

The four-card Wizards pile (Student → Conjurer → Sorcerer → Lich) must use
the same player-count-aware supply size for every partner pile, mirroring
how ``SplitPileMixin`` already handles two-card splits.
"""

from dominion.cards.allies.wizards import WIZARDS_PILE_ORDER
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _NullAI:
    name = "null"

    def __init__(self):
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, *args, **kwargs):
        return None


def _setup(player_count: int) -> GameState:
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI()) for _ in range(player_count)]
    state.setup_supply([get_card("Student")])
    return state


def test_wizards_pile_uses_two_player_supply():
    state = _setup(2)
    for name in WIZARDS_PILE_ORDER:
        assert state.supply[name] == 4, f"{name} should have 4 copies in 2-player"


def test_wizards_pile_uses_higher_player_supply():
    state = _setup(3)
    for name in WIZARDS_PILE_ORDER:
        assert state.supply[name] == 5, f"{name} should have 5 copies in 3-player"
