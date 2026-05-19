from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def _setup(ai=None):
    player = PlayerState(ai or DummyAI())
    state = GameState([player])
    state.setup_supply([get_card("Count")])
    player.hand = []
    player.deck = []
    player.discard = []
    player.in_play = []
    player.coins = 0
    player.actions = 1
    player.buys = 1
    return state, player


def _play_count(state, player):
    count = get_card("Count")
    player.in_play.append(count)
    count.play_effect(state)


class CoinsAI(DummyAI):
    def choose_count_second_mode(self, state, player, options):
        return "coins"


class DiscardCopperEstateAI(CoinsAI):
    def choose_count_first_mode(self, state, player, options):
        return "discard"

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return [card for card in choices if card.name in {"Copper", "Estate"}]


class InvalidTopdeckAI(CoinsAI):
    def choose_card_to_topdeck_from_hand(self, state, player, choices, reason=None):
        return get_card("Province")


def test_count_default_does_not_trash_gold_with_junk():
    state, player = _setup()
    player.hand = [get_card("Gold"), get_card("Copper"), get_card("Estate")]

    _play_count(state, player)

    assert [card.name for card in player.hand] == ["Gold"]
    assert sorted(card.name for card in player.discard) == ["Copper", "Estate"]
    assert all(card.name != "Gold" for card in state.trash)
    assert player.coins == 3


def test_count_discard_two_path_discards_chosen_cards():
    state, player = _setup(DiscardCopperEstateAI())
    player.hand = [get_card("Gold"), get_card("Copper"), get_card("Estate")]

    _play_count(state, player)

    assert [card.name for card in player.hand] == ["Gold"]
    assert sorted(card.name for card in player.discard) == ["Copper", "Estate"]
    assert player.coins == 3


def test_count_topdeck_path_with_fewer_than_two_disposable_cards_validates_pick():
    state, player = _setup(InvalidTopdeckAI())
    player.hand = [get_card("Gold"), get_card("Copper")]

    _play_count(state, player)

    assert [card.name for card in player.deck] == ["Gold"]
    assert [card.name for card in player.hand] == ["Copper"]
    assert all(card.name != "Province" for card in player.deck)
    assert player.coins == 3


def test_count_default_gains_duchy_late_game():
    state, player = _setup()
    state.turn_number = 10
    duchies_before = state.supply["Duchy"]
    player.hand = [get_card("Gold")]

    _play_count(state, player)

    assert [card.name for card in player.deck] == ["Gold"]
    assert any(card.name == "Duchy" for card in player.discard)
    assert state.supply["Duchy"] == duchies_before - 1
