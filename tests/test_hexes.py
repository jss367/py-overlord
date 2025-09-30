from dominion.cards.nocturne.skulk import Skulk
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.hexes import resolve_hex
from tests.utils import DummyAI


class PlayAllTreasuresAI(DummyAI):
    """AI that plays every available treasure in order."""

    def choose_treasure(self, state, choices):
        for choice in choices:
            if choice is not None:
                return choice
        return None


class DiscardLowestAI(DummyAI):
    """AI that always discards the lowest value card presented."""

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return super().choose_cards_to_discard(state, player, choices, count)


def make_state_with_player(ai=None):
    player = PlayerState(ai or DummyAI())
    state = GameState([player])
    state.log_callback = lambda *_: None
    return state, player


def test_bad_omens_topdecks_coppers():
    state, player = make_state_with_player()
    player.deck = [get_card("Estate"), get_card("Silver"), get_card("Copper"), get_card("Copper")]
    player.discard = [get_card("Gold")]

    resolve_hex("Bad Omens", state, player)

    assert [card.name for card in player.deck] == ["Copper", "Copper"]
    assert sorted(card.name for card in player.discard) == ["Estate", "Gold", "Silver"]


def test_delusion_blocks_action_buys():
    state, player = make_state_with_player()
    state.supply = {"Smithy": 10, "Silver": 10}
    player.coins = 5

    resolve_hex("Delusion", state, player)
    assert player.deluded

    state._handle_start_of_buy_phase_effects()

    affordable = state._get_affordable_cards(player)
    names = {card.name for card in affordable}
    assert "Silver" in names
    assert "Smithy" not in names
    assert player.cannot_buy_actions


def test_envy_reduces_silver_output():
    state, player = make_state_with_player(PlayAllTreasuresAI())
    state.supply = {}
    player.hand = [get_card("Silver")]
    player.envious = True

    state.handle_treasure_phase()

    assert player.coins == 1
    assert not player.envious
    assert player.envious_effect_active


def test_misery_affects_scoring():
    state, player = make_state_with_player()
    player.hand = [get_card("Estate")]

    resolve_hex("Misery", state, player)
    resolve_hex("Misery", state, player)

    assert player.misery == 2
    assert player.get_victory_points(state) == -3


def test_locusts_trashes_and_gains_cheaper_card():
    state, player = make_state_with_player(DiscardLowestAI())
    state.supply = {"Copper": 10, "Curse": 10}
    player.deck = [get_card("Silver")]

    resolve_hex("Locusts", state, player)

    assert any(card.name == "Silver" for card in state.trash)
    assert [card.name for card in player.discard] == ["Copper"]
    assert state.supply["Copper"] == 9


def test_skulk_hexes_all_targets_with_same_hex():
    players = [PlayerState(DummyAI()) for _ in range(2)]
    state = GameState(players)
    state.log_callback = lambda *_: None
    state.current_player_index = 0
    state.supply = {"Copper": 10, "Curse": 10}
    state.hex_deck = ["Greed"]

    victim = players[1]
    victim.deck = []
    victim.discard = []

    Skulk().play_effect(state)

    assert victim.deck and victim.deck[-1].name == "Copper"
    assert state.supply["Copper"] == 9
    assert state.hex_deck == []
    assert state.hex_discard == ["Greed"]
