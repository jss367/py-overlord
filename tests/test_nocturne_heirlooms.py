"""Tests for Nocturne Heirlooms (7 cards) and the starting-Copper swap hook."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _AI(DummyAI):
    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c.name == "Estate":
                return c
        return choices[0] if choices else None


def _setup_state():
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.players = [PlayerState(_AI())]
    state.players[0].initialize()
    state.supply = {
        "Copper": 30, "Silver": 20, "Gold": 10, "Curse": 10,
        "Estate": 10, "Duchy": 10, "Province": 8,
        "Wish": 12,
    }
    return state, state.players[0]


def test_starting_copper_swap_with_heirlooms():
    p = PlayerState(_AI())
    p.initialize(heirlooms=["Goat", "Pouch"])
    all_cards = p.deck + p.hand
    coppers = [c for c in all_cards if c.name == "Copper"]
    assert len(coppers) == 5  # 7 - 2 swapped
    names = [c.name for c in all_cards]
    assert "Goat" in names
    assert "Pouch" in names


def test_cursed_gold_play_gains_curse():
    state, player = _setup_state()
    cg = get_card("Cursed Gold")
    coins_before = player.coins
    player.in_play.append(cg)
    cg.on_play(state)
    assert player.coins == coins_before + 3
    assert any(c.name == "Curse" for c in player.discard)


def test_goat_play_trashes_card():
    state, player = _setup_state()
    goat = get_card("Goat")
    player.hand = [get_card("Estate")]
    player.in_play.append(goat)
    goat.on_play(state)
    assert player.coins >= 1
    assert any(c.name == "Estate" for c in state.trash)


def test_lucky_coin_play_gains_silver():
    state, player = _setup_state()
    lc = get_card("Lucky Coin")
    silver_before = state.supply["Silver"]
    player.in_play.append(lc)
    lc.on_play(state)
    assert player.coins == 1
    assert state.supply["Silver"] == silver_before - 1


def test_magic_lamp_play_with_six_unique_in_play_yields_three_wishes():
    state, player = _setup_state()
    lamp = get_card("Magic Lamp")
    # Need 6 differently-named cards in play (besides the lamp).
    player.in_play = [
        get_card("Village"), get_card("Smithy"), get_card("Lab"),
        get_card("Cellar"), get_card("Market"), get_card("Festival"),
    ] if False else [
        get_card("Village"), get_card("Smithy"), get_card("Cellar"),
        get_card("Market"), get_card("Festival"), get_card("Laboratory"),
    ]
    player.in_play.append(lamp)
    wish_before = state.supply["Wish"]
    lamp.on_play(state)
    assert state.supply["Wish"] == wish_before - 3
    assert lamp in state.trash


def test_magic_lamp_no_effect_under_six_unique():
    state, player = _setup_state()
    lamp = get_card("Magic Lamp")
    player.in_play = [get_card("Village"), get_card("Smithy"), lamp]
    wish_before = state.supply["Wish"]
    lamp.on_play(state)
    assert state.supply["Wish"] == wish_before
    assert lamp not in state.trash


def test_pasture_vp_per_estate():
    p = PlayerState(_AI())
    p.deck = [get_card("Estate"), get_card("Estate"), get_card("Pasture")]
    pasture = next(c for c in p.deck if c.name == "Pasture")
    assert pasture.get_victory_points(p) == 2


def test_pouch_grants_buy_and_one_coin():
    state, player = _setup_state()
    pouch = get_card("Pouch")
    buys_before = player.buys
    player.in_play.append(pouch)
    pouch.on_play(state)
    assert player.coins == 1
    assert player.buys == buys_before + 1


def test_haunted_mirror_on_discard_gains_ghost():
    state, player = _setup_state()
    state.supply["Ghost"] = 6
    mirror = get_card("Haunted Mirror")
    village = get_card("Village")
    player.in_play = [mirror]
    player.hand = [village]
    ghost_before = state.supply["Ghost"]
    mirror.on_discard_from_play(state, player)
    # Action got discarded, Ghost gained
    assert state.supply["Ghost"] == ghost_before - 1
    assert any(c.name == "Village" for c in player.discard)
