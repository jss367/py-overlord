from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def make_state(ai: DummyAI) -> tuple[GameState, PlayerState]:
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    state.supply = {}
    return state, player


class WildHuntChoiceAI(DummyAI):
    def __init__(self, choices: list[str]):
        super().__init__()
        self._choices = list(choices)

    def choose_wild_hunt_option(self, state, player, options):
        if self._choices:
            return self._choices.pop(0)
        return "draw"


def test_wild_hunt_draw_option_builds_pile_tokens():
    ai = WildHuntChoiceAI(["draw", "draw"])
    state, player = make_state(ai)
    wild_hunt = get_card("Wild Hunt")

    player.deck = [get_card("Copper") for _ in range(6)]

    wild_hunt.play_effect(state)
    assert state.wild_hunt_pile_tokens == 1
    assert len(player.hand) == 3

    wild_hunt.play_effect(state)
    assert state.wild_hunt_pile_tokens == 2
    assert len(player.hand) == 6


def test_wild_hunt_estate_option_gains_estate_and_scores_tokens():
    ai = WildHuntChoiceAI(["draw", "draw", "estate"])
    state, player = make_state(ai)
    wild_hunt = get_card("Wild Hunt")

    state.supply = {"Estate": 8}
    player.deck = [get_card("Copper") for _ in range(9)]

    wild_hunt.play_effect(state)
    wild_hunt.play_effect(state)

    assert state.wild_hunt_pile_tokens == 2

    previous_vp = player.vp_tokens
    wild_hunt.play_effect(state)

    assert state.supply["Estate"] == 7
    assert any(card.name == "Estate" for card in player.discard)
    assert player.vp_tokens == previous_vp + 2
    assert state.wild_hunt_pile_tokens == 0
