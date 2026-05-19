from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class NamedRebuildAI(DummyAI):
    def __init__(self, named="Province", gain_name=None):
        super().__init__()
        self.named = named
        self.gain_name = gain_name

    def choose_name_for_rebuild(self, state, player):
        return self.named

    def choose_card_to_gain_for_rebuild(self, state, player, choices):
        if self.gain_name is None:
            return None
        for choice in choices:
            if choice.name == self.gain_name:
                return choice
        return None


def make_state(ai=None):
    player = PlayerState(ai or NamedRebuildAI())
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    state.supply = {"Estate": 8, "Duchy": 8, "Province": 8, "Colony": 8}
    return state, player


def test_rebuild_does_not_trash_estate_from_hand_or_discard_directly():
    state, player = make_state(NamedRebuildAI(named="Estate"))
    rebuild = get_card("Rebuild")
    estate_in_hand = get_card("Estate")
    estate_in_discard = get_card("Estate")
    duchy_on_deck = get_card("Duchy")

    player.hand = [estate_in_hand]
    player.discard = [estate_in_discard]
    player.deck = [duchy_on_deck]

    rebuild.play_effect(state)

    assert estate_in_hand in player.hand
    assert estate_in_discard in player.discard
    assert duchy_on_deck in state.trash
    assert estate_in_hand not in state.trash
    assert estate_in_discard not in state.trash


def test_rebuild_reveals_through_deck_and_shuffles_discard_as_needed():
    state, player = make_state(NamedRebuildAI(named="Province"))
    rebuild = get_card("Rebuild")
    copper = get_card("Copper")
    estate = get_card("Estate")

    player.deck = [copper]
    player.discard = [estate]

    rebuild.play_effect(state)

    assert copper in player.discard
    assert estate in state.trash
    assert any(card.name == "Duchy" for card in player.discard)


def test_rebuild_trashes_first_victory_not_matching_named_card():
    state, player = make_state(NamedRebuildAI(named="Estate"))
    rebuild = get_card("Rebuild")
    province_in_deck = get_card("Province")
    duchy = get_card("Duchy")
    named_estate = get_card("Estate")

    player.deck = [province_in_deck, duchy, named_estate]

    rebuild.play_effect(state)

    assert named_estate in player.discard
    assert duchy in state.trash
    assert province_in_deck in player.deck
    assert province_in_deck not in state.trash


def test_rebuild_gains_highest_eligible_victory_by_default():
    state, player = make_state(NamedRebuildAI(named="Province"))
    rebuild = get_card("Rebuild")
    estate = get_card("Estate")

    player.deck = [estate]

    rebuild.play_effect(state)

    assert estate in state.trash
    assert state.supply["Duchy"] == 7
    assert state.supply["Province"] == 8
    assert any(card.name == "Duchy" for card in player.discard)
    assert not any(card.name == "Province" for card in player.discard)
