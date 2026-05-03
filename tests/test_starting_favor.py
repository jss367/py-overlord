"""Each player starts with 1 Favor token when an Ally is in the game.

Per the official Dominion: Allies rules, "Each player starts the game with 1
Favor" whenever an Ally is included. Without this setup step, Ally abilities
can't be activated until a Liaison resolves, which silently changes early-turn
behavior on Ally boards.
"""

from dominion.allies.registry import get_ally
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


def _initialize(player_count: int, allies: list) -> GameState:
    state = GameState(players=[])
    ais = [_NullAI() for _ in range(player_count)]
    # initialize_game uses ais to construct PlayerState; pass a minimal kingdom.
    state.initialize_game(ais, [get_card("Village")], allies=allies)
    return state


def test_each_player_gets_one_favor_when_ally_is_in_game():
    cave_dwellers = get_ally("Cave Dwellers")
    state = _initialize(2, allies=[cave_dwellers])
    for player in state.players:
        assert player.favors == 1


def test_no_starting_favor_when_no_ally_present():
    state = _initialize(2, allies=[])
    for player in state.players:
        assert player.favors == 0


def test_starting_favor_scales_with_player_count():
    cave_dwellers = get_ally("Cave Dwellers")
    state = _initialize(4, allies=[cave_dwellers])
    assert sum(p.favors for p in state.players) == 4
