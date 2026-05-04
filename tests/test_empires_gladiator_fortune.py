"""Tests for the Gladiator/Fortune split pile."""

from dominion.cards.empires.fortune import Fortune
from dominion.cards.empires.gladiator import Gladiator
from dominion.cards.registry import get_card
from dominion.cards.split_pile import BottomSplitPileCard, TopSplitPileCard
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


def _make_game():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players=players)
    state.initialize_game(
        [DummyAI() for _ in range(2)],
        [get_card("Gladiator"), get_card("Village")],
    )
    return state


def test_gladiator_is_top_split_pile():
    g = Gladiator()
    assert isinstance(g, TopSplitPileCard)
    assert g.partner_card_name == "Fortune"


def test_fortune_is_bottom_split_pile():
    f = Fortune()
    assert isinstance(f, BottomSplitPileCard)
    assert f.partner_card_name == "Gladiator"


def test_split_pile_setup_includes_partner():
    state = _make_game()
    assert state.supply.get("Gladiator") == 5
    assert state.supply.get("Fortune") == 5


def test_fortune_not_buyable_until_gladiators_gone():
    state = _make_game()
    fortune = get_card("Fortune")
    assert not fortune.may_be_bought(state)

    state.supply["Gladiator"] = 0
    assert fortune.may_be_bought(state)


def test_fortune_doubles_coins_once_per_turn():
    state = _make_game()
    player = state.players[0]
    player.coins = 5
    fortune = get_card("Fortune")
    fortune.play_effect(state)
    assert player.coins == 10

    # Playing a second Fortune doesn't double again.
    fortune2 = get_card("Fortune")
    fortune2.play_effect(state)
    assert player.coins == 10


def test_gladiator_trashes_one_from_supply_when_unmatched():
    state = _make_game()
    player = state.players[0]
    opponent = state.players[1]
    player.hand = [get_card("Gold")]
    opponent.hand = []

    gladiator = Gladiator()
    state.current_player_index = 0
    coins_before = player.coins
    gladiator.play_effect(state)

    # Gladiator gave +$1 (the duel bonus is added to base; play_effect only
    # handles the duel — the +$2 base is from the action play loop). Just
    # verify the supply was decremented and +$1 from the duel happened.
    assert player.coins == coins_before + 1
    assert state.supply["Gladiator"] == 4
