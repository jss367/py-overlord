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


class FarmersMarketChoiceAI(DummyAI):
    def __init__(self, choices: list[str]):
        super().__init__()
        self._choices = list(choices)

    def choose_farmers_market_option(self, state, player, options, pile_tokens):
        if self._choices:
            return self._choices.pop(0)
        return super().choose_farmers_market_option(state, player, options, pile_tokens)


def test_farmers_market_coin_option_builds_pile_tokens():
    ai = FarmersMarketChoiceAI(["coins", "coins"])
    state, player = make_state(ai)
    farmers_market = get_card("Farmers' Market")

    farmers_market.play_effect(state)
    assert player.coins == 0
    assert state.farmers_market_pile_tokens == 1

    farmers_market.play_effect(state)
    assert player.coins == 1
    assert state.farmers_market_pile_tokens == 2


def test_farmers_market_vp_option_trashes_and_awards_tokens():
    ai = FarmersMarketChoiceAI(["coins", "coins", "vp"])
    state, player = make_state(ai)
    farmers_market = get_card("Farmers' Market")

    farmers_market.play_effect(state)
    farmers_market.play_effect(state)

    assert state.farmers_market_pile_tokens == 2
    assert player.coins == 1

    player.in_play.append(farmers_market)
    previous_vp = player.vp_tokens

    farmers_market.play_effect(state)

    assert player.vp_tokens == previous_vp + 2
    assert player.coins == 1
    assert farmers_market not in player.in_play
    assert farmers_market in state.trash
    assert state.farmers_market_pile_tokens == 1
